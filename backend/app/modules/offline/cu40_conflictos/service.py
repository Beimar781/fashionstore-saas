"""CU-40 · Gestionar conflictos de sincronización (RN14, RF22). Capa de negocio.

Una operación en conflicto (no alcanzaron las existencias) no descontó nada. El Encargado de la sucursal (o el Administrador) la resuelve a mano:
- REINTENTAR: vuelve a aplicarla con las existencias de ahora (por ejemplo, después de recibir mercadería). Si ya alcanzan, queda CONFIRMADA; si no, sigue en conflicto.
- DESCARTAR: la rechaza con un motivo. En una venta de contado, el efectivo ya recibido se devuelve al cliente.
"""
import uuid

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.constantes import ADMIN
from app.core.errors import AppError, Conflicto, DatosInvalidos, NoEncontrado
from app.core.tiempo import ahora
from app.modules.acceso.dependencias import Contexto
from app.modules.acceso.publico import contexto_de_usuario
from app.modules.offline import avisos, schemas
from app.modules.offline.cu38_sincronizar.service import MSG_CONFIRMADA, MSG_CONFLICTO, MSG_FORMATO
from app.modules.offline.cu40_conflictos import schemas as esquemas
from app.modules.offline.descarte import devolver_venta_descartada
from app.modules.offline.ejecucion import Ejecutor, es_falta_de_stock
from app.modules.offline.mapeo import operaciones_out
from app.modules.offline.models import OperacionOffline
from app.modules.offline.repository import OperacionRepository

MSG_NO_ENCONTRADA = "Operación no encontrada."
MSG_YA_RESUELTA = "La operación ya no está en conflicto."
MSG_MOTIVO = "Indique el motivo del descarte."
MSG_SOLO_VENTA = "Solo una venta de contado ya cobrada se descarta devolviendo el dinero."
MSG_USUARIO_INACTIVO = "El usuario que registró la operación ya no está activo: descártela."


class ConflictosService:
    def __init__(self, db: Session, ctx: Contexto):
        self.db = db
        self.ctx = ctx
        self.empresa_id = ctx.empresa_id
        self.ops = OperacionRepository(db, ctx.empresa_id)

    def listar(self) -> list[schemas.OperacionOut]:
        return operaciones_out(self.db, self.empresa_id, self.ops.en_conflicto(self._alcance()))

    def resolver(self, operacion_id: uuid.UUID, datos: esquemas.ResolverIn) -> schemas.OperacionOut:
        fila = self._propia(operacion_id)
        if fila.estado != "EN_CONFLICTO":
            raise Conflicto(MSG_YA_RESUELTA)
        devuelto = None
        if datos.accion == "DESCARTAR":
            devuelto = self._descartar(fila, (datos.motivo or "").strip(), datos)
        else:
            self._reintentar(fila)
        self.db.commit()
        if datos.accion == "DESCARTAR":  # regla 17: el cliente se entera con la operación ya resuelta
            avisos.avisar_descartada(self.db, self.empresa_id, fila, fila.motivo_resolucion, *(devuelto or ()))
        elif fila.estado == "CONFIRMADA":
            avisos.avisar_confirmada(self.db, self.empresa_id, fila)
        return operaciones_out(self.db, self.empresa_id, [fila])[0]

    # ---- acciones ----
    def _descartar(self, fila: OperacionOffline, motivo: str, datos: esquemas.ResolverIn) -> tuple[str, str] | None:
        """Devuelve (monto, nota) si se registró la devolución del dinero de una venta ya cobrada."""
        if not motivo:
            raise DatosInvalidos(MSG_MOTIVO)
        devuelto = None
        if datos.devolver_dinero:
            if fila.tipo != "VENTA_CONTADO":
                raise DatosInvalidos(MSG_SOLO_VENTA)
            autor = contexto_de_usuario(self.db, self.empresa_id, fila.usuario_id)
            if autor is None:
                raise Conflicto(MSG_USUARIO_INACTIVO)
            devolucion, pedido_id = devolver_venta_descartada(self.db, self.ctx, autor, fila, datos.condicion, motivo)  # CU-41: la prenda vuelve al inventario y se emite la nota
            fila.pedido_id = pedido_id
            devuelto = (str(devolucion.reembolso), devolucion.numero)
        fila.estado, fila.resolucion, fila.motivo_resolucion = "RECHAZADA", "DESCARTADA", motivo[:200]
        fila.resuelta_por, fila.resuelta_en = self.ctx.usuario.id, ahora()
        fila.mensaje = f"Descartada por {self.ctx.usuario.nombre}: {motivo}."
        if devuelto:
            fila.mensaje += f" Se devolvieron Bs {devuelto[0]} en efectivo al cliente (nota {devuelto[1]})."
        elif fila.tipo == "VENTA_CONTADO":
            fila.mensaje += " Devuelva el efectivo recibido al cliente."
        return devuelto

    def _reintentar(self, fila: OperacionOffline) -> None:
        autor = contexto_de_usuario(self.db, self.empresa_id, fila.usuario_id)
        if autor is None:
            raise Conflicto(MSG_USUARIO_INACTIVO)
        id_fila, tipo, payload, sucursal_id = fila.id, fila.tipo, fila.payload, fila.sucursal_id
        try:
            r = Ejecutor(self.db, autor).ejecutar(tipo, {**payload, "sucursal_id": sucursal_id} if tipo == "COMPRA" else payload)
            fila.estado, fila.mensaje, fila.detalle = "CONFIRMADA", MSG_CONFIRMADA + " Resuelta por reintento.", None
            fila.referencia, fila.comprobante, fila.pedido_id, fila.reserva_id = r.referencia, r.comprobante, r.pedido_id, r.reserva_id
        except Exception as e:  # noqa: BLE001
            self.db.rollback()
            fila = self.ops.con_id(id_fila)  # tras deshacer, se vuelve a leer la operación
            if es_falta_de_stock(e):  # sigue sin alcanzar: continúa en conflicto con las existencias de ahora
                fila.detalle, fila.mensaje = {"faltantes": Ejecutor(self.db, autor).faltantes(payload, sucursal_id)}, MSG_CONFLICTO
                fila.intentos += 1
                self.db.commit()
                raise Conflicto("Todavía no hay existencias suficientes: " + "; ".join(f"{f['producto']} ({f['talla']}, {f['color']}): solicitadas {f['solicitadas']}, disponibles {f['disponibles']}" for f in fila.detalle["faltantes"]) + ".") from e
            if isinstance(e, (AppError, ValidationError)):  # ya no se puede aplicar por otro motivo (por ejemplo, la reserva venció): se rechaza
                fila.estado, fila.mensaje = "RECHAZADA", e.message if isinstance(e, AppError) else MSG_FORMATO
                fila.detalle = None
            else:
                raise
        fila.intentos += 1
        fila.resolucion, fila.resuelta_por, fila.resuelta_en = "REINTENTADA", self.ctx.usuario.id, ahora()

    def _alcance(self) -> int | None:
        return None if self.ctx.rol == ADMIN else self.ctx.sucursal_id  # el Encargado solo ve su sucursal (RN10)

    def _propia(self, operacion_id: uuid.UUID) -> OperacionOffline:
        fila = self.ops.por_operacion(operacion_id, bloquear=True)
        if fila is None or (self._alcance() is not None and fila.sucursal_id != self._alcance()):
            raise NoEncontrado(MSG_NO_ENCONTRADA)  # también si es de otra sucursal u otra empresa
        return fila

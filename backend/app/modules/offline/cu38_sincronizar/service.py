"""CU-38 · Sincronizar operaciones pendientes (RN11 a RN14, RNF04 a RNF06, RNF10). Capa de negocio.

Cada operación se procesa en orden cronológico y en su propia transacción: la operación y sus efectos (venta, cobro, stock, reserva) se confirman juntos o no se confirma nada.
- Reenviar una operación ya procesada devuelve el resultado original sin duplicarla (RN12, RNF05).
- Si no alcanzan las existencias, no se descuenta nada y queda EN_CONFLICTO para que el Encargado la resuelva (RN14).
- Si el servidor falla por un problema pasajero, la operación NO se guarda y el cliente la conserva para reintentar (RNF06).
"""
import logging

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.constantes import CAJERO, CLIENTE, ENCARGADO
from app.core.errors import AppError
from app.core.tiempo import a_local, ahora
from app.modules.acceso.dependencias import Contexto
from app.modules.offline import avisos, schemas
from app.modules.offline.ejecucion import Ejecutor, Resultado, es_falta_de_stock
from app.modules.offline.mapeo import resultado_de
from app.modules.offline.models import OperacionOffline
from app.modules.offline.repository import OperacionRepository
from app.modules.reservas.publico import notificar
from app.modules.sucursales.publico import sucursal_de_empresa

logger = logging.getLogger(__name__)
MSG_PERMISOS = "No tiene permisos para registrar este tipo de operación sin conexión."
MSG_OTRA_SUCURSAL = "La operación corresponde a otra sucursal."
MSG_ID_AJENO = "Este identificador de operación ya fue utilizado por otro usuario."
MSG_FORMATO = "La operación no tiene el formato esperado."
MSG_SUCURSAL = "Sucursal no encontrada."
MSG_CONFLICTO = "No hay existencias suficientes para esta operación. No se descontó nada del inventario; el Encargado debe resolverla."
MSG_ERROR = "El servidor no pudo procesar la operación ahora. Se conserva en el dispositivo y se reintentará."
MSG_CONFIRMADA = "Operación confirmada."
NOMBRE_TIPO = {"VENTA_CONTADO": "venta de contado", "RESERVA": "reserva", "COMPRA": "compra"}
PERMISOS = {"VENTA_CONTADO": (CAJERO, ENCARGADO), "RESERVA": (CLIENTE,), "COMPRA": (CLIENTE,)}


class SincronizacionService:
    def __init__(self, db: Session, ctx: Contexto):
        self.db = db
        self.ctx = ctx
        self.empresa_id = ctx.empresa_id
        self.ops = OperacionRepository(db, ctx.empresa_id)

    def sincronizar(self, datos: schemas.SincronizarIn) -> schemas.SincronizacionOut:
        por_id = {op.id: self._una(op) for op in sorted(datos.operaciones, key=lambda o: o.creada_en)}  # en el orden en que ocurrieron
        resultados = [por_id[op.id] for op in datos.operaciones]
        return schemas.SincronizacionOut(resultados=resultados, sincronizado_en=ahora())

    def _una(self, op: schemas.OperacionIn) -> schemas.ResultadoOperacionOut:
        self.ops.bloquear(op.id)
        previa = self.ops.por_operacion(op.id)
        if previa is not None:
            if previa.usuario_id != self.ctx.usuario.id:
                return self._sin_guardar(op, "RECHAZADA", MSG_ID_AJENO)
            return resultado_de(previa, ya_procesada=True)  # RN12: el resultado original
        if self.ctx.rol not in PERMISOS[op.tipo]:
            return self._sin_guardar(op, "RECHAZADA", MSG_PERMISOS)
        sucursal_id = self._sucursal(op)
        if sucursal_id is None:
            return self._sin_guardar(op, "RECHAZADA", MSG_SUCURSAL)
        if sucursal_id == -1:
            return self._sin_guardar(op, "RECHAZADA", MSG_OTRA_SUCURSAL)
        try:
            resultado = Ejecutor(self.db, self.ctx).ejecutar(op.tipo, {**op.payload, "sucursal_id": sucursal_id} if op.tipo == "COMPRA" else op.payload)
            fila = self._guardar(op, sucursal_id, "CONFIRMADA", MSG_CONFIRMADA, resultado)
            self.db.commit()  # la operación y todos sus efectos, en una sola transacción (RNF04)
        except Exception as e:  # noqa: BLE001
            self.db.rollback()
            return self._fallida(op, sucursal_id, e)
        avisos.avisar_confirmada(self.db, self.empresa_id, fila)  # regla 17: con la operación ya confirmada
        logger.info("sync operacion=%s tipo=%s estado=%s empresa=%s sucursal=%s", op.id, op.tipo, fila.estado, self.empresa_id, sucursal_id)
        return resultado_de(fila)

    def _sucursal(self, op: schemas.OperacionIn) -> int | None:
        """La sucursal de la operación: la del empleado (RN10) o, para la reserva de un cliente, la que eligió. None: no existe; -1: es de otra sucursal."""
        if self.ctx.sucursal_id is not None:
            return -1 if op.sucursal_id not in (None, self.ctx.sucursal_id) else self.ctx.sucursal_id
        elegida = op.sucursal_id if op.sucursal_id is not None else op.payload.get("sucursal_id")
        return elegida if isinstance(elegida, int) and sucursal_de_empresa(self.db, self.empresa_id, elegida) else None

    def _fallida(self, op: schemas.OperacionIn, sucursal_id: int, e: Exception) -> schemas.ResultadoOperacionOut:
        if es_falta_de_stock(e):  # RN14: conflicto, nada descontado a medias
            detalle = {"faltantes": Ejecutor(self.db, self.ctx).faltantes(op.payload, sucursal_id)}
            fila = self._guardar(op, sucursal_id, "EN_CONFLICTO", MSG_CONFLICTO, Resultado(None, None), detalle)
            self.db.flush()
            notificar(
                self.db, self.empresa_id, "CONFLICTO_SYNC", "Operación offline en conflicto",
                f"Una {NOMBRE_TIPO[op.tipo]} registrada sin conexión por {self.ctx.usuario.nombre} no se pudo aplicar por falta de existencias. Resuélvala en «Conflictos de sincronización».",
                sucursal_id=sucursal_id, referencia_tipo="OPERACION_OFFLINE", referencia_id=fila.id,
            )
        elif isinstance(e, ValidationError):
            fila = self._guardar(op, sucursal_id, "RECHAZADA", MSG_FORMATO, Resultado(None, None))
        elif isinstance(e, AppError):
            fila = self._guardar(op, sucursal_id, "RECHAZADA", e.message, Resultado(None, None))
        else:  # un fallo pasajero del servidor: no se guarda y el cliente reintenta (RNF06)
            logger.exception("sync operacion=%s falló", op.id)
            return self._sin_guardar(op, "ERROR", MSG_ERROR)
        self.db.commit()
        if fila.estado == "EN_CONFLICTO":
            avisos.avisar_conflicto(self.db, self.empresa_id, fila)  # regla 17: el cliente se entera, además del personal de la sucursal
        logger.info("sync operacion=%s tipo=%s estado=%s empresa=%s sucursal=%s", op.id, op.tipo, fila.estado, self.empresa_id, sucursal_id)
        return resultado_de(fila)

    def _guardar(self, op: schemas.OperacionIn, sucursal_id: int, estado: str, mensaje: str, r: Resultado, detalle: dict | None = None) -> OperacionOffline:
        return self.ops.agregar(OperacionOffline(
            operacion_id=op.id, usuario_id=self.ctx.usuario.id, sucursal_id=sucursal_id, tipo=op.tipo, estado=estado, payload=op.payload, creada_en_cliente=a_local(op.creada_en),
            mensaje=mensaje, referencia=r.referencia, comprobante=r.comprobante, detalle=detalle, pedido_id=r.pedido_id, reserva_id=r.reserva_id,
        ))

    @staticmethod
    def _sin_guardar(op: schemas.OperacionIn, estado: str, mensaje: str) -> schemas.ResultadoOperacionOut:
        """Rechazos que no dejan registro (no hay sucursal válida a la que asociarlos) y fallos pasajeros: el resultado se repite igual al reenviar."""
        return schemas.ResultadoOperacionOut(id=op.id, estado=estado, mensaje=mensaje, referencia=None, comprobante=None, detalle=None, ya_procesada=False)

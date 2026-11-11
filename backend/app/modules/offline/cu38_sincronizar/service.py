"""CU-38 · Sincronizar operaciones pendientes (RN11 a RN14, RNF04 a RNF06, RNF10). Capa de negocio.

Cada operación se procesa en orden cronológico y en su propia transacción: la operación y sus efectos (venta, cobro, stock, reserva) se confirman juntos o no se confirma nada.
- Reenviar una operación ya procesada devuelve el resultado original sin duplicarla (RN12, RNF05).
- Si no alcanzan las existencias, no se descuenta nada y queda EN_CONFLICTO para que el Encargado la resuelva (RN14).
- Si el servidor falla por un problema pasajero, la operación NO se guarda y el cliente la conserva para reintentar (RNF06).
"""
import logging

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.constantes import CAJERO, CLIENTE, ENCARGADO, PROVEEDOR
from app.core.errors import AppError
from app.core.tiempo import a_local, ahora
from app.modules.acceso.dependencias import Contexto
from app.modules.offline import avisos, schemas
from app.modules.offline.ejecucion import Ejecutor, PrecioCambio, Resultado, es_falta_de_stock
from app.modules.offline.mapeo import resultado_de
from app.modules.offline.models import OperacionOffline
from app.modules.offline.schemas import DATOS_DE_TARJETA
from app.modules.offline.repository import OperacionRepository
from app.modules.reservas.publico import notificar
from app.modules.sucursales.publico import sucursal_de_empresa
from app.primer_parcial.ventas.publico import ConfirmarIn, IniciarIn, PagoService, SinStock

logger = logging.getLogger(__name__)
MSG_PERMISOS = "No tiene permisos para registrar este tipo de operación sin conexión."
MSG_OTRA_SUCURSAL = "La operación corresponde a otra sucursal."
MSG_ID_AJENO = "Este identificador de operación ya fue utilizado por otro usuario."
MSG_FORMATO = "La operación no tiene el formato esperado."
MSG_SUCURSAL = "Sucursal no encontrada."
MSG_CONFLICTO = "No hay existencias suficientes para esta operación. No se descontó nada del inventario; el Encargado debe resolverla."
MSG_ERROR = "El servidor no pudo procesar la operación ahora. Se conserva en el dispositivo y se reintentará."
MSG_CONFIRMADA = "Operación confirmada."
MSG_COBRADA = "Compra cobrada y confirmada."
MSG_NO_COBRADA = "No pudimos cobrar su tarjeta; complete el pago desde Mis compras."
MSG_COBRO_PENDIENTE = "Estamos verificando el cobro de su tarjeta; revise Mis compras."
MSG_AGOTADA_SIN_COBRO = "La prenda se agotó mientras estaba sin conexión. No se le cobró nada."
MSG_RELOJ = "La hora de este dispositivo parece incorrecta; revísela para que sus ventas queden con la fecha correcta."
TOLERANCIA_RELOJ = 300  # segundos (5 minutos)
NOMBRE_TIPO = {"VENTA_CONTADO": "venta de contado", "RESERVA": "reserva", "COMPRA": "compra", "CANCELAR_RESERVA": "cancelación de reserva", "DEVOLUCION": "devolución", "RECEPCION": "recepción de mercadería", "AJUSTE_INVENTARIO": "ajuste de inventario", "PREPARAR_RESERVA": "preparación de reserva", "PRENDA_NO_ENCONTRADA": "prenda no encontrada", "ATENDER_RESERVA": "atención de reserva", "PROPUESTA_PROVEEDOR": "propuesta de producto"}
PERMISOS = {"VENTA_CONTADO": (CAJERO, ENCARGADO), "RESERVA": (CLIENTE,), "COMPRA": (CLIENTE,), "CANCELAR_RESERVA": (CLIENTE,), "DEVOLUCION": (CAJERO, ENCARGADO), "RECEPCION": (ENCARGADO,), "AJUSTE_INVENTARIO": (ENCARGADO,), "PREPARAR_RESERVA": (ENCARGADO,), "PRENDA_NO_ENCONTRADA": (ENCARGADO,), "ATENDER_RESERVA": (ENCARGADO,), "PROPUESTA_PROVEEDOR": (PROVEEDOR,)}
SIN_SUCURSAL = ("PROPUESTA_PROVEEDOR",)  # el portal del proveedor no pertenece a una sucursal
CON_SUCURSAL = ("COMPRA", "RECEPCION", "AJUSTE_INVENTARIO")  # el ejecutor las aplica en la sucursal de la operación


def sin_datos_de_tarjeta(payload):
    """Nada de número, fecha ni CVC en la cola ni en la base: aunque un cliente los mandara por error, se descartan antes de guardar la operación (aun si se rechaza)."""
    if isinstance(payload, dict):
        return {k: sin_datos_de_tarjeta(v) for k, v in payload.items() if k not in DATOS_DE_TARJETA}
    if isinstance(payload, list):
        return [sin_datos_de_tarjeta(v) for v in payload]
    return payload


class SincronizacionService:
    def __init__(self, db: Session, ctx: Contexto):
        self.db = db
        self.ctx = ctx
        self.empresa_id = ctx.empresa_id
        self.ops = OperacionRepository(db, ctx.empresa_id)
        self.desfase: int | None = None

    def sincronizar(self, datos: schemas.SincronizarIn) -> schemas.SincronizacionOut:
        desfase = round((datos.hora_dispositivo - ahora()).total_seconds()) if datos.hora_dispositivo else None
        self.desfase = desfase
        por_id = {op.id: self._una(op) for op in sorted(datos.operaciones, key=lambda o: o.creada_en)}  # en el orden en que ocurrieron
        resultados = [por_id[op.id] for op in datos.operaciones]
        aviso = MSG_RELOJ if desfase is not None and abs(desfase) > TOLERANCIA_RELOJ else None
        return schemas.SincronizacionOut(resultados=resultados, sincronizado_en=ahora(), desfase_reloj_segundos=desfase, aviso_reloj=aviso)

    def _una(self, op: schemas.OperacionIn) -> schemas.ResultadoOperacionOut:
        self.ops.bloquear(op.id)
        previa = self.ops.por_operacion(op.id)
        if previa is not None:
            if previa.usuario_id != self.ctx.usuario.id:
                return self._sin_guardar(op, "RECHAZADA", MSG_ID_AJENO)
            return resultado_de(previa, ya_procesada=True)  # RN12: el resultado original
        if self.ctx.rol not in PERMISOS[op.tipo]:
            return self._sin_guardar(op, "RECHAZADA", MSG_PERMISOS)
        sucursal_id = self._sucursal(op) if op.tipo not in SIN_SUCURSAL else 0
        if sucursal_id is None:
            return self._sin_guardar(op, "RECHAZADA", MSG_SUCURSAL)
        if sucursal_id == -1:
            return self._sin_guardar(op, "RECHAZADA", MSG_OTRA_SUCURSAL)
        sucursal_id = sucursal_id or None  # 0 = operación sin sucursal
        try:
            resultado = Ejecutor(self.db, self.ctx).ejecutar(op.tipo, {**op.payload, "sucursal_id": sucursal_id} if op.tipo in CON_SUCURSAL else op.payload)
            fila = self._guardar(op, sucursal_id, "CONFIRMADA", MSG_CONFIRMADA, resultado)
            self.db.commit()  # la operación y todos sus efectos, en una sola transacción (RNF04)
        except Exception as e:  # noqa: BLE001
            self.db.rollback()
            return self._fallida(op, sucursal_id, e)
        if resultado.tarjeta_a_cobrar is not None:
            fila = self._cobrar_con_tarjeta(fila, resultado.tarjeta_a_cobrar)  # el cobro y su aviso (regla 17)
        else:
            avisos.avisar_confirmada(self.db, self.empresa_id, fila)  # regla 17: con la operación ya confirmada
        if resultado.despues is not None:
            try:
                resultado.despues()  # por ejemplo, el aviso push de una devolución; un fallo se registra y no deshace la operación
            except Exception:  # noqa: BLE001
                logger.exception("sync operacion=%s: falló el aviso posterior", op.id)
        logger.info("sync operacion=%s tipo=%s estado=%s empresa=%s sucursal=%s", op.id, op.tipo, fila.estado, self.empresa_id, sucursal_id)
        return resultado_de(fila)

    def _cobrar_con_tarjeta(self, fila: OperacionOffline, tarjeta_id: int) -> OperacionOffline:
        """Compra con tarjeta guardada: con la compra ya confirmada se cobra desde el servidor, fuera de sesión (CU-32), y el operacion_id sirve de clave de idempotencia en la pasarela.
        Si el banco rechaza, la tarjeta pide autenticación (3D Secure) o la pasarela no responde, el pedido queda por pagar: el cobro nunca deshace la compra."""
        operacion_id, pedido_id, cobrado, pendiente, sin_stock = fila.operacion_id, fila.pedido_id, False, False, False
        comprobante = None
        try:
            pagos = PagoService(self.db, self.ctx)
            iniciado = pagos.iniciar(pedido_id, IniciarIn(tarjeta_guardada_id=tarjeta_id), fuera_de_sesion=True, idempotencia=str(operacion_id))
            r = pagos.confirmar(iniciado.pago_id, ConfirmarIn())
            cobrado, pendiente, comprobante = r.aprobado, r.pendiente, r.pedido.comprobante_numero
        except SinStock:
            sin_stock = True  # la prenda se agotó entre la confirmación y el cobro: la autorización se anuló y no se cobró nada
        except Exception as e:  # noqa: BLE001
            self.db.rollback()
            logger.warning("sync operacion=%s: no se pudo cobrar la tarjeta guardada (%s)", operacion_id, e.__class__.__name__)
        fila = self.ops.por_operacion(operacion_id)
        if cobrado:
            fila.mensaje, fila.comprobante = MSG_COBRADA, comprobante
        elif sin_stock:
            fila.estado, fila.mensaje = "EN_CONFLICTO", MSG_AGOTADA_SIN_COBRO
        else:
            fila.mensaje = MSG_COBRO_PENDIENTE if pendiente else MSG_NO_COBRADA
        self.db.commit()
        if cobrado:
            avisos.avisar_cobrada(self.db, self.empresa_id, fila)
        elif not sin_stock:  # si se agotó, CU-32 ya avisó al cliente
            avisos.avisar_no_cobrada(self.db, self.empresa_id, fila, pendiente)
        return fila

    def _sucursal(self, op: schemas.OperacionIn) -> int | None:
        """La sucursal de la operación: la del empleado (RN10) o, para la reserva de un cliente, la que eligió. None: no existe; -1: es de otra sucursal."""
        if self.ctx.sucursal_id is not None:
            return -1 if op.sucursal_id not in (None, self.ctx.sucursal_id) else self.ctx.sucursal_id
        elegida = op.sucursal_id if op.sucursal_id is not None else op.payload.get("sucursal_id")
        return elegida if isinstance(elegida, int) and sucursal_de_empresa(self.db, self.empresa_id, elegida) else None

    def _fallida(self, op: schemas.OperacionIn, sucursal_id: int, e: Exception) -> schemas.ResultadoOperacionOut:
        if es_falta_de_stock(e):  # RN14: conflicto, nada descontado a medias
            detalle = {"faltantes": Ejecutor(self.db, self.ctx).faltantes(op.payload, sucursal_id)}
            con_tarjeta = op.tipo == "COMPRA" and op.payload.get("tarjeta_guardada_id") is not None
            fila = self._guardar(op, sucursal_id, "EN_CONFLICTO", MSG_AGOTADA_SIN_COBRO if con_tarjeta else MSG_CONFLICTO, Resultado(None, None), detalle)
            self.db.flush()
            notificar(
                self.db, self.empresa_id, "CONFLICTO_SYNC", "Operación offline en conflicto",
                f"Una {NOMBRE_TIPO[op.tipo]} registrada sin conexión por {self.ctx.usuario.nombre} no se pudo aplicar por falta de existencias. Resuélvala en «Conflictos de sincronización».",
                sucursal_id=sucursal_id, referencia_tipo="OPERACION_OFFLINE", referencia_id=fila.id,
            )
        elif isinstance(e, PrecioCambio):  # §7.2: el precio cambió desde que se registró la venta; no se descuenta nada
            fila = self._guardar(op, sucursal_id, "EN_CONFLICTO", e.message, Resultado(None, None), {"precios": e.cambios})
            self.db.flush()
            notificar(
                self.db, self.empresa_id, "CONFLICTO_SYNC", "Venta offline con precio distinto",
                f"Una {NOMBRE_TIPO[op.tipo]} registrada sin conexión por {self.ctx.usuario.nombre} tiene un precio que cambió. Resuélvala en «Conflictos de sincronización».",
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
        if fila.estado == "EN_CONFLICTO" and "faltantes" in (fila.detalle or {}):
            avisos.avisar_conflicto(self.db, self.empresa_id, fila)  # regla 17: el cliente se entera, además del personal de la sucursal
        elif fila.estado == "EN_CONFLICTO" and fila.tipo == "COMPRA" and "precios" in (fila.detalle or {}):
            avisos.avisar_precio_distinto(self.db, self.empresa_id, fila)  # la compra con tarjeta no se cobró: el precio cambió
        logger.info("sync operacion=%s tipo=%s estado=%s empresa=%s sucursal=%s", op.id, op.tipo, fila.estado, self.empresa_id, sucursal_id)
        return resultado_de(fila)

    def _guardar(self, op: schemas.OperacionIn, sucursal_id: int, estado: str, mensaje: str, r: Resultado, detalle: dict | None = None) -> OperacionOffline:
        return self.ops.agregar(OperacionOffline(
            operacion_id=op.id, usuario_id=self.ctx.usuario.id, sucursal_id=sucursal_id, tipo=op.tipo, estado=estado, payload=sin_datos_de_tarjeta(op.payload), creada_en_cliente=a_local(op.creada_en),
            mensaje=mensaje, referencia=r.referencia, comprobante=r.comprobante, detalle=detalle, pedido_id=r.pedido_id, reserva_id=r.reserva_id,
            desfase_reloj_segundos=self.desfase,
        ))

    @staticmethod
    def _sin_guardar(op: schemas.OperacionIn, estado: str, mensaje: str) -> schemas.ResultadoOperacionOut:
        """Rechazos que no dejan registro (no hay sucursal válida a la que asociarlos) y fallos pasajeros: el resultado se repite igual al reenviar."""
        return schemas.ResultadoOperacionOut(id=op.id, estado=estado, mensaje=mensaje, referencia=None, comprobante=None, detalle=None, ya_procesada=False)

"""Avisos al cliente por sus operaciones sin conexión (regla 17): campana + push, siempre DESPUÉS de confirmar la operación; un fallo del push nunca la deshace.

El personal de la sucursal se entera por el aviso CONFLICTO_SYNC (CU-38); aquí se avisa a quien hizo la compra o la reserva, o al cliente identificado en una venta de caja.
"""
from sqlalchemy.orm import Session

from app.modules.acceso.publico import cliente_por_email
from app.modules.offline.models import OperacionOffline
from app.modules.reservas.publico import avisar_cliente

TEXTO = {"COMPRA": "compra", "RESERVA": "reserva", "VENTA_CONTADO": "compra", "CANCELAR_RESERVA": "reserva", "DEVOLUCION": "devolución", "RECEPCION": "recepción", "AJUSTE_INVENTARIO": "ajuste", "PREPARAR_RESERVA": "reserva", "PRENDA_NO_ENCONTRADA": "reserva", "ATENDER_RESERVA": "reserva", "PROPUESTA_PROVEEDOR": "propuesta"}
PREFIJO = {"COMPRA": "COM", "RESERVA": "RES", "VENTA_CONTADO": "VTA", "CANCELAR_RESERVA": "RES", "DEVOLUCION": "DEV", "RECEPCION": "REC", "AJUSTE_INVENTARIO": "AJU", "PREPARAR_RESERVA": "RES", "PRENDA_NO_ENCONTRADA": "RES", "ATENDER_RESERVA": "RES", "PROPUESTA_PROVEEDOR": "PRO"}


def codigo_visible(tipo: str, operacion_id) -> str:
    """El identificador corto con el que el cliente reconoce su operación mientras no tiene código de pedido o de reserva."""
    return f"{PREFIJO[tipo]}-{str(operacion_id)[:8].upper()}"


def cliente_de(db: Session, empresa_id: int, fila: OperacionOffline) -> int | None:
    if fila.tipo in ("COMPRA", "RESERVA", "CANCELAR_RESERVA"):
        return fila.usuario_id  # la hizo el propio cliente
    email = (fila.payload or {}).get("cliente_email")
    cliente = cliente_por_email(db, empresa_id, email) if email else None
    return cliente.id if cliente else None


def _avisar(db: Session, empresa_id: int, fila: OperacionOffline, titulo: str, mensaje: str, referencia_tipo: str = "OPERACION_OFFLINE", referencia_id: int | None = None) -> None:
    avisar_cliente(db, empresa_id, cliente_de(db, empresa_id, fila), "OPERACION_OFFLINE", titulo, mensaje, referencia_tipo, referencia_id if referencia_id is not None else fila.id)


def avisar_conflicto(db: Session, empresa_id: int, fila: OperacionOffline) -> None:
    """La prenda se agotó entre que el cliente la vio sin conexión y que sincronizó: no se descontó ni se cobró nada."""
    sin_cobro = " No se le cobró nada." if (fila.payload or {}).get("tarjeta_guardada_id") is not None else ""  # compra con tarjeta guardada: se avisa que no hubo cobro
    _avisar(db, empresa_id, fila, "No se pudo realizar su compra" if fila.tipo != "RESERVA" else "No se pudo realizar su reserva",
            f"Su {TEXTO[fila.tipo]} {codigo_visible(fila.tipo, fila.operacion_id)} no se pudo realizar porque la prenda se agotó.{sin_cobro}")


def avisar_cobrada(db: Session, empresa_id: int, fila: OperacionOffline) -> None:
    """Compra hecha sin conexión con tarjeta guardada: el servidor la cobró al sincronizar."""
    comprobante = f" Comprobante {fila.comprobante}." if fila.comprobante else ""
    _avisar(db, empresa_id, fila, "Su compra fue cobrada y confirmada", f"Su compra {fila.referencia} fue cobrada con su tarjeta guardada y está confirmada.{comprobante}", "PEDIDO", fila.pedido_id)


def avisar_no_cobrada(db: Session, empresa_id: int, fila: OperacionOffline, pendiente: bool = False) -> None:
    """El cobro no se completó (rechazo del banco, 3D Secure o pasarela sin respuesta): la compra queda por pagar en «Mis compras»."""
    if pendiente:
        _avisar(db, empresa_id, fila, "Estamos verificando el cobro de su tarjeta", f"Su compra {fila.referencia} está pendiente de confirmación en la pasarela. Revise «Mis compras».", "PEDIDO", fila.pedido_id)
    else:
        _avisar(db, empresa_id, fila, "No pudimos cobrar su tarjeta", f"No pudimos cobrar su tarjeta; complete el pago desde Mis compras. Su compra {fila.referencia} sigue por pagar.", "PEDIDO", fila.pedido_id)


def avisar_precio_distinto(db: Session, empresa_id: int, fila: OperacionOffline) -> None:
    """El precio cambió desde que el cliente autorizó el cobro: no se cobró nada y debe confirmar el nuevo total."""
    _avisar(db, empresa_id, fila, "El precio de su compra cambió", f"El precio cambió; confirme el nuevo total. Su compra {codigo_visible(fila.tipo, fila.operacion_id)} no se realizó y no se le cobró nada.")


def avisar_confirmada(db: Session, empresa_id: int, fila: OperacionOffline) -> None:
    if fila.tipo == "COMPRA":
        _avisar(db, empresa_id, fila, "Su compra está lista para pagar",
                f"Su compra {fila.referencia} se registró y hay stock. Pague con tarjeta en «Mis compras» para confirmarla.", "PEDIDO", fila.pedido_id)
    elif fila.tipo == "RESERVA":
        _avisar(db, empresa_id, fila, "Su reserva fue confirmada", f"Su reserva {fila.referencia} quedó confirmada.", "RESERVA", fila.reserva_id)


    elif fila.tipo == "CANCELAR_RESERVA":
        _avisar(db, empresa_id, fila, "Su reserva fue cancelada", f"Su reserva {fila.referencia} fue cancelada.", "RESERVA", fila.reserva_id)


def avisar_descartada(db: Session, empresa_id: int, fila: OperacionOffline, motivo: str, devuelto: str | None = None, nota: str | None = None) -> None:
    """El Encargado descartó la operación: si el dinero ya se había recibido en caja, el aviso dice que se devolvió."""
    texto = f"Su {TEXTO[fila.tipo]} {codigo_visible(fila.tipo, fila.operacion_id)} no se pudo realizar porque la prenda se agotó ({motivo})."
    texto += f" Se le devolvieron Bs {devuelto} en efectivo (nota {nota})." if devuelto else " No se le cobró nada."
    _avisar(db, empresa_id, fila, "Su compra fue cancelada" if fila.tipo != "RESERVA" else "Su reserva fue cancelada", texto)

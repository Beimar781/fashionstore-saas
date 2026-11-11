from decimal import Decimal

from sqlalchemy.orm import Session

from app.modules.acceso.publico import nombres_de_usuarios
from app.modules.offline.models import OperacionOffline
from app.modules.offline.schemas import OperacionOut, ResultadoOperacionOut
from app.modules.sucursales.publico import nombres_de_sucursales


def resultado_de(fila: OperacionOffline, ya_procesada: bool = False) -> ResultadoOperacionOut:
    return ResultadoOperacionOut(
        id=fila.operacion_id, estado=fila.estado, mensaje=fila.mensaje, referencia=fila.referencia, comprobante=fila.comprobante, detalle=fila.detalle, ya_procesada=ya_procesada,
    )


def _montos_de_venta(f: OperacionOffline) -> tuple[Decimal | None, Decimal | None]:
    """(a devolver, recibido) de una venta de contado sin conexión; (None, None) si no es una venta o si le faltan los precios con que se registró."""
    if f.tipo != "VENTA_CONTADO":
        return None, None
    items = (f.payload or {}).get("items") or []
    try:
        recibido = Decimal(str((f.payload or {}).get("monto_recibido"))).quantize(Decimal("0.01"))
        a_devolver = sum((Decimal(str(i["precio_unitario"])) * int(i["cantidad"]) for i in items), Decimal("0.00")).quantize(Decimal("0.01"))
    except (KeyError, TypeError, ArithmeticError, ValueError):
        return None, None
    return a_devolver, recibido


def operaciones_out(db: Session, empresa_id: int, filas: list[OperacionOffline]) -> list[OperacionOut]:
    sucursales = nombres_de_sucursales(db, empresa_id)
    usuarios = nombres_de_usuarios(db, empresa_id, {f.usuario_id for f in filas})
    return [
        OperacionOut(
            id=f.operacion_id, tipo=f.tipo, estado=f.estado, mensaje=f.mensaje, referencia=f.referencia, comprobante=f.comprobante, detalle=f.detalle, sucursal_id=f.sucursal_id,
            sucursal=sucursales.get(f.sucursal_id, ""), usuario=usuarios.get(f.usuario_id, ""), creada_en=f.creada_en_cliente, procesada_en=f.procesada_en, intentos=f.intentos,
            resolucion=f.resolucion, motivo_resolucion=f.motivo_resolucion,
            **dict(zip(("monto_a_devolver", "efectivo_recibido"), _montos_de_venta(f))),
        )
        for f in filas
    ]

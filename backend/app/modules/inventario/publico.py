"""Interfaz pública del paquete P5 inventario para otros paquetes (catálogo, reservas, ventas...)."""
from collections.abc import Iterable

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.inventario.cu26_inventario_sucursal.service import InventarioService
from app.modules.inventario.models import Existencia
from app.primer_parcial.catalogo.publico import Variante


def disponible_por_variante(db: Session, empresa_id: int, variante_ids: Iterable[int], sucursal_id: int | None = None) -> dict[int, int]:
    """Unidades disponibles de cada variante, en UNA consulta agrupada. Sin sucursal suma las de toda la empresa."""
    ids = list(variante_ids)
    if not ids:
        return {}
    stmt = (
        select(Existencia.variante_id, func.sum(Existencia.disponible))
        .where(Existencia.empresa_id == empresa_id, Existencia.variante_id.in_(ids))
        .group_by(Existencia.variante_id)
    )
    if sucursal_id is not None:
        stmt = stmt.where(Existencia.sucursal_id == sucursal_id)
    return {variante_id: int(cantidad) for variante_id, cantidad in db.execute(stmt)}


def variantes_con_stock(empresa_id: int, sucursal_id: int | None):
    """Condición SQL «la variante tiene unidades disponibles» (en una sucursal o en cualquiera), para usar en filtros."""
    condiciones = [Existencia.variante_id == Variante.id, Existencia.empresa_id == empresa_id, Existencia.disponible > 0]
    if sucursal_id is not None:
        condiciones.append(Existencia.sucursal_id == sucursal_id)
    return select(1).where(*condiciones).exists()


def aplicar_movimientos(
    db: Session, empresa_id: int, sucursal_id: int, lineas: list[tuple[int, int]], tipo: str, referencia_tipo: str,
    referencia_id: int | None = None, usuario_id: int | None = None, nota: str = "",
) -> None:
    """Único camino para cambiar existencias (reservas, ventas, devoluciones, recepciones): valida y deja bitácora.
    No hace commit: lo hace el caso de uso que lo llama, para que todo sea una sola transacción."""
    InventarioService(db, empresa_id).aplicar_movimientos(sucursal_id, lineas, tipo, referencia_tipo, referencia_id, usuario_id, nota)

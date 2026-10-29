from sqlalchemy.orm import selectinload

from app.core.tenant import TenantRepository
from app.primer_parcial.catalogo.publico import Producto, Variante


class VarianteVentaRepository(TenantRepository[Variante]):
    """Prendas del catálogo de la empresa, solo lectura: lo que se puede poner en una venta."""

    model = Variante

    def con_producto(self, ids: set[int]) -> dict[int, Variante]:
        if not ids:
            return {}
        stmt = self._consulta().where(Variante.id.in_(ids)).options(selectinload(Variante.producto))
        return {v.id: v for v in self.db.scalars(stmt)}

    def vendibles(self, ids: set[int]) -> dict[int, Variante]:
        """Variantes activas de productos activos."""
        stmt = (
            self._consulta().join(Producto, Producto.id == Variante.producto_id)
            .where(Variante.id.in_(ids), Variante.activa.is_(True), Producto.activo.is_(True)).options(selectinload(Variante.producto))
        )
        return {v.id: v for v in self.db.scalars(stmt)}

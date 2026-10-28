from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.core.tenant import TenantRepository
from app.modules.inventario.models import Existencia
from app.primer_parcial.catalogo.publico import Producto


class DisponibilidadRepository(TenantRepository[Producto]):
    model = Producto

    def producto_visible(self, producto_id: int) -> Producto | None:
        stmt = self._consulta().where(Producto.id == producto_id, Producto.activo.is_(True)).options(selectinload(Producto.variantes))
        return self.db.scalar(stmt)

    def unidades_por_sucursal(self, variante_ids: list[int]) -> dict[tuple[int, int], int]:
        """{(sucursal, variante): unidades disponibles} de todas las sucursales, en una sola consulta agrupada."""
        stmt = (
            select(Existencia.sucursal_id, Existencia.variante_id, func.sum(Existencia.disponible))
            .where(Existencia.empresa_id == self.empresa_id, Existencia.variante_id.in_(variante_ids))
            .group_by(Existencia.sucursal_id, Existencia.variante_id)
        )
        return {(s, v): int(c) for s, v, c in self.db.execute(stmt)}

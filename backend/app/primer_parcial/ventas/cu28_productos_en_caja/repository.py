from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.core.tenant import TenantRepository
from app.primer_parcial.catalogo.publico import ImagenProducto, Producto, Variante


class CajaRepository(TenantRepository[Variante]):
    """Prendas que el cajero puede vender: variantes activas de productos activos de su empresa."""

    model = Variante

    def _vendibles(self):
        return (
            self._consulta().join(Producto, Producto.id == Variante.producto_id)
            .where(Variante.activa.is_(True), Producto.activo.is_(True)).options(selectinload(Variante.producto))
        )

    def buscar(self, q: str, limite: int) -> list[Variante]:
        patron = f"%{q.strip().lower()}%"
        stmt = self._vendibles().where(or_(
            func.lower(Producto.nombre).like(patron), func.lower(Variante.sku).like(patron), func.lower(func.coalesce(Variante.codigo_barras, "")).like(patron),
        )).order_by(Producto.nombre, Variante.talla_id, Variante.color_id).limit(limite)
        return list(self.db.scalars(stmt))

    def por_codigo(self, codigo: str) -> Variante | None:
        """El lector de código de barras entrega el código de barras o el SKU de la prenda."""
        codigo = codigo.strip().lower()
        stmt = self._vendibles().where(or_(func.lower(Variante.sku) == codigo, func.lower(Variante.codigo_barras) == codigo)).limit(1)
        return self.db.scalar(stmt)

    def imagenes_principales(self, producto_ids: set[int]) -> dict[int, str]:
        if not producto_ids:
            return {}
        stmt = select(ImagenProducto.producto_id, ImagenProducto.ruta).where(
            ImagenProducto.empresa_id == self.empresa_id, ImagenProducto.producto_id.in_(producto_ids), ImagenProducto.principal.is_(True)
        )
        return {producto_id: ruta for producto_id, ruta in self.db.execute(stmt)}

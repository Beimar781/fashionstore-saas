from sqlalchemy import select

from app.core.tenant import TenantRepository
from app.primer_parcial.catalogo.publico import Categoria, Color, Producto, Talla, Variante
from app.primer_parcial.ia.models import ArAsset


class ArAssetRepository(TenantRepository[ArAsset]):
    model = ArAsset

    def de_producto(self, producto_id: int) -> dict[int, ArAsset]:
        """Los recursos del producto por color."""
        return {a.color_id: a for a in self.db.scalars(self._consulta().where(ArAsset.producto_id == producto_id))}

    def por_color(self, producto_id: int, color_id: int) -> ArAsset | None:
        return self.db.scalar(self._consulta().where(ArAsset.producto_id == producto_id, ArAsset.color_id == color_id))

    # ---- lectura del catálogo (solo de esta empresa) ----
    def producto(self, producto_id: int) -> Producto | None:
        return self.db.scalar(select(Producto).where(Producto.empresa_id == self.empresa_id, Producto.id == producto_id))

    def nombres_de_categoria(self, categoria_id: int) -> list[str]:
        """El nombre de la categoría y los de sus categorías superiores."""
        nombres: list[str] = []
        actual = self.db.scalar(select(Categoria).where(Categoria.empresa_id == self.empresa_id, Categoria.id == categoria_id))
        while actual is not None and len(nombres) < 10:
            nombres.append(actual.nombre)
            actual = self.db.scalar(select(Categoria).where(Categoria.empresa_id == self.empresa_id, Categoria.id == actual.padre_id)) if actual.padre_id else None
        return nombres

    def colores(self, producto_id: int) -> list[Color]:
        stmt = (
            select(Color).join(Variante, Variante.color_id == Color.id)
            .where(Variante.empresa_id == self.empresa_id, Variante.producto_id == producto_id, Variante.activa.is_(True)).distinct().order_by(Color.nombre)
        )
        return list(self.db.scalars(stmt))

    def tallas(self, producto_id: int) -> list[str]:
        stmt = (
            select(Talla.codigo).join(Variante, Variante.talla_id == Talla.id)
            .where(Variante.empresa_id == self.empresa_id, Variante.producto_id == producto_id, Variante.activa.is_(True)).distinct().order_by(Talla.codigo)
        )
        return list(self.db.scalars(stmt))

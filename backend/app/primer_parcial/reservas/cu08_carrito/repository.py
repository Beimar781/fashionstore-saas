from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.tenant import TenantRepository
from app.primer_parcial.catalogo.publico import ImagenProducto, Variante
from app.primer_parcial.reservas.models import Carrito, CarritoItem


class CarritoRepository(TenantRepository[Carrito]):
    model = Carrito

    def de_cliente(self, cliente_id: int) -> Carrito | None:
        """Cada cliente tiene su carrito dentro de su empresa: nunca se mezcla con el de otro cliente ni el de otra empresa."""
        stmt = self._consulta().where(Carrito.cliente_id == cliente_id).options(selectinload(Carrito.items))
        return self.db.scalar(stmt)

    def crear(self, cliente_id: int) -> Carrito:
        return self.agregar(Carrito(cliente_id=cliente_id))

    def agregar_item(self, carrito: Carrito, variante_id: int, cantidad: int) -> CarritoItem:
        item = CarritoItem(empresa_id=self.empresa_id, variante_id=variante_id, cantidad=cantidad)
        carrito.items.append(item)
        return item


class VarianteCarritoRepository(TenantRepository[Variante]):
    """Variantes y fotos del catálogo, solo lectura."""

    model = Variante

    def con_producto(self, ids: set[int]) -> dict[int, Variante]:
        if not ids:
            return {}
        stmt = self._consulta().where(Variante.id.in_(ids)).options(selectinload(Variante.producto))
        return {v.id: v for v in self.db.scalars(stmt)}

    def imagenes_principales(self, producto_ids: set[int]) -> dict[int, str]:
        if not producto_ids:
            return {}
        stmt = select(ImagenProducto.producto_id, ImagenProducto.ruta).where(
            ImagenProducto.empresa_id == self.empresa_id, ImagenProducto.producto_id.in_(producto_ids), ImagenProducto.principal.is_(True)
        )
        return {producto_id: ruta for producto_id, ruta in self.db.execute(stmt)}

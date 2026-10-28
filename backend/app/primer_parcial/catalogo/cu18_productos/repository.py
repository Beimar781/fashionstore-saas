from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.core.tenant import TenantRepository
from app.primer_parcial.catalogo.models import ImagenProducto, Producto, Variante


class ProductoRepository(TenantRepository[Producto]):
    model = Producto

    def obtener_completo(self, producto_id: int) -> Producto | None:
        stmt = self._consulta().where(Producto.id == producto_id).options(
            selectinload(Producto.variantes), selectinload(Producto.imagenes)
        )
        return self.db.scalar(stmt)

    def buscar(self, q: str | None, categoria_id: int | None, activo: bool | None, pagina: int, tamano: int) -> tuple[int, list[Producto]]:
        stmt = self._consulta()
        if q:
            patron = f"%{q.strip().lower()}%"
            stmt = stmt.where(or_(func.lower(Producto.nombre).like(patron), func.lower(Producto.slug).like(patron)))
        if categoria_id is not None:
            stmt = stmt.where(Producto.categoria_id == categoria_id)
        if activo is not None:
            stmt = stmt.where(Producto.activo.is_(activo))
        total = self.db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        stmt = stmt.order_by(Producto.creado_en.desc(), Producto.id.desc()).limit(tamano).offset((pagina - 1) * tamano)
        stmt = stmt.options(selectinload(Producto.variantes), selectinload(Producto.imagenes))
        return total, list(self.db.scalars(stmt))

    def slug_libre(self, base: str) -> str:
        slug, n = base, 1
        while self.db.scalar(self._consulta().where(Producto.slug == slug).limit(1)) is not None:
            n += 1
            slug = f"{base}-{n}"
        return slug


class VarianteRepository(TenantRepository[Variante]):
    model = Variante

    def existe_sku(self, sku: str) -> bool:
        return self.db.scalar(self._consulta().where(Variante.sku == sku).limit(1)) is not None

    def existe_barras(self, codigo: str, excluir_id: int) -> bool:
        stmt = self._consulta().where(Variante.codigo_barras == codigo, Variante.id != excluir_id)
        return self.db.scalar(stmt.limit(1)) is not None


class ImagenRepository(TenantRepository[ImagenProducto]):
    model = ImagenProducto

    def siguiente_orden(self, producto_id: int) -> int:
        maximo = self.db.scalar(
            select(func.max(ImagenProducto.orden)).where(ImagenProducto.empresa_id == self.empresa_id, ImagenProducto.producto_id == producto_id)
        )
        return 0 if maximo is None else maximo + 1

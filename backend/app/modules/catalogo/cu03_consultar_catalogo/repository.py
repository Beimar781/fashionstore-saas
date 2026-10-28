from collections import defaultdict

from sqlalchemy import Select, exists, func, select
from sqlalchemy.orm import selectinload

from app.core.tenant import TenantRepository
from app.primer_parcial.catalogo.publico import Categoria, Producto, Variante


class CatalogoRepository(TenantRepository[Producto]):
    """Catálogo visible al público: productos activos con al menos una variante activa."""

    model = Producto

    def con_variante(self, *condiciones):
        """Una sola condición sobre LA MISMA variante activa (así talla + color no se mezclan entre variantes)."""
        return exists().where(Variante.producto_id == Producto.id, Variante.activa.is_(True), *condiciones)

    def visibles(self) -> Select:
        return self._consulta().where(Producto.activo.is_(True), self.con_variante())

    def pagina(self, stmt: Select, pagina: int, tamano: int) -> tuple[int, list[Producto]]:
        total = self.db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
        stmt = stmt.limit(tamano).offset((pagina - 1) * tamano)
        stmt = stmt.options(selectinload(Producto.variantes), selectinload(Producto.imagenes))
        return total, list(self.db.scalars(stmt))

    def listar(self, categoria_ids: list[int] | None, pagina: int, tamano: int) -> tuple[int, list[Producto]]:
        stmt = self.visibles().order_by(Producto.creado_en.desc(), Producto.id.desc())
        if categoria_ids is not None:
            stmt = stmt.where(Producto.categoria_id.in_(categoria_ids))
        return self.pagina(stmt, pagina, tamano)

    def obtener_visible(self, producto_id: int) -> Producto | None:
        stmt = self.visibles().where(Producto.id == producto_id).options(
            selectinload(Producto.variantes), selectinload(Producto.imagenes)
        )
        return self.db.scalar(stmt)

    def categoria_y_subcategorias(self, categoria_id: int) -> list[int]:
        hijas = defaultdict(list)
        for id_, padre_id in self.db.execute(select(Categoria.id, Categoria.padre_id).where(Categoria.empresa_id == self.empresa_id)):
            hijas[padre_id].append(id_)
        pendientes, ids = [categoria_id], []
        while pendientes:
            actual = pendientes.pop()
            ids.append(actual)
            pendientes.extend(hijas[actual])
        return ids

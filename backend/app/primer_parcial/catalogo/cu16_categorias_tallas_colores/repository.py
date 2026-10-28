from sqlalchemy import func, select

from app.core.tenant import TenantRepository
from app.primer_parcial.catalogo.models import Categoria, Color, GrupoTalla, ImagenProducto, Marca, Producto, Talla, Variante


class _PorNombre:
    """Búsqueda sin distinguir mayúsculas, común a los atributos con nombre o slug."""

    def existe(self, excluir_id: int | None = None, **campos) -> bool:
        condiciones = [func.lower(getattr(self.model, c)) == v.lower() for c, v in campos.items()]  # type: ignore[attr-defined]
        stmt = self._consulta().where(*condiciones)  # type: ignore[attr-defined]
        if excluir_id is not None:
            stmt = stmt.where(self.model.id != excluir_id)  # type: ignore[attr-defined]
        return self.db.scalar(stmt.limit(1)) is not None  # type: ignore[attr-defined]


def _cuenta(db, modelo, *condiciones) -> bool:
    return bool(db.scalar(select(func.count()).select_from(modelo).where(*condiciones)))


class CategoriaRepository(_PorNombre, TenantRepository[Categoria]):
    model = Categoria

    def ordenadas(self, solo_activas: bool) -> list[Categoria]:
        stmt = self._consulta().order_by(Categoria.orden, Categoria.nombre)
        return list(self.db.scalars(stmt.where(Categoria.activa.is_(True)) if solo_activas else stmt))

    def en_uso(self, categoria_id: int) -> bool:
        return _cuenta(self.db, Categoria, Categoria.padre_id == categoria_id) or _cuenta(
            self.db, Producto, Producto.categoria_id == categoria_id
        )


class GrupoTallaRepository(_PorNombre, TenantRepository[GrupoTalla]):
    model = GrupoTalla

    def en_uso(self, grupo_id: int) -> bool:
        return _cuenta(self.db, Talla, Talla.grupo_id == grupo_id) or _cuenta(
            self.db, Categoria, Categoria.grupo_talla_id == grupo_id
        )


class TallaRepository(TenantRepository[Talla]):
    model = Talla

    def ordenadas(self) -> list[Talla]:
        return list(self.db.scalars(self._consulta().order_by(Talla.grupo_id, Talla.orden, Talla.codigo)))

    def existe_codigo(self, grupo_id: int, codigo: str, excluir_id: int | None = None) -> bool:
        stmt = self._consulta().where(Talla.grupo_id == grupo_id, func.lower(Talla.codigo) == codigo.lower())
        if excluir_id is not None:
            stmt = stmt.where(Talla.id != excluir_id)
        return self.db.scalar(stmt.limit(1)) is not None

    def siguiente_orden(self, grupo_id: int) -> int:
        maximo = self.db.scalar(select(func.max(Talla.orden)).where(Talla.empresa_id == self.empresa_id, Talla.grupo_id == grupo_id))
        return 0 if maximo is None else maximo + 1

    def en_uso(self, talla_id: int) -> bool:
        return _cuenta(self.db, Variante, Variante.talla_id == talla_id)


class ColorRepository(_PorNombre, TenantRepository[Color]):
    model = Color

    def ordenados(self) -> list[Color]:
        return list(self.db.scalars(self._consulta().order_by(Color.nombre)))

    def en_uso(self, color_id: int) -> bool:
        return _cuenta(self.db, Variante, Variante.color_id == color_id) or _cuenta(
            self.db, ImagenProducto, ImagenProducto.color_id == color_id
        )


class MarcaRepository(_PorNombre, TenantRepository[Marca]):
    model = Marca

    def ordenadas(self) -> list[Marca]:
        return list(self.db.scalars(self._consulta().order_by(Marca.nombre)))

    def en_uso(self, marca_id: int) -> bool:
        return _cuenta(self.db, Producto, Producto.marca_id == marca_id)

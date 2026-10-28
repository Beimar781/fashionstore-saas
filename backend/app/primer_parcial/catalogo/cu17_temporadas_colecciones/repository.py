from sqlalchemy import func, select

from app.core.tenant import TenantRepository
from app.primer_parcial.catalogo.models import Coleccion, Producto, Temporada


class TemporadaRepository(TenantRepository[Temporada]):
    model = Temporada

    def ordenadas(self, solo_activas: bool) -> list[Temporada]:
        stmt = self._consulta().order_by(Temporada.inicio.desc())
        return list(self.db.scalars(stmt.where(Temporada.activa.is_(True)) if solo_activas else stmt))

    def existe_codigo(self, codigo: str, excluir_id: int | None = None) -> bool:
        stmt = self._consulta().where(func.lower(Temporada.codigo) == codigo.lower())
        if excluir_id is not None:
            stmt = stmt.where(Temporada.id != excluir_id)
        return self.db.scalar(stmt.limit(1)) is not None

    def en_uso(self, temporada_id: int) -> bool:
        return bool(self.db.scalar(select(func.count()).select_from(Coleccion).where(Coleccion.temporada_id == temporada_id)))


class ColeccionRepository(TenantRepository[Coleccion]):
    model = Coleccion

    def ordenadas(self, solo_activas: bool, temporada_id: int | None) -> list[Coleccion]:
        stmt = self._consulta().order_by(Coleccion.fecha_lanzamiento.desc().nulls_last(), Coleccion.nombre)
        if solo_activas:
            stmt = stmt.where(Coleccion.activa.is_(True))
        if temporada_id is not None:
            stmt = stmt.where(Coleccion.temporada_id == temporada_id)
        return list(self.db.scalars(stmt))

    def existe_slug(self, slug: str, excluir_id: int | None = None) -> bool:
        stmt = self._consulta().where(Coleccion.slug == slug)
        if excluir_id is not None:
            stmt = stmt.where(Coleccion.id != excluir_id)
        return self.db.scalar(stmt.limit(1)) is not None

    def en_uso(self, coleccion_id: int) -> bool:
        return bool(self.db.scalar(select(func.count()).select_from(Producto).where(Producto.coleccion_id == coleccion_id)))

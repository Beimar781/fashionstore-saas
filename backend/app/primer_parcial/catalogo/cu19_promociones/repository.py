from datetime import date

from sqlalchemy import func, select

from app.core.tenant import TenantRepository
from app.primer_parcial.catalogo.models import Categoria, Promocion


class PromocionRepository(TenantRepository[Promocion]):
    model = Promocion

    def ordenadas(self, solo_vigentes: bool, hoy: date) -> list[Promocion]:
        stmt = self._consulta().order_by(Promocion.inicia.desc(), Promocion.id.desc())
        if solo_vigentes:
            stmt = stmt.where(Promocion.activa.is_(True), Promocion.inicia <= hoy, Promocion.termina >= hoy)
        return list(self.db.scalars(stmt))

    def automaticas_vigentes(self, hoy: date) -> list[Promocion]:
        stmt = self._consulta().where(
            Promocion.activa.is_(True), Promocion.codigo.is_(None), Promocion.inicia <= hoy, Promocion.termina >= hoy
        )
        return list(self.db.scalars(stmt))

    def existe_codigo(self, codigo: str, excluir_id: int | None = None) -> bool:
        stmt = self._consulta().where(func.upper(Promocion.codigo) == codigo.upper())
        if excluir_id is not None:
            stmt = stmt.where(Promocion.id != excluir_id)
        return self.db.scalar(stmt.limit(1)) is not None

    def padres_de_categorias(self) -> dict[int, int | None]:
        """{categoría: categoría padre} de la empresa, para que una promoción de «Camisas» alcance sus subcategorías."""
        filas = self.db.execute(select(Categoria.id, Categoria.padre_id).where(Categoria.empresa_id == self.empresa_id))
        return {id_: padre for id_, padre in filas}

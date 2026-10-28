from sqlalchemy import func, or_, select

from app.core.tenant import TenantRepository
from app.primer_parcial.proveedores.models import Lote, Proveedor


class ProveedorRepository(TenantRepository[Proveedor]):
    model = Proveedor

    def ordenados(self, solo_activos: bool, q: str | None) -> list[Proveedor]:
        stmt = self._consulta().order_by(Proveedor.razon_social)
        if solo_activos:
            stmt = stmt.where(Proveedor.activo.is_(True))
        if q:
            patron = f"%{q.strip().lower()}%"
            stmt = stmt.where(or_(
                func.lower(Proveedor.razon_social).like(patron), func.lower(Proveedor.nombre_comercial).like(patron),
                func.lower(func.coalesce(Proveedor.nit, "")).like(patron),
            ))
        return list(self.db.scalars(stmt))

    def existe_nit(self, nit: str, excluir_id: int | None = None) -> bool:
        stmt = self._consulta().where(func.lower(Proveedor.nit) == nit.lower())
        if excluir_id is not None:
            stmt = stmt.where(Proveedor.id != excluir_id)
        return self.db.scalar(stmt.limit(1)) is not None

    def de_usuario(self, usuario_id: int) -> Proveedor | None:
        """El proveedor al que pertenece la cuenta del portal."""
        return self.db.scalar(self._consulta().where(Proveedor.usuario_id == usuario_id))

    def tiene_lotes_en_transito(self, proveedor_id: int) -> bool:
        stmt = select(func.count()).select_from(Lote).where(
            Lote.empresa_id == self.empresa_id, Lote.proveedor_id == proveedor_id, Lote.estado == "EN_TRANSITO"
        )
        return bool(self.db.scalar(stmt))

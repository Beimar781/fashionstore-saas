from sqlalchemy import func, select

from app.core.tenant import TenantRepository
from app.modules.sucursales.models import Ciudad, Sucursal


class CiudadRepository(TenantRepository[Ciudad]):
    model = Ciudad

    def por_nombre(self, nombre: str) -> Ciudad | None:
        return self.db.scalar(self._consulta().where(func.lower(Ciudad.nombre) == nombre.lower()))


class SucursalRepository(TenantRepository[Sucursal]):
    model = Sucursal

    def existe_nombre(self, nombre: str, excluir_id: int | None = None) -> bool:
        stmt = self._consulta().where(func.lower(Sucursal.nombre) == nombre.lower())
        if excluir_id is not None:
            stmt = stmt.where(Sucursal.id != excluir_id)
        return self.db.scalar(stmt.limit(1)) is not None

    def contar_activas(self) -> int:
        return self.db.scalar(
            select(func.count()).select_from(Sucursal).where(Sucursal.empresa_id == self.empresa_id, Sucursal.activa.is_(True))
        ) or 0

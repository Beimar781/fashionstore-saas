from sqlalchemy import select

from app.core.tenant import TenantRepository
from app.modules.ia.models import ReporteGenerado


class ReporteRepository(TenantRepository[ReporteGenerado]):
    model = ReporteGenerado

    def recientes(self, limite: int = 30) -> list[ReporteGenerado]:
        return list(self.db.scalars(self._consulta().order_by(ReporteGenerado.creado_en.desc(), ReporteGenerado.id.desc()).limit(limite)))

    def con_id(self, reporte_id: int) -> ReporteGenerado | None:
        return self.db.scalar(select(ReporteGenerado).where(ReporteGenerado.empresa_id == self.empresa_id, ReporteGenerado.id == reporte_id))

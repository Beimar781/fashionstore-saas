from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.constantes import SUS_ACTIVA
from app.modules.plataforma.models import Plan, Suscripcion


class PlanRepository:
    def __init__(self, db: Session):
        self.db = db

    def obtener(self, plan_id: int) -> Plan | None:
        return self.db.get(Plan, plan_id)

    def por_nombre(self, nombre: str) -> Plan | None:
        return self.db.scalar(select(Plan).where(func.lower(Plan.nombre) == nombre.lower()))

    def listar_con_empresas_suscritas(self) -> list[tuple[Plan, int]]:
        """Una sola consulta: cada plan con el número de empresas que lo tienen vigente (RNF09)."""
        stmt = (
            select(Plan, func.count(Suscripcion.id))
            .outerjoin(Suscripcion, (Suscripcion.plan_id == Plan.id) & (Suscripcion.estado == SUS_ACTIVA))
            .group_by(Plan.id)
            .order_by(Plan.precio, Plan.id)
        )
        return [(p, int(n)) for p, n in self.db.execute(stmt)]

    def contar_empresas_suscritas(self, plan_id: int) -> int:
        return self.db.scalar(
            select(func.count()).select_from(Suscripcion).where(
                Suscripcion.plan_id == plan_id, Suscripcion.estado == SUS_ACTIVA
            )
        ) or 0

    def agregar(self, plan: Plan) -> Plan:
        self.db.add(plan)
        self.db.flush()
        return plan

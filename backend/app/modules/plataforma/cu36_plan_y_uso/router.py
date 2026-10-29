from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.constantes import ADMIN
from app.core.database import get_db
from app.modules.acceso.dependencias import Contexto, requerir_roles
from app.modules.plataforma.cu36_plan_y_uso import schemas
from app.modules.plataforma.cu36_plan_y_uso.service import PlanYUsoService

router = APIRouter(prefix="/mi-plan", tags=["CU-36 Plan, límites y uso de la empresa"])


@router.get("", response_model=schemas.MiPlanOut)
def plan_limites_y_uso(ctx: Contexto = Depends(requerir_roles(ADMIN)), db: Session = Depends(get_db)):
    """Plan contratado, vigencia, límites con su uso, consumo de la empresa y funcionalidades incluidas."""
    return PlanYUsoService(db, ctx).detalle()

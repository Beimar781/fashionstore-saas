from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.constantes import SUPERADMIN
from app.core.database import get_db
from app.modules.acceso.dependencias import requerir_roles
from app.modules.plataforma.cu34_planes import schemas
from app.modules.plataforma.cu34_planes.service import PlanService

router = APIRouter(prefix="/plataforma/planes", tags=["CU-34 Planes de suscripción"], dependencies=[Depends(requerir_roles(SUPERADMIN))])


@router.get("", response_model=list[schemas.PlanOut])
def listar_planes(db: Session = Depends(get_db)):
    return PlanService(db).listar()


@router.post("", response_model=schemas.PlanGuardadoOut, status_code=201)
def crear_plan(datos: schemas.PlanCreate, db: Session = Depends(get_db)):
    return PlanService(db).crear(datos)


@router.put("/{plan_id}", response_model=schemas.PlanGuardadoOut)
def modificar_plan(plan_id: int, datos: schemas.PlanUpdate, db: Session = Depends(get_db)):
    return PlanService(db).modificar(plan_id, datos)


@router.post("/{plan_id}/inactivar", response_model=schemas.PlanOut)
def inactivar_plan(plan_id: int, db: Session = Depends(get_db)):
    return PlanService(db).inactivar(plan_id)

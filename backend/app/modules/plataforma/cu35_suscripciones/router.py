from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.constantes import SUPERADMIN
from app.core.database import get_db
from app.modules.acceso.dependencias import requerir_roles
from app.modules.plataforma.cu35_suscripciones import schemas
from app.modules.plataforma.cu35_suscripciones.service import SuscripcionService

router = APIRouter(
    prefix="/plataforma/empresas/{empresa_id}",
    tags=["CU-35 Suscripciones de empresas"],
    dependencies=[Depends(requerir_roles(SUPERADMIN))],
)


@router.get("/suscripcion", response_model=schemas.SuscripcionDetalleOut)
def consultar_suscripcion(empresa_id: int, db: Session = Depends(get_db)):
    return SuscripcionService(db).detalle(empresa_id)


@router.post("/suscripciones", response_model=schemas.SuscripcionOut, status_code=201)
def asignar_cambiar_o_renovar(empresa_id: int, datos: schemas.SuscripcionIn, db: Session = Depends(get_db)):
    return SuscripcionService(db).asignar(empresa_id, datos)


@router.post("/suscripcion/suspender", response_model=schemas.SuscripcionOut)
def suspender_o_cancelar(empresa_id: int, datos: schemas.SuscripcionEstadoIn | None = None, db: Session = Depends(get_db)):
    estado = datos.estado if datos else "SUSPENDIDA"
    return SuscripcionService(db).cambiar_estado(empresa_id, estado)

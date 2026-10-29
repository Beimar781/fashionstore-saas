from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.constantes import CAJERO, CLIENTE, ENCARGADO
from app.core.database import get_db
from app.modules.acceso.dependencias import Contexto
from app.modules.offline import schemas
from app.modules.offline.cu39_operaciones.service import OperacionesService
from app.modules.plataforma.publico import contexto_operativo, exigir_funcionalidad

router = APIRouter(prefix="/offline", tags=["CU-39 Consultar operaciones locales y su estado"], dependencies=[Depends(exigir_funcionalidad("offline"))])


@router.get("/operaciones", response_model=list[schemas.OperacionOut])
def mis_operaciones_sincronizadas(ctx: Contexto = Depends(contexto_operativo(CLIENTE, CAJERO, ENCARGADO)), db: Session = Depends(get_db)):
    """Estado en el servidor de las operaciones del usuario: confirmada, rechazada o en conflicto."""
    return OperacionesService(db, ctx).mias()

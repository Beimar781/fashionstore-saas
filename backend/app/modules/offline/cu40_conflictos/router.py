import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.constantes import ADMIN, ENCARGADO
from app.core.database import get_db
from app.modules.acceso.dependencias import Contexto
from app.modules.offline import schemas
from app.modules.offline.cu40_conflictos import schemas as esquemas
from app.modules.offline.cu40_conflictos.service import ConflictosService
from app.modules.plataforma.publico import contexto_operativo, exigir_funcionalidad

router = APIRouter(prefix="/offline/conflictos", tags=["CU-40 Gestionar conflictos de sincronización"], dependencies=[Depends(exigir_funcionalidad("offline"))])
gestor = contexto_operativo(ENCARGADO, ADMIN)


@router.get("", response_model=list[schemas.OperacionOut])
def operaciones_en_conflicto(ctx: Contexto = Depends(gestor), db: Session = Depends(get_db)):
    """Operaciones offline que no se pudieron aplicar por falta de existencias (el Encargado ve las de su sucursal)."""
    return ConflictosService(db, ctx).listar()


@router.post("/{operacion_id}/resolver", response_model=schemas.OperacionOut)
def resolver_conflicto(operacion_id: uuid.UUID, datos: esquemas.ResolverIn, ctx: Contexto = Depends(gestor), db: Session = Depends(get_db)):
    """Reintentar la operación con las existencias de ahora, o descartarla con un motivo."""
    return ConflictosService(db, ctx).resolver(operacion_id, datos)

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.constantes import CAJERO, CLIENTE, ENCARGADO
from app.core.database import get_db
from app.modules.acceso.dependencias import Contexto
from app.modules.offline.cu37_catalogo_offline import schemas
from app.modules.offline.cu37_catalogo_offline.service import CatalogoOfflineService
from app.modules.plataforma.publico import contexto_operativo, exigir_funcionalidad

router = APIRouter(prefix="/offline", tags=["CU-37 Descargar catálogo para uso offline"], dependencies=[Depends(exigir_funcionalidad("offline"))])


@router.get("/catalogo", response_model=schemas.CatalogoLocalOut)
def descargar_catalogo(ctx: Contexto = Depends(contexto_operativo(CLIENTE, CAJERO, ENCARGADO)), db: Session = Depends(get_db)):
    """Catálogo, precios, stock y (para el personal) clientes de las sucursales autorizadas, para guardarlos en el dispositivo."""
    return CatalogoOfflineService(db, ctx).descargar()

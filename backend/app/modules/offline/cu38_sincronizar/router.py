from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.constantes import CAJERO, CLIENTE, ENCARGADO
from app.core.database import get_db
from app.modules.acceso.dependencias import Contexto
from app.modules.offline import schemas
from app.modules.offline.cu38_sincronizar.service import SincronizacionService
from app.modules.plataforma.publico import contexto_operativo, exigir_funcionalidad

router = APIRouter(prefix="/offline", tags=["CU-38 Sincronizar operaciones pendientes"], dependencies=[Depends(exigir_funcionalidad("offline"))])


@router.post("/sincronizar", response_model=schemas.SincronizacionOut)
def sincronizar_operaciones_pendientes(
    datos: schemas.SincronizarIn, ctx: Contexto = Depends(contexto_operativo(CLIENTE, CAJERO, ENCARGADO)), db: Session = Depends(get_db)
):
    """Recibe por lote las operaciones hechas sin conexión (ventas de contado y reservas). Reenviar una ya procesada devuelve su resultado original."""
    return SincronizacionService(db, ctx).sincronizar(datos)

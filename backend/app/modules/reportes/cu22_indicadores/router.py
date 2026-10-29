from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.constantes import ADMIN
from app.core.database import get_db
from app.modules.acceso.dependencias import Contexto
from app.modules.plataforma.publico import contexto_operativo, exigir_funcionalidad
from app.modules.reportes.cu22_indicadores import schemas
from app.modules.reportes.cu22_indicadores.service import IndicadoresService

router = APIRouter(prefix="/reportes", tags=["CU-22 Indicadores empresariales"], dependencies=[Depends(exigir_funcionalidad("reportes_convencionales"))])


@router.get("/indicadores", response_model=schemas.IndicadoresOut)
def indicadores_empresariales(
    dias: int = 30, sucursal: int | None = None, ctx: Contexto = Depends(contexto_operativo(ADMIN)), db: Session = Depends(get_db)
):
    """Panel del Administrador: ventas netas, pedidos, ticket, reservas, inventario y alertas, comparados con el periodo anterior."""
    return IndicadoresService(db, ctx).indicadores(dias, sucursal)

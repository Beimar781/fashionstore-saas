from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.constantes import ADMIN
from app.core.database import get_db
from app.modules.acceso.dependencias import Contexto
from app.modules.ia.cu42_analitica_ml import schemas
from app.modules.ia.cu42_analitica_ml.service import AnaliticaMLService
from app.modules.plataforma.publico import contexto_operativo, exigir_funcionalidad

router = APIRouter(prefix="/ia/analitica", tags=["CU-42 Analítica con Machine Learning"], dependencies=[Depends(exigir_funcionalidad("reportes_ia"))])


@router.get("", response_model=schemas.AnaliticaOut)
def dashboard_analitico(sucursal: int | None = None, ctx: Contexto = Depends(contexto_operativo(ADMIN)), db: Session = Depends(get_db)):
    """Rotación de productos (KMeans) y pronóstico de demanda a 4 semanas (regresión lineal), con recomendación de reposición."""
    return AnaliticaMLService(db, ctx).analitica(sucursal)

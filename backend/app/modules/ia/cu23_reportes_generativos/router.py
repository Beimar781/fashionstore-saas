from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.constantes import ADMIN
from app.core.database import get_db
from app.modules.acceso.dependencias import Contexto
from app.modules.ia.cu23_reportes_generativos import schemas
from app.modules.ia.cu23_reportes_generativos.service import ReporteGenerativoService
from app.modules.plataforma.publico import contexto_operativo, exigir_funcionalidad

router = APIRouter(prefix="/ia/reportes", tags=["CU-23 Reportes generativos"], dependencies=[Depends(exigir_funcionalidad("reportes_ia"))])
admin = contexto_operativo(ADMIN)


@router.post("", response_model=schemas.ReporteGenerativoOut, status_code=201)
def generar_reporte_por_prompt(datos: schemas.PromptIn, ctx: Contexto = Depends(admin), db: Session = Depends(get_db)):
    """El Administrador escribe (o dicta por voz) una petición y recibe el reporte interpretado y generado."""
    return ReporteGenerativoService(db, ctx).generar(datos)


@router.get("", response_model=list[schemas.ReporteGenerativoOut])
def historial_de_reportes(ctx: Contexto = Depends(admin), db: Session = Depends(get_db)):
    return ReporteGenerativoService(db, ctx).listar()


@router.get("/{reporte_id}", response_model=schemas.ReporteGenerativoOut)
def consultar_reporte(reporte_id: int, ctx: Contexto = Depends(admin), db: Session = Depends(get_db)):
    return ReporteGenerativoService(db, ctx).obtener(reporte_id)

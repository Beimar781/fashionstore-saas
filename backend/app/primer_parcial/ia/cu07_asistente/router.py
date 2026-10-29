from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.constantes import CLIENTE
from app.core.database import get_db
from app.modules.acceso.dependencias import Contexto
from app.modules.plataforma.publico import contexto_operativo, exigir_funcionalidad
from app.primer_parcial.ia.cu07_asistente import schemas
from app.primer_parcial.ia.cu07_asistente.service import AsistenteService

router = APIRouter(prefix="/asistente", tags=["CU-07 Asistente y recomendador"], dependencies=[Depends(exigir_funcionalidad("reportes_ia"))])
cliente = contexto_operativo(CLIENTE)


@router.post("/chat", response_model=schemas.ChatOut)
def conversar_con_el_asistente(datos: schemas.ChatIn, ctx: Contexto = Depends(cliente), db: Session = Depends(get_db)):
    """El cliente pide prendas en lenguaje natural y el asistente responde con prendas reales con stock."""
    return AsistenteService(db, ctx).chat(datos)


@router.get("/recomendaciones", response_model=schemas.RecomendacionesOut)
def recomendar_prendas(sucursal_id: int | None = None, limite: int = Query(6, ge=1, le=12), ctx: Contexto = Depends(cliente), db: Session = Depends(get_db)):
    """Prendas parecidas a lo que el cliente ya compró; si aún no compró, lo más vendido."""
    return AsistenteService(db, ctx).recomendaciones(sucursal_id, limite)

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.constantes import CLIENTE
from app.core.database import get_db
from app.modules.acceso.dependencias import Contexto
from app.modules.plataforma.publico import contexto_operativo
from app.modules.reservas.cu09_reservar import schemas
from app.modules.reservas.cu09_reservar.service import ReservaService

router = APIRouter(prefix="/reservas", tags=["CU-09 Reservar prendas"])
solo_cliente = contexto_operativo(CLIENTE)


@router.post("", response_model=schemas.ReservaOut, status_code=201)
def reservar_prendas(datos: schemas.ReservaIn, ctx: Contexto = Depends(solo_cliente), db: Session = Depends(get_db)):
    """Reserva varias prendas en una sucursal con un horario aproximado; el stock pasa de disponible a reservado."""
    return ReservaService(db, ctx.empresa_id).crear(ctx, datos)

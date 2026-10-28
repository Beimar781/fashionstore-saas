from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.constantes import CLIENTE
from app.core.database import get_db
from app.modules.acceso.dependencias import Contexto
from app.modules.plataforma.publico import contexto_operativo
from app.modules.reservas.cu09_reservar.schemas import ReservaOut
from app.modules.reservas.cu10_consultar_cancelar import schemas
from app.modules.reservas.cu10_consultar_cancelar.service import ReservaClienteService

router = APIRouter(prefix="/reservas", tags=["CU-10 Consultar y cancelar reservas"])
solo_cliente = contexto_operativo(CLIENTE)


@router.get("", response_model=list[ReservaOut])
def mis_reservas(estado: str | None = None, ctx: Contexto = Depends(solo_cliente), db: Session = Depends(get_db)):
    return ReservaClienteService(db, ctx).listar(estado)


@router.get("/{reserva_id}", response_model=ReservaOut)
def consultar_estado_de_una_reserva(reserva_id: int, ctx: Contexto = Depends(solo_cliente), db: Session = Depends(get_db)):
    return ReservaClienteService(db, ctx).obtener(reserva_id)


@router.post("/{reserva_id}/cancelar", response_model=ReservaOut)
def cancelar_reserva(reserva_id: int, datos: schemas.CancelacionIn, ctx: Contexto = Depends(solo_cliente), db: Session = Depends(get_db)):
    """Cancela una reserva pendiente o preparada y devuelve su stock a disponible."""
    return ReservaClienteService(db, ctx).cancelar(reserva_id, datos.motivo)

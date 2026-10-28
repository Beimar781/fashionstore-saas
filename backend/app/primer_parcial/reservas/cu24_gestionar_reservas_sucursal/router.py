from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.constantes import ENCARGADO
from app.core.database import get_db
from app.modules.acceso.dependencias import Contexto
from app.modules.plataforma.publico import contexto_operativo
from app.modules.reservas.publico import ReservaOut
from app.primer_parcial.reservas.cu24_gestionar_reservas_sucursal.service import ReservasSucursalService

router = APIRouter(prefix="/reservas-sucursal", tags=["CU-24 Gestionar reservas de la sucursal"])
solo_encargado = contexto_operativo(ENCARGADO)


@router.get("", response_model=list[ReservaOut])
def reservas_de_mi_sucursal(estado: str | None = None, fecha: date | None = None, ctx: Contexto = Depends(solo_encargado), db: Session = Depends(get_db)):
    """Reservas activas de la sucursal del Encargado, por horario; se puede filtrar por estado y por día."""
    return ReservasSucursalService(db, ctx).listar(estado, fecha)


@router.get("/{reserva_id}", response_model=ReservaOut)
def detalle_de_la_reserva(reserva_id: int, ctx: Contexto = Depends(solo_encargado), db: Session = Depends(get_db)):
    return ReservasSucursalService(db, ctx).obtener(reserva_id)


@router.post("/{reserva_id}/preparar", response_model=ReservaOut)
def marcar_prendas_preparadas(reserva_id: int, ctx: Contexto = Depends(solo_encargado), db: Session = Depends(get_db)):
    return ReservasSucursalService(db, ctx).preparar(reserva_id)


@router.post("/{reserva_id}/items/{item_id}/no-encontrado", response_model=ReservaOut)
def marcar_prenda_no_encontrada(reserva_id: int, item_id: int, ctx: Contexto = Depends(solo_encargado), db: Session = Depends(get_db)):
    return ReservasSucursalService(db, ctx).marcar_no_encontrado(reserva_id, item_id)

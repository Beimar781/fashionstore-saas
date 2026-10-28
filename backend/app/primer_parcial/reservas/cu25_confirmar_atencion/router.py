from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.constantes import ENCARGADO
from app.core.database import get_db
from app.modules.acceso.dependencias import Contexto
from app.modules.plataforma.publico import contexto_operativo
from app.modules.reservas.publico import ReservaOut
from app.primer_parcial.reservas.cu25_confirmar_atencion import schemas
from app.primer_parcial.reservas.cu25_confirmar_atencion.service import AtencionService

router = APIRouter(prefix="/atencion-reservas", tags=["CU-25 Confirmar recepción y atención"])
solo_encargado = contexto_operativo(ENCARGADO)


@router.post("/validar", response_model=ReservaOut)
def validar_codigo_de_reserva(datos: schemas.CodigoIn, ctx: Contexto = Depends(solo_encargado), db: Session = Depends(get_db)):
    """El cliente presenta su código en el mostrador: se valida que exista, esté vigente y sea de esta sucursal."""
    return AtencionService(db, ctx).validar_codigo(datos.codigo)


@router.post("/{reserva_id}/atender", response_model=ReservaOut)
def entregar_prendas_al_cliente(reserva_id: int, ctx: Contexto = Depends(solo_encargado), db: Session = Depends(get_db)):
    return AtencionService(db, ctx).atender(reserva_id)


@router.post("/{reserva_id}/completar", response_model=schemas.AtencionOut)
def completar_atencion(reserva_id: int, datos: schemas.CompletarIn, ctx: Contexto = Depends(solo_encargado), db: Session = Depends(get_db)):
    return AtencionService(db, ctx).completar(reserva_id, datos)

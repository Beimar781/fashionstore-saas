from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.constantes import CAJERO, ENCARGADO
from app.core.database import get_db
from app.modules.acceso.dependencias import Contexto
from app.modules.plataforma.publico import contexto_operativo
from app.modules.reservas.publico import ReservaOut
from app.modules.ventas.cu29_venta_presencial import schemas
from app.modules.ventas.cu29_venta_presencial.service import VentaPresencialService
from app.primer_parcial.ventas.publico import PedidoOut

router = APIRouter(prefix="/caja", tags=["CU-29 Venta presencial"])
en_caja = contexto_operativo(CAJERO, ENCARGADO)


@router.post("/ventas", response_model=PedidoOut, status_code=201)
def registrar_venta_presencial(datos: schemas.VentaIn, ctx: Contexto = Depends(en_caja), db: Session = Depends(get_db)):
    """Arma la venta de caja (con prendas escaneadas o desde una reserva preparada): queda pendiente de cobro."""
    return VentaPresencialService(db, ctx).crear(datos)


@router.get("/ventas/pendientes", response_model=list[PedidoOut])
def ventas_pendientes_de_cobro(ctx: Contexto = Depends(en_caja), db: Session = Depends(get_db)):
    return VentaPresencialService(db, ctx).pendientes()


@router.get("/ventas/{pedido_id}", response_model=PedidoOut)
def consultar_venta(pedido_id: int, ctx: Contexto = Depends(en_caja), db: Session = Depends(get_db)):
    return VentaPresencialService(db, ctx).obtener(pedido_id)


@router.delete("/ventas/{pedido_id}", response_model=PedidoOut)
def anular_venta_en_curso(pedido_id: int, ctx: Contexto = Depends(en_caja), db: Session = Depends(get_db)):
    return VentaPresencialService(db, ctx).anular(pedido_id)


@router.get("/reservas/{codigo}", response_model=ReservaOut)
def reserva_del_cliente(codigo: str, ctx: Contexto = Depends(en_caja), db: Session = Depends(get_db)):
    """La reserva que el cliente presenta en caja (preparada o en probador), con sus prendas."""
    return VentaPresencialService(db, ctx).reserva(codigo)

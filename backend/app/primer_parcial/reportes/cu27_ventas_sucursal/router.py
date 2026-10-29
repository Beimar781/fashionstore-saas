from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.constantes import ENCARGADO
from app.core.database import get_db
from app.modules.acceso.dependencias import Contexto
from app.modules.plataforma.publico import contexto_operativo
from app.primer_parcial.reportes.cu27_ventas_sucursal import schemas
from app.primer_parcial.reportes.cu27_ventas_sucursal.service import VentasSucursalService
from app.primer_parcial.ventas.publico import PedidoOut

router = APIRouter(prefix="/reportes/sucursal", tags=["CU-27 Ventas de la sucursal"])
solo_encargado = contexto_operativo(ENCARGADO)


@router.get("/resumen", response_model=schemas.ResumenDiaOut)
def resumen_del_dia(fecha: date | None = None, sucursal: int | None = None, ctx: Contexto = Depends(solo_encargado), db: Session = Depends(get_db)):
    """Resumen monetario y cierre de caja del día de la sucursal del Encargado (hoy, si no se indica fecha)."""
    return VentasSucursalService(db, ctx).resumen(fecha, sucursal)


@router.get("/ventas", response_model=schemas.VentasOut)
def tickets_de_la_sucursal(
    desde: date | None = None, hasta: date | None = None, canal: str | None = None, metodo: str | None = None, sucursal: int | None = None,
    ctx: Contexto = Depends(solo_encargado), db: Session = Depends(get_db),
):
    return VentasSucursalService(db, ctx).listar(desde, hasta, canal, metodo, sucursal)


@router.get("/ventas/{pedido_id}", response_model=PedidoOut)
def detalle_del_ticket(pedido_id: int, ctx: Contexto = Depends(solo_encargado), db: Session = Depends(get_db)):
    return VentasSucursalService(db, ctx).detalle(pedido_id)

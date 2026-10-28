from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.constantes import CLIENTE
from app.core.database import get_db
from app.modules.acceso.dependencias import Contexto
from app.modules.plataforma.publico import contexto_operativo
from app.primer_parcial.ventas.cu11_compra_digital import schemas
from app.primer_parcial.ventas.cu11_compra_digital.service import CompraService

router = APIRouter(prefix="/compras", tags=["CU-11 Compra digital"])
solo_cliente = contexto_operativo(CLIENTE)


@router.post("/checkout", response_model=schemas.PedidoOut, status_code=201)
def proceder_al_pago(datos: schemas.CheckoutIn, ctx: Contexto = Depends(solo_cliente), db: Session = Depends(get_db)):
    """Convierte el carrito en un pedido por pagar, con los datos de entrega o retiro y de facturación (NIT/CI)."""
    return CompraService(db, ctx).checkout(datos)

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.core.constantes import CAJERO, ENCARGADO
from app.core.database import get_db
from app.modules.acceso.dependencias import Contexto
from app.modules.plataforma.publico import contexto_operativo
from app.primer_parcial.ventas.cu30_pago_en_caja import schemas
from app.primer_parcial.ventas.cu30_pago_en_caja.service import CobroCajaService

router = APIRouter(prefix="/caja/ventas", tags=["CU-30 Pago en caja y comprobante"])
en_caja = contexto_operativo(CAJERO, ENCARGADO)


@router.post("/{pedido_id}/cobrar", response_model=schemas.CobroOut)
def cobrar_en_efectivo(pedido_id: int, datos: schemas.CobroIn, ctx: Contexto = Depends(en_caja), db: Session = Depends(get_db)):
    """Cobra la venta (efectivo con cambio), descuenta el stock y emite el comprobante. Con tarjeta se usa `/api/pagos`."""
    return CobroCajaService(db, ctx).cobrar(pedido_id, datos)


@router.get("/{pedido_id}/comprobante")
def comprobante_de_la_venta(pedido_id: int, ctx: Contexto = Depends(en_caja), db: Session = Depends(get_db)):
    pdf, nombre = CobroCajaService(db, ctx).comprobante(pedido_id)
    return Response(pdf, media_type="application/pdf", headers={"Content-Disposition": f'inline; filename="{nombre}"'})

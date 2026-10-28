from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.core.constantes import CLIENTE
from app.core.database import get_db
from app.modules.acceso.dependencias import Contexto
from app.modules.plataforma.publico import contexto_operativo
from app.primer_parcial.ventas.cu12_historial_compras import schemas
from app.primer_parcial.ventas.cu12_historial_compras.service import HistorialService

router = APIRouter(prefix="/compras", tags=["CU-12 Historial de compras"])
solo_cliente = contexto_operativo(CLIENTE)


@router.get("", response_model=schemas.HistorialOut)
def mis_compras(estado: str | None = None, ctx: Contexto = Depends(solo_cliente), db: Session = Depends(get_db)):
    """Compras del cliente ordenadas por fecha, con monto, sucursal y estado."""
    return HistorialService(db, ctx).listar(estado)


@router.get("/{pedido_id}", response_model=schemas.PedidoOut)
def detalle_de_la_compra(pedido_id: int, ctx: Contexto = Depends(solo_cliente), db: Session = Depends(get_db)):
    return HistorialService(db, ctx).detalle(pedido_id)


@router.get("/{pedido_id}/comprobante")
def descargar_comprobante(pedido_id: int, ctx: Contexto = Depends(solo_cliente), db: Session = Depends(get_db)):
    pdf, nombre = HistorialService(db, ctx).comprobante(pedido_id)
    return Response(pdf, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{nombre}"'})

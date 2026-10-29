from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.constantes import CAJERO, ENCARGADO
from app.core.database import get_db
from app.modules.acceso.dependencias import Contexto
from app.modules.plataforma.publico import contexto_operativo
from app.primer_parcial.ventas.cu28_productos_en_caja import schemas
from app.primer_parcial.ventas.cu28_productos_en_caja.service import ProductosCajaService

router = APIRouter(prefix="/caja/productos", tags=["CU-28 Productos en caja"])
en_caja = contexto_operativo(CAJERO, ENCARGADO)


@router.get("", response_model=list[schemas.ProductoCajaOut])
def buscar_productos_en_caja(q: str = Query(min_length=2, max_length=100), ctx: Contexto = Depends(en_caja), db: Session = Depends(get_db)):
    """Busca prendas por nombre, SKU o código de barras: talla, color, precio con promoción y stock de la sucursal del cajero."""
    return ProductosCajaService(db, ctx).buscar(q)


@router.get("/codigo/{codigo}", response_model=schemas.ProductoCajaOut)
def escanear_codigo(codigo: str, ctx: Contexto = Depends(en_caja), db: Session = Depends(get_db)):
    """El lector de código de barras (o el SKU escrito) identifica una prenda."""
    return ProductosCajaService(db, ctx).por_codigo(codigo)

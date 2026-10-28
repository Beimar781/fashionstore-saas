from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.constantes import ADMIN, CAJERO, CLIENTE, ENCARGADO
from app.core.database import get_db
from app.modules.acceso.dependencias import Contexto
from app.modules.inventario.cu05_disponibilidad import schemas
from app.modules.inventario.cu05_disponibilidad.service import DisponibilidadService
from app.modules.plataforma.publico import contexto_operativo

router = APIRouter(prefix="/inventario", tags=["CU-05 Tallas, colores y disponibilidad por sucursal"])
cualquier_rol = contexto_operativo(ADMIN, ENCARGADO, CAJERO, CLIENTE)


@router.get("/productos/{producto_id}/disponibilidad", response_model=schemas.DisponibilidadOut)
def disponibilidad_por_sucursal(producto_id: int, ctx: Contexto = Depends(cualquier_rol), db: Session = Depends(get_db)):
    """Qué tallas y colores hay de la prenda en cada sucursal de la empresa."""
    return DisponibilidadService(db, ctx.empresa_id).por_sucursal(producto_id)

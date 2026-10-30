from fastapi import APIRouter, Depends, File, Form, Response, UploadFile
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.constantes import ADMIN, CLIENTE
from app.core.database import get_db
from app.core.errors import DatosInvalidos
from app.modules.acceso.dependencias import Contexto
from app.modules.plataforma.publico import contexto_operativo
from app.primer_parcial.ia.cu06_vestidor import schemas
from app.primer_parcial.ia.cu06_vestidor.service import MSG_ANCLAJE, VestidorService

router = APIRouter(prefix="/vestidor", tags=["CU-06 Vestidor virtual"])
solo_admin = contexto_operativo(ADMIN)
admin_o_cliente = contexto_operativo(ADMIN, CLIENTE)


@router.get("/productos/{producto_id}", response_model=schemas.VestidorProductoOut)
def ver_recursos_del_producto(producto_id: int, ctx: Contexto = Depends(admin_o_cliente), db: Session = Depends(get_db)):
    """Lo que el móvil necesita para probarse la prenda (imagen, anclaje y escala por talla) o el aviso de que no admite vestidor."""
    return VestidorService(db, ctx.empresa_id).obtener(producto_id)


@router.put("/productos/{producto_id}/colores/{color_id}", response_model=schemas.ColorVestidorOut)
async def subir_imagen_del_color(
    producto_id: int, color_id: int, archivo: UploadFile = File(...), y_hombros: float = Form(0.10), ancho_hombros: float = Form(0.85),
    y_cadera: float = Form(0.92), ajuste: float = Form(1.0), ctx: Contexto = Depends(solo_admin), db: Session = Depends(get_db),
):
    """El Administrador sube el PNG ya recortado (fondo transparente) de la prenda en ese color; se reemplaza el anterior."""
    try:
        anclaje = schemas.Anclaje(y_hombros=y_hombros, ancho_hombros=ancho_hombros, y_cadera=y_cadera, ajuste=ajuste)
    except ValidationError as e:
        raise DatosInvalidos(MSG_ANCLAJE) from e
    contenido = await archivo.read()
    return VestidorService(db, ctx.empresa_id).subir(producto_id, color_id, contenido, anclaje)


@router.delete("/productos/{producto_id}/colores/{color_id}", status_code=204)
def quitar_imagen_del_color(producto_id: int, color_id: int, ctx: Contexto = Depends(solo_admin), db: Session = Depends(get_db)):
    VestidorService(db, ctx.empresa_id).quitar(producto_id, color_id)
    return Response(status_code=204)

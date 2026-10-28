from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile
from sqlalchemy.orm import Session

from app.core.constantes import ADMIN
from app.core.database import get_db
from app.modules.acceso.dependencias import Contexto
from app.modules.plataforma.publico import contexto_operativo
from app.primer_parcial.catalogo.cu18_productos import schemas
from app.primer_parcial.catalogo.cu18_productos.service import ProductoService

router = APIRouter(prefix="/productos", tags=["CU-18 Productos"])
solo_admin = contexto_operativo(ADMIN)


@router.get("", response_model=schemas.ProductosPagina)
def listar_productos(
    q: str | None = None, categoria_id: int | None = None, activo: bool | None = None,
    pagina: int = Query(1, ge=1), tamano: int = Query(20, ge=1, le=100),
    ctx: Contexto = Depends(solo_admin), db: Session = Depends(get_db),
):
    return ProductoService(db, ctx.empresa_id).listar(q, categoria_id, activo, pagina, tamano)


@router.post("", response_model=schemas.ProductoOut, status_code=201)
def crear_producto(datos: schemas.ProductoIn, ctx: Contexto = Depends(solo_admin), db: Session = Depends(get_db)):
    return ProductoService(db, ctx.empresa_id).crear(datos)


@router.get("/{producto_id}", response_model=schemas.ProductoOut)
def obtener_producto(producto_id: int, ctx: Contexto = Depends(solo_admin), db: Session = Depends(get_db)):
    return ProductoService(db, ctx.empresa_id).obtener(producto_id)


@router.put("/{producto_id}", response_model=schemas.ProductoOut)
def editar_producto(producto_id: int, datos: schemas.ProductoUpdate, ctx: Contexto = Depends(solo_admin), db: Session = Depends(get_db)):
    return ProductoService(db, ctx.empresa_id).editar(producto_id, datos)


@router.post("/{producto_id}/activar", response_model=schemas.ProductoOut)
def activar_producto(producto_id: int, ctx: Contexto = Depends(solo_admin), db: Session = Depends(get_db)):
    return ProductoService(db, ctx.empresa_id).activar(producto_id)


@router.post("/{producto_id}/desactivar", response_model=schemas.ProductoOut)
def desactivar_producto(producto_id: int, ctx: Contexto = Depends(solo_admin), db: Session = Depends(get_db)):
    return ProductoService(db, ctx.empresa_id).desactivar(producto_id)


@router.post("/{producto_id}/variantes", response_model=schemas.VariantesGeneradasOut, status_code=201)
def generar_variantes(producto_id: int, datos: schemas.VariantesIn, ctx: Contexto = Depends(solo_admin), db: Session = Depends(get_db)):
    return ProductoService(db, ctx.empresa_id).generar_variantes(producto_id, datos)


@router.put("/{producto_id}/variantes/{variante_id}", response_model=schemas.VarianteOut)
def editar_variante(producto_id: int, variante_id: int, datos: schemas.VarianteUpdate, ctx: Contexto = Depends(solo_admin), db: Session = Depends(get_db)):
    return ProductoService(db, ctx.empresa_id).editar_variante(producto_id, variante_id, datos)


@router.post("/{producto_id}/imagenes", response_model=schemas.ImagenOut, status_code=201)
async def subir_imagen(
    producto_id: int, archivo: UploadFile = File(...), color_id: int | None = Form(None),
    texto_alt: str = Form(""), principal: bool = Form(False),
    ctx: Contexto = Depends(solo_admin), db: Session = Depends(get_db),
):
    contenido = await archivo.read()
    return ProductoService(db, ctx.empresa_id).subir_imagen(producto_id, contenido, color_id, texto_alt, principal)


@router.post("/{producto_id}/imagenes/{imagen_id}/principal", response_model=schemas.ProductoOut)
def marcar_imagen_principal(producto_id: int, imagen_id: int, ctx: Contexto = Depends(solo_admin), db: Session = Depends(get_db)):
    return ProductoService(db, ctx.empresa_id).marcar_principal(producto_id, imagen_id)


@router.delete("/{producto_id}/imagenes/{imagen_id}", status_code=204)
def eliminar_imagen(producto_id: int, imagen_id: int, ctx: Contexto = Depends(solo_admin), db: Session = Depends(get_db)):
    ProductoService(db, ctx.empresa_id).eliminar_imagen(producto_id, imagen_id)
    return Response(status_code=204)

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.constantes import ADMIN, CAJERO, CLIENTE, ENCARGADO
from app.core.database import get_db
from app.modules.acceso.dependencias import Contexto
from app.modules.catalogo.cu03_consultar_catalogo import schemas
from app.modules.catalogo.cu03_consultar_catalogo.service import CatalogoService
from app.modules.plataforma.publico import contexto_operativo

router = APIRouter(prefix="/catalogo", tags=["CU-03 Consultar catálogo"])
cualquier_rol = contexto_operativo(ADMIN, ENCARGADO, CAJERO, CLIENTE)


@router.get("/sucursales", response_model=list[schemas.SucursalCatalogoOut])
def sucursales_para_consultar(ctx: Contexto = Depends(cualquier_rol), db: Session = Depends(get_db)):
    """Sucursales activas de la empresa, para elegir en cuál consultar la disponibilidad."""
    return CatalogoService(db, ctx.empresa_id).sucursales()


@router.get("/productos", response_model=schemas.PrendasPagina)
def consultar_catalogo(
    categoria_id: int | None = None, sucursal: int | None = None,
    pagina: int = Query(1, ge=1), tamano: int = Query(20, ge=1, le=50),
    ctx: Contexto = Depends(cualquier_rol), db: Session = Depends(get_db),
):
    return CatalogoService(db, ctx.empresa_id).listar(categoria_id, sucursal, pagina, tamano)


@router.get("/productos/{producto_id}", response_model=schemas.PrendaDetalle)
def ver_prenda(producto_id: int, sucursal: int | None = None, ctx: Contexto = Depends(cualquier_rol), db: Session = Depends(get_db)):
    return CatalogoService(db, ctx.empresa_id).detalle(producto_id, sucursal)


@router.get("/productos/{producto_id}/opciones", response_model=schemas.OpcionesOut)
def opciones_de_la_prenda(producto_id: int, sucursal: int | None = None, ctx: Contexto = Depends(cualquier_rol), db: Session = Depends(get_db)):
    """Matriz color × talla con `disponible`, `cantidad` y `orden`. Web y móvil solo la dibujan."""
    return CatalogoService(db, ctx.empresa_id).opciones(producto_id, sucursal)

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.constantes import CLIENTE
from app.core.database import get_db
from app.modules.acceso.dependencias import Contexto
from app.modules.plataforma.publico import contexto_operativo
from app.primer_parcial.reservas.cu08_carrito import schemas
from app.primer_parcial.reservas.cu08_carrito.service import CarritoService

router = APIRouter(prefix="/carrito", tags=["CU-08 Carrito de compras"])
solo_cliente = contexto_operativo(CLIENTE)


@router.get("", response_model=schemas.CarritoOut)
def ver_carrito(ctx: Contexto = Depends(solo_cliente), db: Session = Depends(get_db)):
    """El carrito del cliente con precios vigentes, disponibilidad actual y totales."""
    return CarritoService(db, ctx.empresa_id).obtener(ctx.usuario.id)


@router.post("/items", response_model=schemas.CarritoOut, status_code=201)
def agregar_prenda(datos: schemas.ItemIn, ctx: Contexto = Depends(solo_cliente), db: Session = Depends(get_db)):
    return CarritoService(db, ctx.empresa_id).agregar(ctx.usuario.id, datos)


@router.put("/items/{item_id}", response_model=schemas.CarritoOut)
def cambiar_cantidad(item_id: int, datos: schemas.CantidadIn, ctx: Contexto = Depends(solo_cliente), db: Session = Depends(get_db)):
    return CarritoService(db, ctx.empresa_id).cambiar_cantidad(ctx.usuario.id, item_id, datos.cantidad)


@router.delete("/items/{item_id}", response_model=schemas.CarritoOut)
def quitar_prenda(item_id: int, ctx: Contexto = Depends(solo_cliente), db: Session = Depends(get_db)):
    return CarritoService(db, ctx.empresa_id).quitar(ctx.usuario.id, item_id)


@router.put("/sucursal", response_model=schemas.CarritoOut)
def elegir_sucursal(datos: schemas.SucursalIn, ctx: Contexto = Depends(solo_cliente), db: Session = Depends(get_db)):
    return CarritoService(db, ctx.empresa_id).elegir_sucursal(ctx.usuario.id, datos.sucursal_id)


@router.delete("", response_model=schemas.CarritoOut)
def vaciar_carrito(ctx: Contexto = Depends(solo_cliente), db: Session = Depends(get_db)):
    return CarritoService(db, ctx.empresa_id).vaciar(ctx.usuario.id)

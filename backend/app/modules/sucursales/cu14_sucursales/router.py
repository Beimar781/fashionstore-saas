from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.constantes import ADMIN
from app.core.database import get_db
from app.modules.acceso.dependencias import Contexto
from app.modules.plataforma.publico import contexto_operativo
from app.modules.sucursales.cu14_sucursales import schemas
from app.modules.sucursales.cu14_sucursales.service import SucursalService

router = APIRouter(tags=["CU-14 Ciudades y sucursales"])
solo_admin = contexto_operativo(ADMIN)


@router.get("/sucursales", response_model=schemas.SucursalesOut)
def listar_sucursales(ctx: Contexto = Depends(solo_admin), db: Session = Depends(get_db)):
    return SucursalService(db, ctx.empresa_id).listar()


@router.post("/sucursales", response_model=schemas.SucursalOut, status_code=201)
def crear_sucursal(datos: schemas.SucursalCreate, ctx: Contexto = Depends(solo_admin), db: Session = Depends(get_db)):
    return SucursalService(db, ctx.empresa_id).crear(datos)


@router.put("/sucursales/{sucursal_id}", response_model=schemas.SucursalOut)
def editar_sucursal(sucursal_id: int, datos: schemas.SucursalUpdate, ctx: Contexto = Depends(solo_admin), db: Session = Depends(get_db)):
    return SucursalService(db, ctx.empresa_id).editar(sucursal_id, datos)


@router.post("/sucursales/{sucursal_id}/activar", response_model=schemas.SucursalOut)
def activar_sucursal(sucursal_id: int, ctx: Contexto = Depends(solo_admin), db: Session = Depends(get_db)):
    return SucursalService(db, ctx.empresa_id).activar(sucursal_id)


@router.post("/sucursales/{sucursal_id}/desactivar", response_model=schemas.SucursalOut)
def desactivar_sucursal(sucursal_id: int, ctx: Contexto = Depends(solo_admin), db: Session = Depends(get_db)):
    return SucursalService(db, ctx.empresa_id).desactivar(sucursal_id)


@router.get("/ciudades", response_model=list[schemas.CiudadOut])
def listar_ciudades(ctx: Contexto = Depends(solo_admin), db: Session = Depends(get_db)):
    return SucursalService(db, ctx.empresa_id).listar_ciudades()


@router.post("/ciudades", response_model=schemas.CiudadOut, status_code=201)
def crear_ciudad(datos: schemas.CiudadCreate, ctx: Contexto = Depends(solo_admin), db: Session = Depends(get_db)):
    return SucursalService(db, ctx.empresa_id).crear_ciudad(datos)

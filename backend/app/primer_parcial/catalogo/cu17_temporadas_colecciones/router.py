from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.core.constantes import ADMIN, CAJERO, CLIENTE, ENCARGADO, PROVEEDOR
from app.core.database import get_db
from app.modules.acceso.dependencias import Contexto
from app.modules.plataforma.publico import contexto_operativo
from app.primer_parcial.catalogo.cu17_temporadas_colecciones import schemas
from app.primer_parcial.catalogo.cu17_temporadas_colecciones.service import TemporadaService

router = APIRouter(tags=["CU-17 Temporadas y colecciones"])
solo_admin = contexto_operativo(ADMIN)
cualquier_rol = contexto_operativo(ADMIN, ENCARGADO, CAJERO, CLIENTE, PROVEEDOR)  # todos leen (el proveedor elige colección al proponer); solo el Administrador escribe


@router.get("/temporadas", response_model=list[schemas.TemporadaOut])
def listar_temporadas(ctx: Contexto = Depends(cualquier_rol), db: Session = Depends(get_db)):
    return TemporadaService(db, ctx.empresa_id).listar_temporadas(solo_activas=ctx.rol != ADMIN)


@router.post("/temporadas", response_model=schemas.TemporadaOut, status_code=201)
def crear_temporada(datos: schemas.TemporadaIn, ctx: Contexto = Depends(solo_admin), db: Session = Depends(get_db)):
    return TemporadaService(db, ctx.empresa_id).crear_temporada(datos)


@router.put("/temporadas/{temporada_id}", response_model=schemas.TemporadaOut)
def editar_temporada(temporada_id: int, datos: schemas.TemporadaUpdate, ctx: Contexto = Depends(solo_admin), db: Session = Depends(get_db)):
    return TemporadaService(db, ctx.empresa_id).editar_temporada(temporada_id, datos)


@router.delete("/temporadas/{temporada_id}", status_code=204)
def eliminar_temporada(temporada_id: int, ctx: Contexto = Depends(solo_admin), db: Session = Depends(get_db)):
    TemporadaService(db, ctx.empresa_id).eliminar_temporada(temporada_id)
    return Response(status_code=204)


@router.get("/colecciones", response_model=list[schemas.ColeccionOut])
def listar_colecciones(temporada_id: int | None = None, ctx: Contexto = Depends(cualquier_rol), db: Session = Depends(get_db)):
    return TemporadaService(db, ctx.empresa_id).listar_colecciones(ctx.rol != ADMIN, temporada_id)


@router.post("/colecciones", response_model=schemas.ColeccionOut, status_code=201)
def crear_coleccion(datos: schemas.ColeccionIn, ctx: Contexto = Depends(solo_admin), db: Session = Depends(get_db)):
    return TemporadaService(db, ctx.empresa_id).crear_coleccion(datos)


@router.put("/colecciones/{coleccion_id}", response_model=schemas.ColeccionOut)
def editar_coleccion(coleccion_id: int, datos: schemas.ColeccionUpdate, ctx: Contexto = Depends(solo_admin), db: Session = Depends(get_db)):
    return TemporadaService(db, ctx.empresa_id).editar_coleccion(coleccion_id, datos)


@router.delete("/colecciones/{coleccion_id}", status_code=204)
def eliminar_coleccion(coleccion_id: int, ctx: Contexto = Depends(solo_admin), db: Session = Depends(get_db)):
    TemporadaService(db, ctx.empresa_id).eliminar_coleccion(coleccion_id)
    return Response(status_code=204)

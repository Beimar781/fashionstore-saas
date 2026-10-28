from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.core.constantes import ADMIN, CAJERO, CLIENTE, ENCARGADO
from app.core.database import get_db
from app.modules.acceso.dependencias import Contexto
from app.modules.plataforma.publico import contexto_operativo
from app.primer_parcial.catalogo.cu16_categorias_tallas_colores import schemas
from app.primer_parcial.catalogo.cu16_categorias_tallas_colores.service import AtributoService

router = APIRouter(tags=["CU-16 Categorías, tallas y colores"])
solo_admin = contexto_operativo(ADMIN)
cualquier_rol = contexto_operativo(ADMIN, ENCARGADO, CAJERO, CLIENTE)  # todos leen; solo el Administrador escribe


def _servicio(ctx: Contexto, db: Session) -> AtributoService:
    return AtributoService(db, ctx.empresa_id)


# ---- categorías ----
@router.get("/categorias", response_model=list[schemas.CategoriaOut])
def listar_categorias(ctx: Contexto = Depends(cualquier_rol), db: Session = Depends(get_db)):
    return _servicio(ctx, db).listar_categorias(solo_activas=ctx.rol != ADMIN)


@router.post("/categorias", response_model=schemas.CategoriaOut, status_code=201)
def crear_categoria(datos: schemas.CategoriaIn, ctx: Contexto = Depends(solo_admin), db: Session = Depends(get_db)):
    return _servicio(ctx, db).crear_categoria(datos)


@router.put("/categorias/{categoria_id}", response_model=schemas.CategoriaOut)
def editar_categoria(categoria_id: int, datos: schemas.CategoriaUpdate, ctx: Contexto = Depends(solo_admin), db: Session = Depends(get_db)):
    return _servicio(ctx, db).editar_categoria(categoria_id, datos)


@router.delete("/categorias/{categoria_id}", status_code=204)
def eliminar_categoria(categoria_id: int, ctx: Contexto = Depends(solo_admin), db: Session = Depends(get_db)):
    _servicio(ctx, db).eliminar_categoria(categoria_id)
    return Response(status_code=204)


# ---- grupos de talla y tallas ----
@router.get("/grupos-talla", response_model=list[schemas.GrupoTallaOut])
def listar_grupos(ctx: Contexto = Depends(cualquier_rol), db: Session = Depends(get_db)):
    return _servicio(ctx, db).listar_grupos()


@router.post("/grupos-talla", response_model=schemas.GrupoTallaOut, status_code=201)
def crear_grupo(datos: schemas.GrupoTallaIn, ctx: Contexto = Depends(solo_admin), db: Session = Depends(get_db)):
    return _servicio(ctx, db).crear_grupo(datos)


@router.delete("/grupos-talla/{grupo_id}", status_code=204)
def eliminar_grupo(grupo_id: int, ctx: Contexto = Depends(solo_admin), db: Session = Depends(get_db)):
    _servicio(ctx, db).eliminar_grupo(grupo_id)
    return Response(status_code=204)


@router.post("/tallas", response_model=schemas.TallaOut, status_code=201)
def crear_talla(datos: schemas.TallaIn, ctx: Contexto = Depends(solo_admin), db: Session = Depends(get_db)):
    return _servicio(ctx, db).crear_talla(datos)


@router.put("/tallas/{talla_id}", response_model=schemas.TallaOut)
def editar_talla(talla_id: int, datos: schemas.TallaUpdate, ctx: Contexto = Depends(solo_admin), db: Session = Depends(get_db)):
    return _servicio(ctx, db).editar_talla(talla_id, datos)


@router.delete("/tallas/{talla_id}", status_code=204)
def eliminar_talla(talla_id: int, ctx: Contexto = Depends(solo_admin), db: Session = Depends(get_db)):
    _servicio(ctx, db).eliminar_talla(talla_id)
    return Response(status_code=204)


# ---- colores ----
@router.get("/colores", response_model=list[schemas.ColorOut])
def listar_colores(ctx: Contexto = Depends(cualquier_rol), db: Session = Depends(get_db)):
    return _servicio(ctx, db).listar_colores()


@router.post("/colores", response_model=schemas.ColorOut, status_code=201)
def crear_color(datos: schemas.ColorIn, ctx: Contexto = Depends(solo_admin), db: Session = Depends(get_db)):
    return _servicio(ctx, db).crear_color(datos)


@router.put("/colores/{color_id}", response_model=schemas.ColorOut)
def editar_color(color_id: int, datos: schemas.ColorUpdate, ctx: Contexto = Depends(solo_admin), db: Session = Depends(get_db)):
    return _servicio(ctx, db).editar_color(color_id, datos)


@router.delete("/colores/{color_id}", status_code=204)
def eliminar_color(color_id: int, ctx: Contexto = Depends(solo_admin), db: Session = Depends(get_db)):
    _servicio(ctx, db).eliminar_color(color_id)
    return Response(status_code=204)


# ---- marcas ----
@router.get("/marcas", response_model=list[schemas.MarcaOut])
def listar_marcas(ctx: Contexto = Depends(cualquier_rol), db: Session = Depends(get_db)):
    return _servicio(ctx, db).listar_marcas()


@router.post("/marcas", response_model=schemas.MarcaOut, status_code=201)
def crear_marca(datos: schemas.MarcaIn, ctx: Contexto = Depends(solo_admin), db: Session = Depends(get_db)):
    return _servicio(ctx, db).crear_marca(datos)


@router.delete("/marcas/{marca_id}", status_code=204)
def eliminar_marca(marca_id: int, ctx: Contexto = Depends(solo_admin), db: Session = Depends(get_db)):
    _servicio(ctx, db).eliminar_marca(marca_id)
    return Response(status_code=204)

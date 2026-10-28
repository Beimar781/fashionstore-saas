from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.core.constantes import ADMIN
from app.core.database import get_db
from app.modules.acceso.dependencias import Contexto
from app.modules.plataforma.publico import contexto_operativo
from app.primer_parcial.catalogo.cu19_promociones import schemas
from app.primer_parcial.catalogo.cu19_promociones.service import PromocionService

router = APIRouter(prefix="/promociones", tags=["CU-19 Promociones y descuentos"])
solo_admin = contexto_operativo(ADMIN)


@router.get("", response_model=list[schemas.PromocionOut])
def listar_promociones(solo_vigentes: bool = False, ctx: Contexto = Depends(solo_admin), db: Session = Depends(get_db)):
    return PromocionService(db, ctx.empresa_id).listar(solo_vigentes)


@router.post("", response_model=schemas.PromocionOut, status_code=201)
def crear_promocion(datos: schemas.PromocionIn, ctx: Contexto = Depends(solo_admin), db: Session = Depends(get_db)):
    return PromocionService(db, ctx.empresa_id).crear(datos)


@router.put("/{promocion_id}", response_model=schemas.PromocionOut)
def editar_promocion(promocion_id: int, datos: schemas.PromocionUpdate, ctx: Contexto = Depends(solo_admin), db: Session = Depends(get_db)):
    return PromocionService(db, ctx.empresa_id).editar(promocion_id, datos)


@router.delete("/{promocion_id}", status_code=204)
def eliminar_promocion(promocion_id: int, ctx: Contexto = Depends(solo_admin), db: Session = Depends(get_db)):
    PromocionService(db, ctx.empresa_id).eliminar(promocion_id)
    return Response(status_code=204)

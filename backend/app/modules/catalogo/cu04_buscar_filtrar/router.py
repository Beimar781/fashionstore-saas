from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.constantes import ADMIN, CAJERO, CLIENTE, ENCARGADO
from app.core.database import get_db
from app.modules.acceso.dependencias import Contexto
from app.modules.catalogo.cu03_consultar_catalogo.schemas import PrendasPagina
from app.modules.catalogo.cu04_buscar_filtrar.schemas import FiltrosBusqueda
from app.modules.catalogo.cu04_buscar_filtrar.service import BusquedaService
from app.modules.plataforma.publico import contexto_operativo

router = APIRouter(prefix="/catalogo", tags=["CU-04 Buscar y filtrar prendas"])
cualquier_rol = contexto_operativo(ADMIN, ENCARGADO, CAJERO, CLIENTE)


@router.get("/buscar", response_model=PrendasPagina)
def buscar_prendas(filtros: Annotated[FiltrosBusqueda, Query()], ctx: Contexto = Depends(cualquier_rol), db: Session = Depends(get_db)):
    return BusquedaService(db, ctx.empresa_id).buscar(filtros)

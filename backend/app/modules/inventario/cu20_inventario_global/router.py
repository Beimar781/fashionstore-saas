from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.constantes import ADMIN
from app.core.database import get_db
from app.modules.acceso.dependencias import Contexto
from app.modules.inventario.cu20_inventario_global import schemas
from app.modules.inventario.cu20_inventario_global.service import InventarioGlobalService
from app.modules.plataforma.publico import contexto_operativo

router = APIRouter(prefix="/inventario", tags=["CU-20 Inventario global"])
solo_admin = contexto_operativo(ADMIN)


@router.get("/global", response_model=schemas.InventarioPagina)
def consultar_inventario_global(filtros: Annotated[schemas.FiltrosInventario, Query()], ctx: Contexto = Depends(solo_admin), db: Session = Depends(get_db)):
    """Existencias de todas las sucursales (o de la que se indique): disponibles, reservadas, vendidas, agotadas y próximas a ingresar."""
    return InventarioGlobalService(db, ctx.empresa_id).consultar(filtros)

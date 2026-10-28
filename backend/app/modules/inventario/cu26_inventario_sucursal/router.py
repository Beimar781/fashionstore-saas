from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.constantes import ADMIN, ENCARGADO
from app.core.database import get_db
from app.modules.acceso.dependencias import Contexto
from app.modules.inventario.cu20_inventario_global.schemas import FiltrosInventario, InventarioPagina
from app.modules.inventario.cu20_inventario_global.service import InventarioGlobalService
from app.modules.inventario.cu26_inventario_sucursal import schemas
from app.modules.inventario.cu26_inventario_sucursal.service import InventarioService, sucursal_del_usuario
from app.modules.plataforma.publico import contexto_operativo
from app.primer_parcial.proveedores.publico import LoteOut

router = APIRouter(prefix="/inventario", tags=["CU-26 Inventario de la sucursal"])
solo_encargado = contexto_operativo(ENCARGADO)
admin_o_encargado = contexto_operativo(ADMIN, ENCARGADO)


@router.get("/sucursal", response_model=InventarioPagina)
def inventario_de_mi_sucursal(filtros: Annotated[FiltrosInventario, Query()], ctx: Contexto = Depends(solo_encargado), db: Session = Depends(get_db)):
    """Disponibilidad e inventario de la sucursal del Encargado (RN10: solo la suya)."""
    filtros.sucursal = sucursal_del_usuario(ctx)
    return InventarioGlobalService(db, ctx.empresa_id).consultar(filtros)


@router.post("/sucursal/movimientos", response_model=schemas.ExistenciaOut, status_code=201)
def registrar_ajuste(datos: schemas.AjusteIn, ctx: Contexto = Depends(solo_encargado), db: Session = Depends(get_db)):
    return InventarioService(db, ctx.empresa_id).ajustar(ctx, datos)


@router.put("/sucursal/variantes/{variante_id}/umbral", response_model=schemas.ExistenciaOut)
def fijar_umbral_de_reposicion(variante_id: int, datos: schemas.UmbralIn, ctx: Contexto = Depends(solo_encargado), db: Session = Depends(get_db)):
    return InventarioService(db, ctx.empresa_id).fijar_umbral(ctx, variante_id, datos)


@router.get("/movimientos", response_model=schemas.MovimientosPagina)
def consultar_movimientos(
    sucursal: int | None = None, variante_id: int | None = None, tipo: str | None = None, desde: date | None = None, hasta: date | None = None,
    pagina: int = Query(1, ge=1), tamano: int = Query(25, ge=1, le=100),
    ctx: Contexto = Depends(admin_o_encargado), db: Session = Depends(get_db),
):
    return InventarioService(db, ctx.empresa_id).listar_movimientos(ctx, sucursal, variante_id, tipo, desde, hasta, pagina, tamano)


@router.get("/recepciones", response_model=list[LoteOut])
def lotes_por_recibir(ctx: Contexto = Depends(admin_o_encargado), db: Session = Depends(get_db)):
    """Lotes en tránsito hacia la sucursal (todos, para el Administrador)."""
    return InventarioService(db, ctx.empresa_id).recepciones(ctx)


@router.post("/recepciones/{lote_id}/recibir", response_model=LoteOut)
def recibir_lote(lote_id: int, datos: schemas.RecepcionIn, ctx: Contexto = Depends(admin_o_encargado), db: Session = Depends(get_db)):
    """Suma al inventario lo recibido y cierra el lote."""
    return InventarioService(db, ctx.empresa_id).recibir(ctx, lote_id, datos)

"""Interfaz pública del paquete P3 proveedores (primer parcial) para otros paquetes.

El inventario consulta aquí las unidades «próximas a ingresar» y recibe los lotes en tránsito.
"""
from collections.abc import Callable

from sqlalchemy.orm import Session

from app.modules.acceso.dependencias import Contexto
from app.primer_parcial.proveedores.cu31_abastecimiento.repository import LoteRepository
from app.primer_parcial.proveedores.cu31_abastecimiento.schemas import LoteOut  # noqa: F401
from app.primer_parcial.proveedores.cu31_abastecimiento.service import AbastecimientoService


def en_transito_por_variante(db: Session, empresa_id: int, sucursal_id: int | None = None) -> dict[int, int]:
    """Unidades en lotes EN_TRANSITO por variante (estado «próxima a ingresar»), en una consulta agrupada."""
    return LoteRepository(db, empresa_id).en_transito_por_variante(sucursal_id)


def lotes_para_recibir(db: Session, ctx: Contexto, sucursal_id: int | None) -> list[LoteOut]:
    return AbastecimientoService(db, ctx).lotes_para_recibir(sucursal_id)


def recibir_lote(
    db: Session, ctx: Contexto, lote_id: int, sucursal_id: int | None, recibidas: dict[int, int] | None,
    aplicar: Callable[[int, int, list[tuple[int, int]]], None],
) -> LoteOut:
    return AbastecimientoService(db, ctx).recibir_lote(lote_id, sucursal_id, recibidas, aplicar)

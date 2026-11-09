from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.core.constantes import ADMIN
from app.core.database import get_db
from app.modules.acceso.dependencias import Contexto
from app.modules.plataforma.publico import contexto_operativo, exigir_funcionalidad
from app.modules.reportes.cu21_ventas_y_reservas import schemas
from app.modules.reportes.cu21_ventas_y_reservas.service import VentasYReservasService

router = APIRouter(prefix="/reportes", tags=["CU-21 Reportes de ventas y reservas"], dependencies=[Depends(exigir_funcionalidad("reportes_convencionales"))])
admin = contexto_operativo(ADMIN)


@router.get("/ventas", response_model=schemas.VentasReporteOut)
def reporte_de_ventas(
    desde: date | None = None, hasta: date | None = None, sucursal: int | None = None, canal: Literal["DIGITAL", "PRESENCIAL"] | None = None,
    ctx: Contexto = Depends(admin), db: Session = Depends(get_db),
):
    """Ventas digitales y presenciales netas de devoluciones, por canal, sucursal, día y medio de pago, con los productos más y menos vendidos."""
    return VentasYReservasService(db, ctx).ventas(desde, hasta, sucursal, canal)


@router.get("/reservas", response_model=schemas.ReservasReporteOut)
def reporte_de_reservas(desde: date | None = None, hasta: date | None = None, sucursal: int | None = None, ctx: Contexto = Depends(admin), db: Session = Depends(get_db)):
    return VentasYReservasService(db, ctx).reservas(desde, hasta, sucursal)


@router.get("/pagos", response_model=schemas.PagosReporteOut)
def vista_de_pagos(desde: date | None = None, hasta: date | None = None, sucursal: int | None = None, ctx: Contexto = Depends(admin), db: Session = Depends(get_db)):
    """Pagos aprobados, rechazados y pendientes de confirmación, desde la tabla de pagos."""
    return VentasYReservasService(db, ctx).pagos(desde, hasta, sucursal)


@router.get("/inventario")
def inventario_por_sucursal(
    sucursal: int | None = None, categoria: int | None = None, pagina: int = Query(1, ge=1), tamano: int = Query(50, ge=1, le=200),
    ctx: Contexto = Depends(admin), db: Session = Depends(get_db),
):
    """Existencias por prenda, talla y color (bajo stock y agotados), por sucursal y categoría, paginado."""
    return VentasYReservasService(db, ctx).inventario(sucursal, categoria, pagina, tamano)


@router.get("/exportar/{tipo}")
def exportar_reporte(
    tipo: str, desde: date | None = None, hasta: date | None = None, sucursal: int | None = None, formato: str = "csv", categoria: int | None = None,
    ctx: Contexto = Depends(admin), db: Session = Depends(get_db),
):
    """Descarga el reporte en CSV, Excel (xlsx) o PDF."""
    contenido, tipo_mime, nombre = VentasYReservasService(db, ctx).exportar(tipo, desde, hasta, sucursal, formato, categoria)
    return Response(contenido, media_type=tipo_mime, headers={"Content-Disposition": f'attachment; filename="{nombre}"'})

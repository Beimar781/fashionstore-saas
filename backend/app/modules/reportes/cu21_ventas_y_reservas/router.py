from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Response
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


@router.get("/exportar/{tipo}")
def exportar_reporte(
    tipo: str, desde: date | None = None, hasta: date | None = None, sucursal: int | None = None, ctx: Contexto = Depends(admin), db: Session = Depends(get_db)
):
    texto, nombre = VentasYReservasService(db, ctx).exportar(tipo, desde, hasta, sucursal)
    return Response(texto, media_type="text/csv; charset=utf-8", headers={"Content-Disposition": f'attachment; filename="{nombre}"'})

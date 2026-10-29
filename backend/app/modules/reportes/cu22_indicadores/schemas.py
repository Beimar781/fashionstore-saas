from datetime import date, datetime

from pydantic import BaseModel

from app.core.tipos import Dinero
from app.modules.reportes.cu21_ventas_y_reservas.schemas import CanalOut, DiaOut, EstadoReservaOut, ProductoVendidoOut, SucursalVentasOut


class IndicadorOut(BaseModel):
    """Valor del periodo, valor del periodo anterior de la misma duración y la variación porcentual (None si antes era cero)."""

    valor: float
    anterior: float
    variacion: float | None


class StockOut(BaseModel):
    disponibles: int
    reservadas: int
    vendidas: int
    stock_bajo: int
    agotadas: int


class StockBajoOut(BaseModel):
    sucursal_id: int
    sucursal: str
    producto: str
    sku: str
    disponible: int
    umbral: int


class UltimaVentaOut(BaseModel):
    id: int
    codigo: str
    comprobante: str | None
    sucursal: str
    canal: str
    total: Dinero
    fecha: datetime


class IndicadoresOut(BaseModel):
    dias: int
    desde: date
    hasta: date
    sucursal_id: int | None
    ventas_netas: IndicadorOut
    ventas: IndicadorOut
    ticket_promedio: IndicadorOut
    reservas: IndicadorOut
    conversion_reservas: IndicadorOut  # %
    stock: StockOut
    productos_activos: int
    ventas_por_dia: list[DiaOut]
    por_canal: list[CanalOut]
    por_sucursal: list[SucursalVentasOut]
    reservas_por_estado: list[EstadoReservaOut]
    mas_vendidos: list[ProductoVendidoOut]
    stock_bajo_items: list[StockBajoOut]
    ultimas_ventas: list[UltimaVentaOut]

from datetime import date, datetime

from pydantic import BaseModel

from app.core.tipos import Dinero


class TotalesOut(BaseModel):
    ventas: int
    unidades: int
    total_bruto: Dinero
    devoluciones: int  # notas de devolución y cambio del periodo
    devuelto: Dinero
    entregado_en_cambios: Dinero
    ventas_netas: Dinero  # bruto − devuelto + entregado en cambios
    ticket_promedio: Dinero


class CanalOut(BaseModel):
    canal: str  # DIGITAL | PRESENCIAL
    ventas: int
    unidades: int
    total: Dinero


class SucursalVentasOut(BaseModel):
    sucursal_id: int
    sucursal: str
    ventas: int
    total: Dinero


class DiaOut(BaseModel):
    fecha: date
    ventas: int
    total: Dinero


class ProductoVendidoOut(BaseModel):
    producto: str
    unidades: int  # netas de devoluciones
    ingresos: Dinero


class MetodoOut(BaseModel):
    metodo: str  # EFECTIVO | TARJETA
    cobros: int
    total: Dinero


class VentasReporteOut(BaseModel):
    desde: date
    hasta: date
    sucursal_id: int | None
    canal: str | None
    totales: TotalesOut
    por_canal: list[CanalOut]
    por_sucursal: list[SucursalVentasOut]
    por_dia: list[DiaOut]
    por_metodo: list[MetodoOut]
    mas_vendidos: list[ProductoVendidoOut]
    menos_vendidos: list[ProductoVendidoOut]


class EstadoReservaOut(BaseModel):
    estado: str
    cantidad: int


class SucursalReservasOut(BaseModel):
    sucursal_id: int
    sucursal: str
    reservas: int
    completadas: int


class ReservasReporteOut(BaseModel):
    desde: date
    hasta: date
    sucursal_id: int | None
    total: int
    completadas: int
    conversion: float  # % de reservas completadas (la prenda se llevó) sobre el total
    por_estado: list[EstadoReservaOut]
    por_sucursal: list[SucursalReservasOut]
    por_dia: list[dict]


class ResumenEstadoPagoOut(BaseModel):
    cantidad: int
    monto: Dinero


class PagoPorMetodoOut(BaseModel):
    metodo: str
    estado: str
    cantidad: int
    monto: Dinero


class PagoProblemaOut(BaseModel):
    id: int
    pedido: str
    sucursal_id: int
    sucursal: str
    metodo: str
    estado: str  # RECHAZADO | PENDIENTE_CONFIRMACION
    monto: Dinero
    motivo: str
    tarjeta: str
    fecha: datetime


class PagosReporteOut(BaseModel):
    desde: date
    hasta: date
    sucursal_id: int | None
    aprobados: ResumenEstadoPagoOut
    rechazados: ResumenEstadoPagoOut
    pendientes_confirmacion: ResumenEstadoPagoOut
    por_metodo: list[PagoPorMetodoOut]
    con_problemas: list[PagoProblemaOut]

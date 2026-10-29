from datetime import date, datetime

from pydantic import BaseModel

from app.core.tipos import Dinero


class TotalCanal(BaseModel):
    ventas: int
    unidades: int
    total: Dinero


class CierreMetodo(BaseModel):
    metodo: str  # EFECTIVO | TARJETA | QR
    cobros: int
    total: Dinero
    recibido: Dinero | None  # solo efectivo: lo que entregaron los clientes
    cambio: Dinero | None  # solo efectivo: lo que se devolvió


class ResumenDiaOut(BaseModel):
    fecha: date
    sucursal_id: int
    sucursal: str
    total_vendido: Dinero
    ventas: int
    unidades: int
    ticket_promedio: Dinero
    presencial: TotalCanal  # ventas del día en caja (POS)
    digital: TotalCanal  # pedidos online pagados que se retiran o despachan desde la sucursal
    cierre_de_caja: list[CierreMetodo]
    efectivo_en_caja: Dinero  # lo que debe haber en la caja por cobros en efectivo
    reservas_completadas: int


class TicketOut(BaseModel):
    id: int
    codigo: str
    comprobante_numero: str | None
    comprobante_tipo: str | None
    fecha: datetime
    canal: str
    cliente: str | None
    vendedor: str | None
    metodo: str | None
    unidades: int
    total: Dinero


class VentasOut(BaseModel):
    desde: date
    hasta: date
    total: Dinero
    tickets: list[TicketOut]

from datetime import date, datetime

from pydantic import BaseModel

from app.core.tipos import Dinero


class TotalCanal(BaseModel):
    ventas: int
    unidades: int
    total: Dinero


class CierreMetodo(BaseModel):
    metodo: str  # EFECTIVO | TARJETA
    cobros: int
    total: Dinero
    recibido: Dinero | None  # solo efectivo: lo que entregaron los clientes
    cambio: Dinero | None  # solo efectivo: lo que se devolvió


class DevolucionesDia(BaseModel):
    """Devoluciones y cambios registrados en el día (CU-41): restan en las ventas netas y en el efectivo de caja."""

    notas: int
    devuelto: Dinero  # valor de las prendas que volvieron
    entregado_en_cambios: Dinero  # valor de las prendas nuevas entregadas en cambios
    reembolsado_efectivo: Dinero
    reembolsado_tarjeta: Dinero
    cobrado_efectivo: Dinero  # diferencias que pagaron los clientes en cambios
    cobrado_tarjeta: Dinero


class ResumenDiaOut(BaseModel):
    fecha: date
    sucursal_id: int
    sucursal: str
    total_vendido: Dinero
    ventas_netas: Dinero  # lo vendido menos lo devuelto, más lo entregado en cambios
    ventas: int
    unidades: int
    ticket_promedio: Dinero
    presencial: TotalCanal  # ventas del día en caja (POS)
    digital: TotalCanal  # pedidos online pagados que se retiran o despachan desde la sucursal
    cierre_de_caja: list[CierreMetodo]
    devoluciones: DevolucionesDia
    efectivo_en_caja: Dinero  # cobros en efectivo, más diferencias de cambios, menos reembolsos en efectivo
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

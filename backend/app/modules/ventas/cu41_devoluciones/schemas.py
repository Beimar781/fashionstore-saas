from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from app.core.tipos import Dinero
from app.primer_parcial.ventas.publico import PedidoOut, TarjetaIn


class ItemDevueltoIn(BaseModel):
    pedido_item_id: int
    cantidad: int = Field(ge=1, le=100)


class ItemNuevoIn(BaseModel):
    variante_id: int
    cantidad: int = Field(ge=1, le=50)


class CobroDiferenciaIn(BaseModel):
    """Cómo paga el cliente la diferencia cuando la prenda nueva de un cambio vale más: efectivo o tarjeta (la que prefiera)."""

    metodo: Literal["EFECTIVO", "TARJETA"]
    monto_recibido: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)  # efectivo
    intento_id: int | None = None  # tarjeta: el cobro que se inició con POST /devoluciones/diferencia
    tarjeta: TarjetaIn | None = None  # tarjeta con la pasarela simulada; con Stripe la confirma el navegador


class DiferenciaOut(BaseModel):
    """Cobro con tarjeta de la diferencia, listo para confirmar (mismo formato que el pago del CU-32)."""

    pago_id: int
    modo: str
    publishable_key: str | None
    client_secret: str | None
    monto: Dinero
    moneda: str
    monto_pasarela: float
    moneda_pasarela: str
    tarjeta_guardada: None = None


class CondicionIn(BaseModel):
    """RN15: quien recibe la prenda comprueba que no tenga daños ni desgaste y que conserve sus etiquetas."""

    sin_danos: bool = False
    sin_desgaste: bool = False
    con_etiquetas: bool = False


class DevolucionIn(BaseModel):
    comprobante: str = Field(default="", max_length=30)  # RN15: se requiere el comprobante de la venta; las faltas se avisan con el mensaje de la regla
    tipo: Literal["DEVOLUCION", "CAMBIO"] = "DEVOLUCION"
    motivo: str = Field(default="", max_length=200)
    items: list[ItemDevueltoIn] = Field(default=[], max_length=60)
    nuevos: list[ItemNuevoIn] = Field(default=[], max_length=60)  # solo en un cambio
    cobro: CobroDiferenciaIn | None = None
    condicion: CondicionIn = CondicionIn()


class ItemDevolucionOut(BaseModel):
    sentido: str  # DEVUELTA | ENTREGADA
    sku: str
    producto: str
    talla: str
    color: str
    cantidad: int
    precio_final: Dinero
    subtotal: Dinero


class DevolucionOut(BaseModel):
    id: int
    numero: str
    tipo: str
    motivo: str
    comprobante: str | None
    pedido_codigo: str
    sucursal_id: int
    sucursal: str
    fecha: datetime
    monto_devuelto: Dinero
    monto_nuevo: Dinero
    reembolso: Dinero
    cobro_adicional: Dinero
    medio_reembolso: str | None
    referencia_reembolso: str | None
    medio_cobro: str | None
    monto_recibido: Dinero | None
    cambio_entregado: Dinero | None
    tarjeta_cobro: str | None  # «Visa ****4242» cuando la diferencia se pagó con tarjeta
    registrada_por: str | None
    sin_danos: bool = True
    sin_desgaste: bool = True
    con_etiquetas: bool = True
    items: list[ItemDevolucionOut]


class ItemDevolvibleOut(BaseModel):
    pedido_item_id: int
    variante_id: int
    sku: str
    producto: str
    talla: str
    color: str
    precio_final: Dinero
    vendida: int
    devuelta: int
    devolvible: int  # lo que todavía se puede devolver


class VentaDevolvibleOut(BaseModel):
    pedido: PedidoOut
    items: list[ItemDevolvibleOut]
    medio_pago: str | None  # con qué se pagó: de ahí sale cómo se devuelve el dinero
    plazo_dias: int
    vence_el: datetime
    dentro_del_plazo: bool
    devoluciones: list[DevolucionOut]


class ConfiguracionOut(BaseModel):
    plazo_dias: int


class ConfiguracionIn(BaseModel):
    plazo_dias: int = Field(ge=0, le=365)


class ResumenFecha(BaseModel):
    desde: date
    hasta: date

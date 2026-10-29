from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.core.tipos import Dinero

MSG_NIT = "Ingrese su NIT o CI para la facturación."
MSG_DIRECCION = "Ingrese la dirección de entrega."


class CheckoutIn(BaseModel):
    tipo_entrega: Literal["DELIVERY", "RETIRO"]
    direccion_entrega: str = Field(default="", max_length=300)  # solo en delivery; en retiro se recoge en la sucursal del carrito
    nit_ci: str = Field(default="", max_length=20)
    razon_social: str = Field(default="", max_length=120)

    @model_validator(mode="after")
    def _datos(self):
        if len(self.nit_ci.strip()) < 3:
            raise ValueError(MSG_NIT)
        if self.tipo_entrega == "DELIVERY" and not self.direccion_entrega.strip():
            raise ValueError(MSG_DIRECCION)
        return self


class ItemPedidoOut(BaseModel):
    id: int
    variante_id: int
    sku: str
    producto: str
    talla: str
    color: str
    cantidad: int
    precio_unitario: Dinero
    precio_final: Dinero
    subtotal: Dinero


class PagoResumenOut(BaseModel):
    id: int
    estado: str
    metodo: str
    proveedor: str
    monto: Dinero
    monto_recibido: Dinero | None = None
    cambio: Dinero | None = None
    tarjeta_marca: str
    tarjeta_ultimos4: str
    mensaje: str
    motivo: str
    creado_en: datetime


class PedidoOut(BaseModel):
    id: int
    codigo: str
    estado: str
    canal: str
    tipo_entrega: str
    direccion_entrega: str
    nit_ci: str
    razon_social: str
    sucursal_id: int
    sucursal: str
    subtotal: Dinero
    descuento: Dinero
    iva_incluido: Dinero
    total: Dinero
    moneda: str
    total_unidades: int
    comprobante_numero: str | None
    comprobante_tipo: str | None = None  # FACTURA o INTERNO_TEMPORAL
    comprobante_aviso: str | None = None  # aviso de la ficha CU-30 cuando el servicio de impuestos no respondió
    cliente: str | None = None
    vendedor: str | None = None
    reserva_id: int | None = None
    creado_en: datetime
    pagado_en: datetime | None
    items: list[ItemPedidoOut]
    pagos: list[PagoResumenOut]

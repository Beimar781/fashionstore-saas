from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from app.core.tipos import Dinero


class ItemIn(BaseModel):
    variante_id: int
    cantidad: int = Field(default=1, ge=1, le=10)
    sucursal_id: int | None = None  # la primera vez define de qué sucursal se compra; después se usa la del carrito


class CantidadIn(BaseModel):
    cantidad: int = Field(ge=1, le=10)


class SucursalIn(BaseModel):
    sucursal_id: int


EstadoItem = Literal["OK", "SIN_STOCK", "RETIRADA"]


class ItemCarritoOut(BaseModel):
    id: int
    variante_id: int
    producto_id: int
    sku: str
    producto: str
    talla: str
    color: str
    imagen: str | None
    cantidad: int
    precio: Dinero
    precio_final: Dinero
    subtotal: Dinero
    disponible: int  # unidades que hay ahora en la sucursal del carrito
    estado: EstadoItem


class CarritoOut(BaseModel):
    sucursal_id: int | None
    sucursal: str | None
    items: list[ItemCarritoOut]
    total_unidades: int
    subtotal: Dinero
    descuento: Dinero
    iva_incluido: Dinero
    total: Dinero
    puede_pagar: bool
    avisos: list[str]


CERO = Decimal("0.00")

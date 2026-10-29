from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from app.modules.catalogo.publico import PrendaOut


class MensajeIn(BaseModel):
    rol: Literal["usuario", "asistente"]
    texto: str = Field(default="", max_length=500)


class ChatIn(BaseModel):
    mensajes: list[MensajeIn] = Field(min_length=1, max_length=20)  # la conversación; el último debe ser del cliente
    sucursal_id: int | None = None  # con sucursal, solo prendas con stock allí


class ChatOut(BaseModel):
    respuesta: str
    productos: list[PrendaOut]
    sugerencias: list[str]
    filtros: dict  # lo que se entendió del pedido, para mostrarlo al cliente
    origen: Literal["IA", "REGLAS"]


class RecomendacionesOut(BaseModel):
    motivo: str
    personalizada: bool  # False cuando el sistema aún no conoce los gustos del cliente y se muestra lo más vendido
    productos: list[PrendaOut]
    motivos: dict[int, str]  # por qué se le recomienda cada prenda (id de la prenda → motivo)
    ofertas: list[PrendaOut]  # prendas en promoción que encajan con sus gustos
    origen: Literal["IA", "REGLAS"]


class OutfitOut(BaseModel):
    base: PrendaOut | None
    prendas: list[PrendaOut]  # las que completan el outfit
    motivo: str
    motivos: dict[int, str]
    origen: Literal["IA", "REGLAS"]


class InteraccionIn(BaseModel):
    """Algo que el cliente hizo en la tienda y que revela sus gustos: una búsqueda o una prenda que miró."""

    tipo: Literal["BUSQUEDA", "VISTA"]
    texto: str | None = Field(default=None, max_length=120)
    producto_id: int | None = None
    categoria_id: int | None = None
    color_id: int | None = None
    talla: str | None = Field(default=None, max_length=8)
    precio_max: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)


class InteraccionOut(BaseModel):
    registrada: bool  # False si el cliente apagó la personalización


class PrivacidadIn(BaseModel):
    personalizar: bool


class PrivacidadOut(BaseModel):
    personalizar: bool
    interacciones: int  # cuántas búsquedas y prendas vistas se recuerdan

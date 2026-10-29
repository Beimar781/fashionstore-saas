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
    personalizada: bool  # False cuando el cliente aún no tiene compras y se muestra lo más vendido
    productos: list[PrendaOut]

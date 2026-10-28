from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class AjusteIn(BaseModel):
    variante_id: int
    tipo: Literal["AJUSTE_ENTRADA", "AJUSTE_SALIDA"]
    cantidad: int = Field(ge=1, le=100000)
    nota: str = Field(min_length=3, max_length=200)  # un ajuste siempre lleva su motivo


class UmbralIn(BaseModel):
    umbral_minimo: int = Field(ge=0, le=100000)


class ExistenciaOut(BaseModel):
    variante_id: int
    disponible: int
    reservada: int
    vendida: int
    umbral_minimo: int


class MovimientoOut(BaseModel):
    id: int
    creado_en: datetime
    sucursal_id: int
    sucursal: str
    variante_id: int
    sku: str
    producto: str
    talla: str
    color: str
    tipo: str
    cantidad: int
    referencia_tipo: str
    referencia_id: int | None
    usuario: str | None
    nota: str


class MovimientosPagina(BaseModel):
    total: int
    pagina: int
    tamano: int
    items: list[MovimientoOut]


class ItemRecibido(BaseModel):
    item_id: int
    cantidad_recibida: int = Field(ge=0, le=100000)


class RecepcionIn(BaseModel):
    items: list[ItemRecibido] = []  # sin lista: se recibe todo lo despachado

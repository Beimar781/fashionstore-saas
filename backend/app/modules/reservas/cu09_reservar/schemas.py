from datetime import datetime

from pydantic import BaseModel, Field


class ItemIn(BaseModel):
    variante_id: int
    cantidad: int = Field(ge=1, le=10)


class ReservaIn(BaseModel):
    sucursal_id: int
    programada_para: datetime  # horario aproximado de visita; sin zona se toma como hora de la tienda
    notas: str = Field(default="", max_length=300)
    items: list[ItemIn] = Field(default=[], max_length=20)  # al menos una prenda: se valida en el servicio


class ItemOut(BaseModel):
    id: int
    variante_id: int
    sku: str
    producto: str
    talla: str
    color: str
    cantidad: int
    estado: str


class ReservaOut(BaseModel):
    id: int
    codigo: str
    estado: str
    sucursal_id: int
    sucursal: str
    cliente_id: int
    cliente: str
    programada_para: datetime
    vence_en: datetime
    notas: str
    creada_en: datetime
    total_unidades: int
    puede_cancelar: bool
    items: list[ItemOut]

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

MSG_FECHAS = "La fecha de fin debe ser posterior a la de inicio."  # excepción de la ficha CU-17

TipoTemporada = Literal["PRIMAVERA_VERANO", "OTONO_INVIERNO", "ESCOLAR", "PROMOCIONAL", "NUEVA_COLECCION"]


class TemporadaIn(BaseModel):
    nombre: str = Field(min_length=2, max_length=100)
    codigo: str = Field(min_length=2, max_length=20)
    tipo: TipoTemporada
    inicio: date
    fin: date
    activa: bool = True

    @model_validator(mode="after")
    def _fechas(self):
        if self.fin <= self.inicio:
            raise ValueError(MSG_FECHAS)
        return self


class TemporadaUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=2, max_length=100)
    codigo: str | None = Field(default=None, min_length=2, max_length=20)
    tipo: TipoTemporada | None = None
    inicio: date | None = None
    fin: date | None = None
    activa: bool | None = None


class TemporadaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    codigo: str
    tipo: str
    inicio: date
    fin: date
    activa: bool


class ColeccionIn(BaseModel):
    nombre: str = Field(min_length=2, max_length=120)
    temporada_id: int
    fecha_lanzamiento: date | None = None
    activa: bool = True


class ColeccionUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=2, max_length=120)
    temporada_id: int | None = None
    fecha_lanzamiento: date | None = None
    activa: bool | None = None


class ColeccionOut(BaseModel):
    id: int
    nombre: str
    slug: str
    temporada_id: int
    temporada: str
    fecha_lanzamiento: date | None
    activa: bool

    @classmethod
    def desde(cls, c) -> "ColeccionOut":
        return cls(
            id=c.id, nombre=c.nombre, slug=c.slug, temporada_id=c.temporada_id, temporada=c.temporada.nombre,
            fecha_lanzamiento=c.fecha_lanzamiento, activa=c.activa,
        )

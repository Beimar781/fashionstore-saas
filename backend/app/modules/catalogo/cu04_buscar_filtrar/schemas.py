from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, model_validator

MSG_PRECIOS = "El precio mínimo no puede ser mayor que el máximo."


class FiltrosBusqueda(BaseModel):
    """Filtros de la búsqueda (query string). Talla y color se aplican a la MISMA variante."""

    q: str | None = Field(default=None, max_length=100)
    categoria_id: int | None = None  # incluye sus subcategorías
    marca_id: int | None = None
    genero: Literal["MASCULINO", "FEMENINO", "UNISEX", "NINOS"] | None = None
    temporada_id: int | None = None
    coleccion_id: int | None = None
    talla: str | None = Field(default=None, max_length=8)  # por código (M, 32...), no por id: cambia entre grupos
    color_id: int | None = None
    precio_min: Decimal | None = Field(default=None, ge=0)
    precio_max: Decimal | None = Field(default=None, ge=0)
    sucursal: int | None = None  # con sucursal solo salen las variantes con stock allí
    solo_disponibles: bool = False
    orden: Literal["recientes", "precio_asc", "precio_desc", "nombre"] = "recientes"
    pagina: int = Field(default=1, ge=1)
    tamano: int = Field(default=20, ge=1, le=50)

    @model_validator(mode="after")
    def _precios(self):
        if self.precio_min is not None and self.precio_max is not None and self.precio_min > self.precio_max:
            raise ValueError(MSG_PRECIOS)
        return self

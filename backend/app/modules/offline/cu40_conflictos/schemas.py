from typing import Literal

from pydantic import BaseModel, Field


class ResolverIn(BaseModel):
    accion: Literal["REINTENTAR", "DESCARTAR"]
    motivo: str | None = Field(default=None, max_length=200)  # obligatorio al descartar

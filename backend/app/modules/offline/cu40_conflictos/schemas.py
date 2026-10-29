from typing import Literal

from pydantic import BaseModel, Field

from app.modules.ventas.publico import CondicionIn


class ResolverIn(BaseModel):
    accion: Literal["REINTENTAR", "DESCARTAR"]
    motivo: str | None = Field(default=None, max_length=200)  # obligatorio al descartar
    devolver_dinero: bool = False  # solo en una venta de contado ya cobrada: registra la devolución del efectivo con CU-41
    condicion: CondicionIn = CondicionIn()  # la prenda que vuelve se revisa igual que en CU-41

from pydantic import BaseModel, Field

from app.modules.reservas.publico import ReservaOut


class CodigoIn(BaseModel):
    codigo: str = Field(min_length=1, max_length=20)


class CompletarIn(BaseModel):
    llevara_prendas: bool = False  # sí: el cobro sigue en CU-29 (venta presencial)


class AtencionOut(BaseModel):
    reserva: ReservaOut
    habilita_venta: bool  # verdadero cuando el cliente decide llevar las prendas

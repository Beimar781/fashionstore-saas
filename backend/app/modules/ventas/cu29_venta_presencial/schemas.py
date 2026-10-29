from pydantic import BaseModel, Field


class LineaIn(BaseModel):
    variante_id: int
    cantidad: int = Field(ge=1, le=50)


class VentaIn(BaseModel):
    items: list[LineaIn] = Field(default=[], max_length=60)  # sin reserva: al menos una prenda; con reserva: las que el cliente se lleva (vacío = todas)
    reserva_codigo: str | None = Field(default=None, max_length=20)
    cliente_email: str | None = Field(default=None, max_length=120)  # vincula la venta a un cliente registrado (aparece en su historial)
    nit_ci: str = Field(default="0", max_length=20)
    razon_social: str = Field(default="Sin nombre", max_length=120)

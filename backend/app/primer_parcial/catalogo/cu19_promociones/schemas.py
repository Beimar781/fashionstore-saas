from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.core.tipos import Dinero

MSG_FECHAS = "La fecha de finalización debe ser posterior a la fecha de inicio."  # excepción de la ficha CU-19
MSG_PORCENTAJE = "El porcentaje de descuento debe estar entre 0 y 100."

TipoDescuento = Literal["PORCENTAJE", "MONTO"]


class PromocionIn(BaseModel):
    nombre: str = Field(min_length=2, max_length=200)
    codigo: str | None = Field(default=None, min_length=3, max_length=50)  # sin código: promoción automática
    tipo_descuento: TipoDescuento
    valor: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    inicia: date
    termina: date
    monto_minimo: Decimal = Field(default=Decimal(0), ge=0, max_digits=10, decimal_places=2)
    usos_maximos: int | None = Field(default=None, ge=1)
    activa: bool = True
    categorias_ids: list[int] = []  # los tres vacíos: la promoción aplica a todo el catálogo
    colecciones_ids: list[int] = []
    productos_ids: list[int] = []

    @model_validator(mode="after")
    def _reglas(self):
        if self.termina <= self.inicia:
            raise ValueError(MSG_FECHAS)
        if self.tipo_descuento == "PORCENTAJE" and self.valor > 100:
            raise ValueError(MSG_PORCENTAJE)
        return self


class PromocionUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=2, max_length=200)
    codigo: str | None = Field(default=None, min_length=3, max_length=50)
    tipo_descuento: TipoDescuento | None = None
    valor: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    inicia: date | None = None
    termina: date | None = None
    monto_minimo: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    usos_maximos: int | None = Field(default=None, ge=1)
    activa: bool | None = None
    categorias_ids: list[int] | None = None
    colecciones_ids: list[int] | None = None
    productos_ids: list[int] | None = None


class PromocionOut(BaseModel):
    id: int
    nombre: str
    codigo: str | None
    tipo_descuento: str
    valor: Dinero
    inicia: date
    termina: date
    monto_minimo: Dinero
    usos_maximos: int | None
    usos: int
    activa: bool
    vigente: bool
    categorias_ids: list[int]
    colecciones_ids: list[int]
    productos_ids: list[int]

    @classmethod
    def desde(cls, p, hoy: date) -> "PromocionOut":
        return cls(
            id=p.id, nombre=p.nombre, codigo=p.codigo, tipo_descuento=p.tipo_descuento, valor=p.valor, inicia=p.inicia,
            termina=p.termina, monto_minimo=p.monto_minimo, usos_maximos=p.usos_maximos, usos=p.usos, activa=p.activa,
            vigente=p.activa and p.inicia <= hoy <= p.termina,
            categorias_ids=[c.id for c in p.categorias], colecciones_ids=[c.id for c in p.colecciones],
            productos_ids=[x.id for x in p.productos],
        )

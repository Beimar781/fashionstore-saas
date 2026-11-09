from datetime import date
from decimal import Decimal

from pydantic import BaseModel, computed_field

from app.core.dinero import precio_plan_texto


class PlanDetalleOut(BaseModel):
    id: int
    nombre: str
    descripcion: str | None
    precio: Decimal
    periodicidad: str

    @computed_field
    @property
    def moneda(self) -> str:
        return "BOB"

    @computed_field
    @property
    def precio_texto(self) -> str:
        return precio_plan_texto(self.precio, self.periodicidad)


class VigenciaOut(BaseModel):
    estado: str
    fecha_inicio: date
    fecha_vencimiento: date
    dias_restantes: int | None  # None si ya no está activa
    vigente: bool


class LimiteOut(BaseModel):
    clave: str
    etiqueta: str
    usado: int
    limite: int | None
    porcentaje: float | None
    alcanzado: bool


class ConsumoOut(BaseModel):
    clave: str
    etiqueta: str
    valor: int


class FuncionalidadOut(BaseModel):
    clave: str
    etiqueta: str
    incluida: bool


class MiPlanOut(BaseModel):
    plan: PlanDetalleOut | None
    vigencia: VigenciaOut | None
    limites: list[LimiteOut]
    consumo: list[ConsumoOut]
    funcionalidades: list[FuncionalidadOut]
    alertas: list[str]

from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class PlanDetalleOut(BaseModel):
    id: int
    nombre: str
    descripcion: str | None
    precio: Decimal
    periodicidad: str


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

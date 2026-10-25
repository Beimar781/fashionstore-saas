from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _limite_positivo(v: int | None) -> int | None:
    if v is not None and v <= 0:
        raise ValueError("El límite de sucursales debe ser mayor a cero.")
    return v


class PlanCreate(BaseModel):
    nombre: str = Field(min_length=2, max_length=50)
    descripcion: str | None = None
    precio: Decimal = Field(ge=0)
    periodicidad: str = Field(default="mensual", pattern="^(mensual|anual)$")
    max_sucursales: int
    reportes_ia: bool = False
    offline: bool = True
    reportes_convencionales: bool = True

    _v = field_validator("max_sucursales")(_limite_positivo)


class PlanUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=2, max_length=50)
    descripcion: str | None = None
    precio: Decimal | None = Field(default=None, ge=0)
    periodicidad: str | None = Field(default=None, pattern="^(mensual|anual)$")
    max_sucursales: int | None = None
    reportes_ia: bool | None = None
    offline: bool | None = None
    reportes_convencionales: bool | None = None

    _v = field_validator("max_sucursales")(_limite_positivo)


class PlanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    descripcion: str | None
    precio: Decimal
    periodicidad: str
    max_sucursales: int
    reportes_ia: bool
    offline: bool
    reportes_convencionales: bool
    activo: bool
    empresas_suscritas: int = 0


class EmpresaExcedida(BaseModel):
    empresa_id: int
    codigo: str
    sucursales_activas: int
    limite: int


class PlanGuardadoOut(BaseModel):
    plan: PlanOut
    advertencias: list[EmpresaExcedida] = []

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

from app.core.constantes import FORMAS_PAGO, SUS_CANCELADA, SUS_SUSPENDIDA
from app.core.dinero import formato_bs


class SuscripcionIn(BaseModel):
    """Asignar plan, cambiar de plan o renovar (el servicio distingue el caso)."""

    plan_id: int
    fecha_inicio: date
    fecha_vencimiento: date | None = None
    duracion_meses: int | None = Field(default=None, ge=1, le=60)
    forma_pago: str | None = None

    @field_validator("forma_pago")
    @classmethod
    def _forma_pago(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip().upper()
        if v not in FORMAS_PAGO:
            raise ValueError("La forma de pago debe ser efectivo, transferencia o QR.")
        return v


class SuscripcionEstadoIn(BaseModel):
    estado: str = SUS_SUSPENDIDA

    @field_validator("estado")
    @classmethod
    def _estado(cls, v: str) -> str:
        v = v.upper()
        if v not in (SUS_SUSPENDIDA, SUS_CANCELADA):
            raise ValueError("El estado debe ser SUSPENDIDA o CANCELADA.")
        return v


class PlanResumen(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    max_sucursales: int
    reportes_ia: bool
    offline: bool
    reportes_convencionales: bool


class SuscripcionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    empresa_id: int
    plan: PlanResumen
    fecha_inicio: date
    fecha_vencimiento: date
    estado: str
    forma_pago: str | None
    monto: Decimal | None

    @computed_field
    @property
    def moneda(self) -> str:
        return "BOB"

    @computed_field
    @property
    def monto_texto(self) -> str | None:
        return formato_bs(self.monto) if self.monto is not None else None


class UsoPlan(BaseModel):
    sucursales_activas: int
    limite: int | None


class SuscripcionDetalleOut(BaseModel):
    vigente: SuscripcionOut | None
    historial: list[SuscripcionOut]
    uso: UsoPlan

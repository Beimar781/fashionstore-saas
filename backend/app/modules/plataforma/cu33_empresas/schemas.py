from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.modules.acceso.cu13_usuarios.schemas import validar_password


class AdministradorIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=80)
    apellidos: str = Field(default="", max_length=80)
    email: EmailStr
    password: str

    _v = field_validator("password")(validar_password)


class SuscripcionInicialIn(BaseModel):
    plan_id: int
    fecha_inicio: date
    fecha_vencimiento: date | None = None
    duracion_meses: int | None = Field(default=None, ge=1, le=60)
    forma_pago: str | None = None


class EmpresaCreate(BaseModel):
    codigo: str = Field(min_length=2, max_length=30, pattern=r"^[A-Za-z0-9_-]+$")
    razon_social: str = Field(min_length=2, max_length=120)
    nit: str = Field(min_length=3, max_length=20)
    email_contacto: EmailStr | None = None
    telefono: str | None = Field(default=None, max_length=20)
    administrador: AdministradorIn | None = None
    suscripcion: SuscripcionInicialIn | None = None


class EmpresaUpdate(BaseModel):
    razon_social: str | None = Field(default=None, min_length=2, max_length=120)
    nit: str | None = Field(default=None, min_length=3, max_length=20)
    email_contacto: EmailStr | None = None
    telefono: str | None = Field(default=None, max_length=20)


class EmpresaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    codigo: str
    razon_social: str
    nit: str
    email_contacto: str | None
    telefono: str | None
    estado: str
    creado_en: datetime
    plan: str | None = None
    suscripcion_estado: str | None = None
    fecha_vencimiento: date | None = None


class EmpresaRegistradaOut(EmpresaOut):
    """Datos de acceso mostrados al confirmar el registro (CU-33, paso 9)."""

    administrador_email: str | None = None

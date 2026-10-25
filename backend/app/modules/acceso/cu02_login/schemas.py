from datetime import date

from pydantic import BaseModel, Field, field_validator

from app.modules.acceso.cu13_usuarios.schemas import validar_password


class LoginIn(BaseModel):
    codigo_empresa: str | None = Field(default=None, max_length=30)  # el SuperAdministrador lo omite
    email: str = Field(min_length=3, max_length=120)
    password: str = Field(min_length=1)


class RefreshIn(BaseModel):
    refresh_token: str


class UsuarioSesion(BaseModel):
    id: int
    nombre: str
    apellidos: str
    email: str
    rol: str
    sucursal_id: int | None
    sucursal_nombre: str | None = None


class EmpresaSesion(BaseModel):
    id: int
    codigo: str
    razon_social: str
    estado: str


class PlanSesion(BaseModel):
    nombre: str
    max_sucursales: int
    reportes_ia: bool
    offline: bool
    reportes_convencionales: bool


class SuscripcionSesion(BaseModel):
    estado: str
    fecha_inicio: date
    fecha_vencimiento: date
    plan: PlanSesion


class SesionOut(BaseModel):
    """Contexto de la sesión: se guarda localmente (web/móvil) para operar sin conexión (CU-02, paso 8)."""

    usuario: UsuarioSesion
    empresa: EmpresaSesion | None
    suscripcion: SuscripcionSesion | None
    panel: str
    restringido: bool  # Administrador con suscripción no vigente: solo consulta de plan


class TokenOut(SesionOut):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class OlvidePasswordIn(BaseModel):
    codigo_empresa: str | None = Field(default=None, max_length=30)  # el SuperAdministrador lo omite
    email: str = Field(min_length=3, max_length=120)


class RestablecerPasswordIn(BaseModel):
    token: str = Field(min_length=10, max_length=200)
    password: str

    _v = field_validator("password")(validar_password)


class MensajeOut(BaseModel):
    detail: str

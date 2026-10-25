from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


def validar_password(v: str) -> str:
    if v is None or len(v) < 8:
        raise ValueError("La contraseña debe tener al menos 8 caracteres.")
    return v


class UsuarioCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=80)
    apellidos: str = Field(default="", max_length=80)
    email: EmailStr
    password: str
    rol: str
    sucursal_id: int | None = None

    _v = field_validator("password")(validar_password)


class UsuarioUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=80)
    apellidos: str | None = Field(default=None, max_length=80)
    rol: str | None = None
    sucursal_id: int | None = None
    activo: bool | None = None
    password: str | None = None

    @field_validator("password")
    @classmethod
    def _pw(cls, v: str | None) -> str | None:
        return None if v is None else validar_password(v)


class UsuarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    apellidos: str
    email: str
    rol: str
    sucursal_id: int | None
    sucursal_nombre: str | None = None
    activo: bool
    ultimo_acceso: datetime | None = None

    @classmethod
    def desde(cls, u) -> "UsuarioOut":
        return cls(
            id=u.id,
            nombre=u.nombre,
            apellidos=u.apellidos,
            email=u.email,
            rol=u.rol.nombre,
            sucursal_id=u.sucursal_id,
            sucursal_nombre=u.sucursal.nombre if u.sucursal else None,
            activo=u.activo,
            ultimo_acceso=u.ultimo_acceso,
        )

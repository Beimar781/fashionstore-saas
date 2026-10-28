from pydantic import BaseModel, EmailStr, Field, field_validator

from app.modules.acceso.cu13_usuarios.schemas import validar_password


class RegistroClienteIn(BaseModel):
    codigo_empresa: str = Field(min_length=1, max_length=30)  # el cliente se registra en la tienda (empresa) que visita
    nombre: str = Field(min_length=1, max_length=80)
    apellidos: str = Field(default="", max_length=80)
    email: EmailStr
    password: str

    _v = field_validator("password")(validar_password)

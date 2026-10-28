from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from app.modules.acceso.publico import validar_password

MSG_DATOS = "Debe proporcionar el nombre de la empresa y la información de contacto."  # excepción de la ficha CU-15


def _vacio_a_none(v):
    return None if isinstance(v, str) and not v.strip() else v


class ProveedorIn(BaseModel):
    razon_social: str | None = Field(default=None, max_length=200)
    nombre_comercial: str = Field(default="", max_length=200)
    nit: str | None = Field(default=None, max_length=50)
    email: EmailStr | None = None
    telefono: str | None = Field(default=None, max_length=20)
    direccion: str = Field(default="", max_length=300)

    _limpiar = field_validator("razon_social", "nit", "email", "telefono", mode="before")(_vacio_a_none)

    @model_validator(mode="after")
    def _obligatorios(self):
        if not self.razon_social or not (self.email or self.telefono):  # nombre de la empresa y algún dato de contacto
            raise ValueError(MSG_DATOS)
        return self


class ProveedorUpdate(BaseModel):
    razon_social: str | None = Field(default=None, max_length=200)
    nombre_comercial: str | None = Field(default=None, max_length=200)
    nit: str | None = Field(default=None, max_length=50)
    email: EmailStr | None = None
    telefono: str | None = Field(default=None, max_length=20)
    direccion: str | None = Field(default=None, max_length=300)

    _limpiar = field_validator("razon_social", "nit", "email", "telefono", mode="before")(_vacio_a_none)


class ProveedorOut(BaseModel):
    id: int
    razon_social: str
    nombre_comercial: str
    nit: str | None
    email: str | None
    telefono: str | None
    direccion: str
    activo: bool
    tiene_acceso: bool  # cuenta del portal de proveedores

    @classmethod
    def desde(cls, p) -> "ProveedorOut":
        return cls(
            id=p.id, razon_social=p.razon_social, nombre_comercial=p.nombre_comercial, nit=p.nit, email=p.email,
            telefono=p.telefono, direccion=p.direccion, activo=p.activo, tiene_acceso=p.usuario_id is not None,
        )


class AccesoIn(BaseModel):
    nombre: str | None = Field(default=None, max_length=80)  # sin valor: se usa el nombre del proveedor
    email: EmailStr
    password: str

    _v = field_validator("password")(validar_password)


class VincularColeccionIn(BaseModel):
    proveedor_id: int | None = None  # sin valor: la colección queda sin proveedor

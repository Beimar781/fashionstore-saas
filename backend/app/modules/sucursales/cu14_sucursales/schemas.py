from pydantic import BaseModel, ConfigDict, Field, model_validator


class CiudadCreate(BaseModel):
    nombre: str = Field(min_length=2, max_length=80)
    departamento: str | None = Field(default=None, max_length=80)


class CiudadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    departamento: str | None


class SucursalCreate(BaseModel):
    ciudad_id: int | None = None
    ciudad_nombre: str | None = Field(default=None, max_length=80)
    nombre: str = Field(min_length=2, max_length=100)
    direccion: str | None = Field(default=None, max_length=200)
    telefono: str | None = Field(default=None, max_length=20)
    horario: str | None = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def _ciudad(self):
        if self.ciudad_id is None and not (self.ciudad_nombre and self.ciudad_nombre.strip()):
            raise ValueError("Seleccione o ingrese la ciudad de la sucursal.")
        return self


class SucursalUpdate(BaseModel):
    ciudad_id: int | None = None
    nombre: str | None = Field(default=None, min_length=2, max_length=100)
    direccion: str | None = Field(default=None, max_length=200)
    telefono: str | None = Field(default=None, max_length=20)
    horario: str | None = Field(default=None, max_length=100)


class SucursalOut(BaseModel):
    id: int
    nombre: str
    ciudad_id: int
    ciudad: str
    direccion: str | None
    telefono: str | None
    horario: str | None
    activa: bool

    @classmethod
    def desde(cls, s) -> "SucursalOut":
        return cls(
            id=s.id, nombre=s.nombre, ciudad_id=s.ciudad_id, ciudad=s.ciudad.nombre,
            direccion=s.direccion, telefono=s.telefono, horario=s.horario, activa=s.activa,
        )


class UsoPlanOut(BaseModel):
    plan: str | None
    activas: int
    limite: int | None
    disponibles: int | None


class SucursalesOut(BaseModel):
    uso_plan: UsoPlanOut
    sucursales: list[SucursalOut]

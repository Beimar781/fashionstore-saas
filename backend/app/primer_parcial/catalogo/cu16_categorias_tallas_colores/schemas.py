from pydantic import BaseModel, ConfigDict, Field


class CategoriaIn(BaseModel):
    nombre: str = Field(min_length=2, max_length=100)
    padre_id: int | None = None
    grupo_talla_id: int | None = None
    orden: int = Field(default=0, ge=0)
    activa: bool = True


class CategoriaUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=2, max_length=100)
    padre_id: int | None = None
    grupo_talla_id: int | None = None
    orden: int | None = Field(default=None, ge=0)
    activa: bool | None = None


class CategoriaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    slug: str
    padre_id: int | None
    grupo_talla_id: int | None
    orden: int
    activa: bool


class GrupoTallaIn(BaseModel):
    nombre: str = Field(min_length=2, max_length=50)
    descripcion: str | None = Field(default=None, max_length=200)


class TallaIn(BaseModel):
    grupo_id: int
    codigo: str = Field(min_length=1, max_length=8, pattern=r"^[A-Za-z0-9.\-]+$")
    orden: int | None = Field(default=None, ge=0)  # sin valor: va al final del grupo


class TallaUpdate(BaseModel):
    codigo: str | None = Field(default=None, min_length=1, max_length=8, pattern=r"^[A-Za-z0-9.\-]+$")
    orden: int | None = Field(default=None, ge=0)


class TallaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    grupo_id: int
    codigo: str
    orden: int


class GrupoTallaOut(BaseModel):
    id: int
    nombre: str
    descripcion: str | None
    tallas: list[TallaOut]


class ColorIn(BaseModel):
    nombre: str = Field(min_length=2, max_length=50)
    codigo_hex: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")


class ColorUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=2, max_length=50)
    codigo_hex: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")


class ColorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    slug: str
    codigo: str
    codigo_hex: str


class MarcaIn(BaseModel):
    nombre: str = Field(min_length=2, max_length=100)


class MarcaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    slug: str

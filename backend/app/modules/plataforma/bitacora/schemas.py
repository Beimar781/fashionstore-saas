from datetime import date, datetime

from pydantic import BaseModel


class RegistroOut(BaseModel):
    id: int
    fecha: datetime
    empresa_id: int | None
    empresa: str | None  # solo en la bitácora general del SuperAdministrador; «Plataforma» si la operación no es de una empresa
    usuario: str
    rol: str | None
    accion: str
    accion_texto: str
    tono: str  # color de la etiqueta: verde, gris, azul, ambar, rojo o morado
    entidad: str
    entidad_id: int | None
    detalle: str
    ip: str | None


class PaginaBitacoraOut(BaseModel):
    total: int
    pagina: int
    tamano: int
    items: list[RegistroOut]


class AccionOut(BaseModel):
    codigo: str
    texto: str


class EmpresaOpcionOut(BaseModel):
    id: int
    nombre: str


class OpcionesOut(BaseModel):
    usuarios: list[str]
    entidades: list[str]
    acciones: list[AccionOut]
    empresas: list[EmpresaOpcionOut]  # solo el SuperAdministrador ve más de una


class Filtros(BaseModel):
    usuario: str | None = None
    entidad: str | None = None
    accion: str | None = None
    desde: date | None = None
    hasta: date | None = None
    q: str | None = None
    empresa: str | None = None  # SuperAdministrador: id de la empresa o «plataforma»
    pagina: int = 1
    tamano: int = 25

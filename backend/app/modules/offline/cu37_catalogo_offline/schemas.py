from datetime import datetime

from pydantic import BaseModel

from app.core.tipos import Dinero


class SucursalLocalOut(BaseModel):
    id: int
    nombre: str
    ciudad: str
    direccion: str | None
    horario: str | None


class VarianteLocalOut(BaseModel):
    id: int
    sku: str
    codigo_barras: str | None
    talla: str
    color: str
    precio: Dinero
    precio_final: Dinero  # con la promoción vigente al descargar
    promocion: str | None
    stock: dict[int, int]  # sucursal → disponibles; el personal recibe solo la de su sucursal


class ProductoLocalOut(BaseModel):
    id: int
    nombre: str
    categoria: str
    genero: str
    imagen: str | None
    variantes: list[VarianteLocalOut]


class ClienteLocalOut(BaseModel):
    id: int
    nombre: str
    email: str


class CatalogoLocalOut(BaseModel):
    generado_en: datetime  # RN16: el cliente muestra esta fecha para avisar que la información puede estar desactualizada
    empresa_id: int
    sucursales: list[SucursalLocalOut]
    productos: list[ProductoLocalOut]
    clientes: list[ClienteLocalOut]  # solo para el personal (datos mínimos)

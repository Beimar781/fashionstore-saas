from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from app.core.tipos import Dinero


class ItemIn(BaseModel):
    sku: str = Field(min_length=1, max_length=40)
    cantidad: int = Field(ge=1, le=100000)
    costo_unitario: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)


class VarianteHabilitada(BaseModel):
    sku: str
    producto: str
    talla: str
    color: str


class SucursalDestino(BaseModel):
    id: int
    nombre: str
    ciudad: str


class LoteIn(BaseModel):
    sucursal_id: int
    proveedor_id: int | None = None  # solo lo indica el Administrador; el Proveedor envía como sí mismo
    referencia: str = Field(default="", max_length=100)
    notas: str = Field(default="", max_length=300)
    items: list[ItemIn] = []  # se valida en el servicio: al menos un producto


class ItemOut(BaseModel):
    id: int
    variante_id: int
    sku: str
    producto: str
    talla: str
    color: str
    cantidad: int
    cantidad_recibida: int | None
    costo_unitario: Dinero | None


class LoteOut(BaseModel):
    id: int
    codigo: str
    estado: Literal["EN_TRANSITO", "RECIBIDO", "CANCELADO"]
    proveedor_id: int
    proveedor: str
    sucursal_id: int
    sucursal: str
    referencia: str
    notas: str
    creado_en: datetime
    cerrado_en: datetime | None
    total_unidades: int
    items: list[ItemOut]


class PropuestaIn(BaseModel):
    nombre: str = Field(min_length=2, max_length=200)
    descripcion: str = Field(default="", max_length=2000)
    coleccion_id: int
    genero: Literal["MASCULINO", "FEMENINO", "UNISEX", "NINOS"]
    precio_base: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    material: str = Field(default="", max_length=200)


class PropuestaOut(BaseModel):
    id: int
    proveedor_id: int
    proveedor: str
    nombre: str
    descripcion: str
    coleccion_id: int
    coleccion: str
    genero: str
    precio_base: Dinero
    material: str
    estado: Literal["PENDIENTE", "APROBADA", "RECHAZADA"]
    notas_revision: str
    creado_en: datetime


class RevisionIn(BaseModel):
    notas: str = Field(default="", max_length=500)


class ResumenOut(BaseModel):
    lotes_en_transito: int
    propuestas_pendientes: int

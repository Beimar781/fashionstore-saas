from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from app.core.almacenamiento import url_media
from app.core.tipos import Dinero

Genero = Literal["MASCULINO", "FEMENINO", "UNISEX", "NINOS"]


class ProductoIn(BaseModel):
    nombre: str = Field(min_length=2, max_length=200)
    descripcion: str = Field(default="", max_length=2000)
    categoria_id: int
    marca_id: int | None = None
    coleccion_id: int
    genero: Genero
    precio_base: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    material: str = Field(default="", max_length=200)
    cuidado: str = Field(default="", max_length=500)
    tallas_ids: list[int] = []  # se validan en el servicio: la ficha exige al menos una talla y un color
    colores_ids: list[int] = []


class ProductoUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=2, max_length=200)
    descripcion: str | None = Field(default=None, max_length=2000)
    categoria_id: int | None = None
    marca_id: int | None = None
    coleccion_id: int | None = None
    genero: Genero | None = None
    precio_base: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    material: str | None = Field(default=None, max_length=200)
    cuidado: str | None = Field(default=None, max_length=500)


class VariantesIn(BaseModel):
    tallas_ids: list[int] = []
    colores_ids: list[int] = []


class VarianteUpdate(BaseModel):
    precio_especifico: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    codigo_barras: str | None = Field(default=None, max_length=32)
    activa: bool | None = None


class VarianteOut(BaseModel):
    id: int
    sku: str
    talla_id: int
    talla: str
    color_id: int
    color: str
    codigo_barras: str | None
    precio_especifico: Dinero | None
    precio: Dinero
    activa: bool

    @classmethod
    def desde(cls, v) -> "VarianteOut":
        return cls(
            id=v.id, sku=v.sku, talla_id=v.talla_id, talla=v.talla.codigo, color_id=v.color_id, color=v.color.nombre,
            codigo_barras=v.codigo_barras, precio_especifico=v.precio_especifico, precio=v.precio, activa=v.activa,
        )


class ImagenOut(BaseModel):
    id: int
    color_id: int | None
    url: str
    texto_alt: str
    principal: bool
    orden: int

    @classmethod
    def desde(cls, i) -> "ImagenOut":
        return cls(id=i.id, color_id=i.color_id, url=url_media(i.ruta), texto_alt=i.texto_alt, principal=i.principal, orden=i.orden)


class ProductoOut(BaseModel):
    id: int
    publico_id: str
    nombre: str
    slug: str
    descripcion: str
    categoria_id: int
    categoria: str
    marca_id: int | None
    marca: str | None
    coleccion_id: int
    coleccion: str
    temporada: str
    genero: str
    precio_base: Dinero
    material: str
    cuidado: str
    activo: bool
    variantes: list[VarianteOut]
    imagenes: list[ImagenOut]

    @classmethod
    def desde(cls, p) -> "ProductoOut":
        variantes = sorted(p.variantes, key=lambda v: (v.talla.orden, v.color.nombre))  # tallas por orden, no por creación
        imagenes = sorted(p.imagenes, key=lambda i: (not i.principal, i.orden, i.id))
        return cls(
            id=p.id, publico_id=str(p.publico_id), nombre=p.nombre, slug=p.slug, descripcion=p.descripcion,
            categoria_id=p.categoria_id, categoria=p.categoria.nombre, marca_id=p.marca_id, marca=p.marca.nombre if p.marca else None,
            coleccion_id=p.coleccion_id, coleccion=p.coleccion.nombre, temporada=p.coleccion.temporada.nombre,
            genero=p.genero, precio_base=p.precio_base, material=p.material, cuidado=p.cuidado, activo=p.activo,
            variantes=[VarianteOut.desde(v) for v in variantes], imagenes=[ImagenOut.desde(i) for i in imagenes],
        )


class ProductoResumen(BaseModel):
    id: int
    nombre: str
    categoria: str
    marca: str | None
    coleccion: str
    precio_base: Dinero
    activo: bool
    variantes: int
    imagen_principal: str | None


class ProductosPagina(BaseModel):
    total: int
    pagina: int
    tamano: int
    items: list[ProductoResumen]


class VariantesGeneradasOut(BaseModel):
    creadas: int
    omitidas: int  # combinaciones que ya existían
    variantes: list[VarianteOut]

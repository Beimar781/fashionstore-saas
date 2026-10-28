from pydantic import BaseModel

from app.core.tipos import Dinero


class SucursalCatalogoOut(BaseModel):
    id: int
    nombre: str
    ciudad: str
    direccion: str | None
    horario: str | None


class ColorOut(BaseModel):
    id: int
    nombre: str
    codigo_hex: str


class ImagenOut(BaseModel):
    id: int
    color_id: int | None
    url: str
    texto_alt: str
    principal: bool


class PrendaOut(BaseModel):
    """Tarjeta del catálogo: el precio es el de la variante más barata («desde»), con su promoción si la tiene."""

    id: int
    publico_id: str
    nombre: str
    slug: str
    categoria: str
    marca: str | None
    genero: str
    coleccion: str
    temporada: str
    precio: Dinero
    precio_final: Dinero
    promocion: str | None
    imagen: str | None
    colores: list[ColorOut]
    tallas: list[str]
    disponible: bool


class PrendasPagina(BaseModel):
    total: int
    pagina: int
    tamano: int
    items: list[PrendaOut]


class PrendaDetalle(PrendaOut):
    descripcion: str
    material: str
    cuidado: str
    imagenes: list[ImagenOut]


# ---- Opciones color × talla (un solo endpoint para web y móvil: ellos solo dibujan, no recalculan) ----
class OpcionTalla(BaseModel):
    id: int
    codigo: str
    orden: int
    disponible: bool


class OpcionColor(ColorOut):
    disponible: bool


class OpcionVariante(BaseModel):
    variante_id: int
    sku: str
    talla_id: int
    talla: str
    color_id: int
    color: str
    precio: Dinero
    precio_final: Dinero
    disponible: bool
    cantidad: int
    orden: int  # orden de la talla dentro de su grupo


class OpcionesOut(BaseModel):
    producto_id: int
    sucursal_id: int | None
    tallas: list[OpcionTalla]
    colores: list[OpcionColor]
    variantes: list[OpcionVariante]

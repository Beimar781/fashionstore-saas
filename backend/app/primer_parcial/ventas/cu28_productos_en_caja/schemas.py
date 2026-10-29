from pydantic import BaseModel

from app.core.tipos import Dinero


class ProductoCajaOut(BaseModel):
    variante_id: int
    producto_id: int
    sku: str
    codigo_barras: str | None
    producto: str
    talla: str
    color: str
    precio: Dinero
    precio_final: Dinero  # con la promoción vigente aplicada
    promocion: str | None
    disponible: int  # unidades en la sucursal del cajero
    imagen: str | None

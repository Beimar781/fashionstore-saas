"""CU-06 · Vestidor virtual con realidad aumentada: el recurso (PNG con fondo transparente y anclaje) de cada prenda superior por color. Capa de negocio.

El Administrador sube el PNG ya recortado; el backend lo valida (PNG con transparencia), lo reduce a 800 px de ancho y guarda sus puntos de anclaje.
El Cliente consulta, desde el móvil, lo que necesita para probarse la prenda; la cámara y la detección de pose ocurren solo en el teléfono.
"""
import unicodedata

from sqlalchemy.orm import Session

from app.core import almacenamiento
from app.core.config import get_settings
from app.core.errors import DatosInvalidos, NoEncontrado
from app.primer_parcial.ia.cu06_vestidor import schemas
from app.primer_parcial.ia.cu06_vestidor.imagen import preparar_png
from app.primer_parcial.ia.cu06_vestidor.repository import ArAssetRepository
from app.primer_parcial.ia.models import ArAsset

MSG_NO_ADMITE = "Esta prenda no admite vestidor."
MSG_SOLO_SUPERIORES = "Esta prenda no admite vestidor: solo se aceptan camisas, polos y chaquetas."
MSG_COLOR = "El producto no tiene prendas de ese color."
MSG_ANCLAJE = "Los puntos de anclaje de la prenda no son válidos."
MSG_TAMANO = "La imagen no puede pesar más de {mb} MB."
PRENDAS_SUPERIORES = ("camisa", "camiseta", "polo", "polera", "blusa", "chaqueta", "casaca", "saco", "chompa", "sudadera")  # esta versión solo viste el torso
ESCALA_TALLAS = {"XXS": 0.88, "XS": 0.92, "S": 0.96, "M": 1.0, "L": 1.05, "XL": 1.10, "XXL": 1.15, "XXXL": 1.20}  # por código de talla; las numéricas y las demás usan 1.0


def _sin_tildes(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto.lower()) if unicodedata.category(c) != "Mn")


def escala_de(talla: str) -> float:
    return ESCALA_TALLAS.get(talla.strip().upper(), 1.0)


class VestidorService:
    def __init__(self, db: Session, empresa_id: int):
        self.db = db
        self.empresa_id = empresa_id
        self.assets = ArAssetRepository(db, empresa_id)

    # ---- Administrador: sube o quita el PNG de un color ----
    def subir(self, producto_id: int, color_id: int, contenido: bytes, anclaje: schemas.Anclaje) -> schemas.ColorVestidorOut:
        producto = self._producto(producto_id)
        if not self._es_superior(producto):
            raise DatosInvalidos(MSG_SOLO_SUPERIORES)
        color = next((c for c in self.assets.colores(producto.id) if c.id == color_id), None)
        if color is None:
            raise DatosInvalidos(MSG_COLOR)
        maximo_mb = get_settings().media_max_mb
        if len(contenido) > maximo_mb * 1024 * 1024:
            raise DatosInvalidos(MSG_TAMANO.format(mb=maximo_mb))
        png, ancho, alto = preparar_png(contenido)
        ruta = almacenamiento.guardar_imagen(self.empresa_id, producto.id, png, "png")
        previo = self.assets.por_color(producto.id, color.id)
        ruta_anterior = previo.ruta if previo else None
        if previo is None:
            previo = self.assets.agregar(ArAsset(producto_id=producto.id, color_id=color.id, ruta=ruta, ancho=ancho, alto=alto, anclaje=anclaje.model_dump()))
        else:
            previo.ruta, previo.ancho, previo.alto, previo.anclaje = ruta, ancho, alto, anclaje.model_dump()
        self.db.commit()
        if ruta_anterior:
            almacenamiento.borrar_imagen(ruta_anterior)
        return self._color(color, previo)

    def quitar(self, producto_id: int, color_id: int) -> None:
        self._producto(producto_id)
        asset = self.assets.por_color(producto_id, color_id)
        if asset is None:
            raise NoEncontrado("La prenda no tiene imagen de vestidor en ese color.")
        ruta = asset.ruta
        self.db.delete(asset)
        self.db.commit()
        almacenamiento.borrar_imagen(ruta)

    # ---- Administrador y Cliente: lo que hay para probarse ----
    def obtener(self, producto_id: int) -> schemas.VestidorProductoOut:
        producto = self._producto(producto_id)
        if not self._es_superior(producto):
            return schemas.VestidorProductoOut(producto_id=producto.id, producto=producto.nombre, admite=False, mensaje=MSG_NO_ADMITE, colores=[], escala_tallas={})
        assets = self.assets.de_producto(producto.id)
        return schemas.VestidorProductoOut(
            producto_id=producto.id, producto=producto.nombre, admite=True, mensaje=None,
            colores=[self._color(c, assets.get(c.id)) for c in self.assets.colores(producto.id)],
            escala_tallas={talla: escala_de(talla) for talla in self.assets.tallas(producto.id)},
        )

    # ---- auxiliares ----
    def _producto(self, producto_id: int):
        producto = self.assets.producto(producto_id)
        if producto is None:
            raise NoEncontrado("Producto no encontrado.")  # también si es de otra empresa
        return producto

    def _es_superior(self, producto) -> bool:
        nombres = [_sin_tildes(n) for n in self.assets.nombres_de_categoria(producto.categoria_id)]
        return any(clave in nombre for nombre in nombres for clave in PRENDAS_SUPERIORES)

    @staticmethod
    def _color(color, asset: ArAsset | None) -> schemas.ColorVestidorOut:
        return schemas.ColorVestidorOut(
            color_id=color.id, color=color.nombre, codigo_hex=color.codigo_hex, listo=asset is not None,
            imagen_url=almacenamiento.url_media(asset.ruta) if asset else None, ancho=asset.ancho if asset else None, alto=asset.alto if asset else None,
            anclaje=schemas.Anclaje(**asset.anclaje) if asset else None,
        )

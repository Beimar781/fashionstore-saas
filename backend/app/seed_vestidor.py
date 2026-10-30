"""Seed del vestidor virtual (CU-06): las prendas superiores de cada empresa con su PNG de demostración, dibujado por código (nada copiado de ningún sitio)."""
import io

from PIL import Image, ImageDraw
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import almacenamiento
from app.modules.plataforma.models import Empresa
from app.primer_parcial.catalogo.publico import Producto
from app.primer_parcial.ia.cu06_vestidor.imagen import preparar_png
from app.primer_parcial.ia.cu06_vestidor.repository import ArAssetRepository
from app.primer_parcial.ia.cu06_vestidor.schemas import Anclaje
from app.primer_parcial.ia.cu06_vestidor.service import VestidorService
from app.primer_parcial.ia.models import ArAsset

ANCHO, ALTO = 400, 480


def png_de_camisa(hex_color: str) -> bytes:
    """Una camisa tipo polo sencilla (cuerpo, mangas y cuello) del color pedido, sobre fondo transparente. Los hombros quedan al 10 % de la altura."""
    color = tuple(int(hex_color.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)) + (255,)
    sombra = tuple(max(0, c - 40) for c in color[:3]) + (255,)
    imagen = Image.new("RGBA", (ANCHO, ALTO), (0, 0, 0, 0))
    dibujo = ImageDraw.Draw(imagen)
    dibujo.polygon([(75, 48), (140, 48), (200, 82), (260, 48), (325, 48), (392, 130), (340, 178), (310, 150), (310, 460), (90, 460), (90, 150), (60, 178), (8, 130)], fill=color, outline=sombra)
    dibujo.polygon([(140, 48), (200, 82), (260, 48), (236, 40), (200, 56), (164, 40)], fill=sombra)  # cuello
    dibujo.line([(200, 82), (200, 150)], fill=sombra, width=3)  # botonadura
    salida = io.BytesIO()
    imagen.save(salida, format="PNG")
    return salida.getvalue()


def cargar_vestidor(db: Session, empresa: Empresa) -> None:
    """Deja lista para el vestidor cada prenda superior de la empresa (camisas, polos, chompas), en todos sus colores."""
    servicio = VestidorService(db, empresa.id)
    repo = ArAssetRepository(db, empresa.id)
    for producto in db.scalars(select(Producto).where(Producto.empresa_id == empresa.id, Producto.activo.is_(True)).order_by(Producto.id)):
        if not servicio._es_superior(producto):
            continue
        for color in repo.colores(producto.id):
            if repo.por_color(producto.id, color.id) is not None:
                continue
            png, ancho, alto = preparar_png(png_de_camisa(color.codigo_hex))
            ruta = almacenamiento.guardar_imagen(empresa.id, producto.id, png, "png")
            repo.agregar(ArAsset(producto_id=producto.id, color_id=color.id, ruta=ruta, ancho=ancho, alto=alto, anclaje=Anclaje(y_hombros=0.10, ancho_hombros=0.82, y_cadera=0.90).model_dump()))

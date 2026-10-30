"""Seed de las prendas de demostración reales (Prompt L): 7 PNG con fondo transparente en `app/seed_data/prendas/`, que sirven de foto del producto y de PNG del vestidor virtual (CU-06).
Se agregan a las dos empresas con precios distintos. Es idempotente y, si el volumen de imágenes está vacío (despliegue nuevo), `reponer_imagenes` las vuelve a escribir."""
import io
from decimal import Decimal
from pathlib import Path

from PIL import Image
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import almacenamiento
from app.core.texto import codigo_corto, slugify
from app.modules.inventario.models import Existencia
from app.modules.sucursales.models import Sucursal
from app.primer_parcial.catalogo.models import Categoria, Coleccion, Color, GrupoTalla, ImagenProducto, Marca, Producto, Talla, Variante
from app.primer_parcial.ia.cu06_vestidor.imagen import preparar_png
from app.primer_parcial.ia.cu06_vestidor.schemas import Anclaje
from app.primer_parcial.ia.models import ArAsset

CARPETA = Path(__file__).parent / "seed_data" / "prendas"
TALLAS = ["S", "M", "L", "XL"]

# archivo, nombre, categoría, color (nombre, hex), género, material, precio en EMP-A y en EMP-B (Bs)
PRENDAS = [
    ("camiseta-raglan-gris.png", "Camiseta Raglán Gris", "Camisetas", ("Gris", "#A3A5A8"), "UNISEX", "Algodón y poliéster (manga 3/4)", {"EMP-A": "95", "EMP-B": "130"}),
    ("chaqueta-cuero-negra.png", "Chaqueta de Cuero Negra", "Chaquetas", ("Negro", "#111111"), "UNISEX", "Cuero sintético", {"EMP-A": "420", "EMP-B": "480"}),
    ("polo-blanco.png", "Polo Blanco", "Polos", ("Blanco", "#F5F5F5"), "MASCULINO", "Piqué de algodón", {"EMP-A": "85", "EMP-B": "110"}),
    ("camiseta-mostaza.png", "Camiseta Mostaza", "Camisetas", ("Mostaza", "#D4A017"), "UNISEX", "Algodón rayado", {"EMP-A": "70", "EMP-B": "95"}),
    ("camiseta-beige.png", "Camiseta Beige", "Camisetas", ("Beige", "#D2B48C"), "UNISEX", "Algodón", {"EMP-A": "65", "EMP-B": "90"}),
    ("camiseta-azul-marino.png", "Camiseta Azul Marino", "Camisetas", ("Azul marino", "#1A2A5E"), "MASCULINO", "Algodón peinado", {"EMP-A": "75", "EMP-B": "100"}),
    ("camiseta-verde-oliva.png", "Camiseta Verde Oliva Estampada", "Camisetas", ("Verde oliva", "#6B7A4B"), "UNISEX", "Algodón con estampado", {"EMP-A": "80", "EMP-B": "105"}),
]
ARCHIVO_DE = {nombre: archivo for archivo, nombre, *_ in PRENDAS}


def anclaje_desde_png(contenido: bytes) -> Anclaje:
    """Calcula el anclaje del vestidor a partir del recuadro visible de la prenda: la línea de hombros queda cerca del borde superior de la prenda
    (8 % de su altura), el ancho de hombros es lo que ocupa la prenda a 12 % de su altura (donde nacen las mangas) y la cadera cerca del borde inferior."""
    with Image.open(io.BytesIO(contenido)) as imagen:
        alfa = imagen.convert("RGBA").getchannel("A").point(lambda v: 255 if v > 16 else 0)
    ancho, alto = alfa.size
    izq, sup, der, inf = alfa.getbbox()
    y_hombros = sup + 0.08 * (inf - sup)
    y_fila = int(sup + 0.12 * (inf - sup))
    fila = alfa.crop((0, y_fila, ancho, y_fila + 1)).getbbox()
    ancho_fila = (fila[2] - fila[0]) if fila else (der - izq)
    return Anclaje(
        y_hombros=round(min(0.5, y_hombros / alto), 3),
        ancho_hombros=round(max(0.3, min(1.0, ancho_fila / ancho)), 3),
        y_cadera=round(max(0.4, min(1.0, (sup + 0.95 * (inf - sup)) / alto)), 3),
    )


def _color(db: Session, empresa_id: int, nombre: str, hexa: str) -> Color:
    existente = db.scalar(select(Color).where(Color.empresa_id == empresa_id, Color.nombre == nombre))
    if existente:
        return existente
    usados = set(db.scalars(select(Color.codigo).where(Color.empresa_id == empresa_id)))
    color = Color(empresa_id=empresa_id, nombre=nombre, slug=slugify(nombre), codigo=codigo_corto(nombre, lambda c: c in usados), codigo_hex=hexa)
    db.add(color)
    db.flush()
    return color


def _categoria(db: Session, empresa_id: int, nombre: str, grupo: GrupoTalla) -> Categoria:
    existente = db.scalar(select(Categoria).where(Categoria.empresa_id == empresa_id, Categoria.slug == slugify(nombre)))
    if existente:
        return existente
    orden = len(list(db.scalars(select(Categoria.id).where(Categoria.empresa_id == empresa_id)))) + 1
    categoria = Categoria(empresa_id=empresa_id, nombre=nombre, slug=slugify(nombre), grupo_talla_id=grupo.id, orden=orden)
    db.add(categoria)
    db.flush()
    return categoria


def cargar_prendas(db: Session, empresa) -> None:
    """Agrega las 7 prendas a la empresa (si es una de las de demostración): color real, tallas S a XL del grupo «Ropa superior», existencias, foto y PNG del vestidor."""
    eid = empresa.id
    grupo = db.scalar(select(GrupoTalla).where(GrupoTalla.empresa_id == eid, GrupoTalla.nombre == "Ropa superior"))
    coleccion = db.scalar(select(Coleccion).where(Coleccion.empresa_id == eid).order_by(Coleccion.id))
    if grupo is None or coleccion is None or empresa.codigo not in PRENDAS[0][6]:
        return
    marca = db.scalar(select(Marca).where(Marca.empresa_id == eid).order_by(Marca.id))
    tallas = {t.codigo: t for t in db.scalars(select(Talla).where(Talla.grupo_id == grupo.id))}
    sucursales = list(db.scalars(select(Sucursal).where(Sucursal.empresa_id == eid).order_by(Sucursal.id)))
    for archivo, nombre, nombre_categoria, (nombre_color, hexa), genero, material, precios in PRENDAS:
        if db.scalar(select(Producto.id).where(Producto.empresa_id == eid, Producto.slug == slugify(nombre))):
            continue
        categoria, color = _categoria(db, eid, nombre_categoria, grupo), _color(db, eid, nombre_color, hexa)
        producto = Producto(
            empresa_id=eid, categoria_id=categoria.id, marca_id=marca.id if marca else None, coleccion_id=coleccion.id, nombre=nombre, slug=slugify(nombre),
            descripcion=f"{nombre} de la colección {coleccion.nombre}.", genero=genero, precio_base=Decimal(precios[empresa.codigo]), material=material,
            cuidado="Lavar a máquina en agua fría",
        )
        db.add(producto)
        db.flush()
        for codigo in TALLAS:
            variante = Variante(empresa_id=eid, producto_id=producto.id, talla_id=tallas[codigo].id, color_id=color.id, sku=f"P{producto.id}-{codigo}-{color.codigo}".upper())
            db.add(variante)
            db.flush()
            for s in sucursales:
                db.add(Existencia(empresa_id=eid, sucursal_id=s.id, variante_id=variante.id, disponible=5 + (variante.id * 3 + s.id) % 8))
        foto = (CARPETA / archivo).read_bytes()
        db.add(ImagenProducto(empresa_id=eid, producto_id=producto.id, color_id=color.id, ruta=almacenamiento.guardar_imagen(eid, producto.id, foto, "png"), texto_alt=nombre, principal=True, orden=1))
        png, ancho, alto = preparar_png(foto)
        db.add(ArAsset(empresa_id=eid, producto_id=producto.id, color_id=color.id, ruta=almacenamiento.guardar_imagen(eid, producto.id, png, "png"), ancho=ancho, alto=alto, anclaje=anclaje_desde_png(png).model_dump()))
    db.flush()


def reponer_imagenes(db: Session) -> int:
    """Si una prenda de demostración perdió su archivo (volumen vacío), lo vuelve a escribir en la misma ruta. Devuelve cuántos archivos repuso."""
    repuestos = 0
    for producto in db.scalars(select(Producto).where(Producto.nombre.in_(ARCHIVO_DE))):
        foto = (CARPETA / ARCHIVO_DE[producto.nombre]).read_bytes()
        for imagen in db.scalars(select(ImagenProducto).where(ImagenProducto.producto_id == producto.id)):
            if not almacenamiento.existe_imagen(imagen.ruta):
                almacenamiento.escribir_imagen(imagen.ruta, foto)
                repuestos += 1
        for asset in db.scalars(select(ArAsset).where(ArAsset.producto_id == producto.id)):
            if not almacenamiento.existe_imagen(asset.ruta):
                almacenamiento.escribir_imagen(asset.ruta, preparar_png(foto)[0])
                repuestos += 1
    return repuestos

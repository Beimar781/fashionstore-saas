"""Prompt L · Prendas de demostración reales — las 7 prendas con su PNG como foto y como recurso del vestidor, anclaje calculado, existencias, aislamiento y reposición del volumen."""
from PIL import Image
from sqlalchemy import select

from app.core import almacenamiento
from app.primer_parcial.catalogo.models import ImagenProducto, Producto, Variante
from app.primer_parcial.ia.models import ArAsset
from app.seed_prendas import CARPETA, PRENDAS, anclaje_desde_png, cargar_prendas, reponer_imagenes

NOMBRES = [p[1] for p in PRENDAS]


def _cargar(db, mundo):
    for empresa in (mundo.a, mundo.b):
        cargar_prendas(db, empresa)
    db.commit()


def _producto(db, empresa, nombre):
    return db.scalar(select(Producto).where(Producto.empresa_id == empresa.id, Producto.nombre == nombre))


def test_01_los_siete_png_del_seed_son_validos_y_miden_1200_px_como_maximo():
    assert len(PRENDAS) == 7
    for archivo, *_ in PRENDAS:
        with Image.open(CARPETA / archivo) as imagen:
            assert max(imagen.size) <= 1200 and imagen.mode == "RGBA", archivo
            assert imagen.getchannel("A").getextrema()[0] == 0, archivo  # con píxeles transparentes


def test_02_cada_empresa_recibe_las_siete_prendas_con_precios_distintos(inv, mundo, tienda_b, db):
    _cargar(db, mundo)
    for nombre in NOMBRES:
        a, b = _producto(db, mundo.a, nombre), _producto(db, mundo.b, nombre)
        assert a is not None and b is not None and a.id != b.id and a.precio_base != b.precio_base, nombre
    cargar_prendas(db, mundo.a)  # idempotente
    assert len(list(db.scalars(select(Producto).where(Producto.empresa_id == mundo.a.id, Producto.nombre.in_(NOMBRES))))) == 7


def test_03_color_real_tallas_del_grupo_y_existencias(inv, mundo, tienda_b, db):
    _cargar(db, mundo)
    polo = _producto(db, mundo.a, "Polo Blanco")
    variantes = list(db.scalars(select(Variante).where(Variante.producto_id == polo.id)))
    assert sorted(v.talla.codigo for v in variantes) == ["L", "M", "S", "XL"] and {v.color.nombre for v in variantes} == {"Blanco"}
    assert polo.categoria_id and {v.talla.grupo_id for v in variantes} == {polo_categoria_grupo(db, polo)}
    mostaza = db.scalar(select(Variante).where(Variante.producto_id == _producto(db, mundo.a, "Camiseta Mostaza").id))
    assert mostaza.color.nombre == "Mostaza" and mostaza.color.codigo_hex == "#D4A017"


def polo_categoria_grupo(db, producto):
    from app.primer_parcial.catalogo.models import Categoria

    return db.get(Categoria, producto.categoria_id).grupo_talla_id


def test_04_la_imagen_es_la_foto_y_el_png_del_vestidor_con_anclaje_calculado(inv, mundo, tienda_b, db, client):
    _cargar(db, mundo)
    for nombre in NOMBRES:
        producto = _producto(db, mundo.a, nombre)
        foto = db.scalar(select(ImagenProducto).where(ImagenProducto.producto_id == producto.id))
        asset = db.scalar(select(ArAsset).where(ArAsset.producto_id == producto.id))
        assert foto.principal and asset.ancho <= 800 and 0.02 <= asset.anclaje["y_hombros"] <= 0.5, nombre
        assert 0.4 <= asset.anclaje["ancho_hombros"] <= 1.0 and asset.anclaje["y_cadera"] > asset.anclaje["y_hombros"], nombre
        d = client.get(f"/api/vestidor/productos/{producto.id}", headers=inv.h_cliente).json()
        assert d["admite"] is True and d["colores"][0]["listo"] is True and client.get(d["colores"][0]["imagen_url"]).status_code == 200, nombre


def test_05_el_anclaje_sale_del_recuadro_visible_de_la_prenda():
    anclajes = {archivo: anclaje_desde_png((CARPETA / archivo).read_bytes()) for archivo, *_ in PRENDAS}
    raglan = anclajes["camiseta-raglan-gris.png"]  # lienzo 800x1200 con la prenda entre y=137 y y=1039: los hombros quedan ~8 % bajo el borde superior de la prenda
    assert abs(raglan.y_hombros - (137 + 0.08 * 902) / 1200) < 0.01
    assert abs(raglan.y_cadera - (137 + 0.95 * 902) / 1200) < 0.01
    assert anclajes["polo-blanco.png"].y_hombros < 0.1  # el polo casi toca el borde superior


def test_06_cada_empresa_solo_ve_sus_archivos(inv, mundo, tienda_b, db, client):
    _cargar(db, mundo)
    de_a = _producto(db, mundo.a, "Polo Blanco")
    assert client.get(f"/api/vestidor/productos/{de_a.id}", headers=tienda_b.h_admin).status_code == 404
    ruta_a = db.scalar(select(ArAsset.ruta).where(ArAsset.producto_id == de_a.id))
    assert ruta_a.startswith(f"{mundo.a.id}/")
    assert not any(r.startswith(f"{mundo.a.id}/") for r in db.scalars(select(ArAsset.ruta).where(ArAsset.empresa_id == mundo.b.id)))


def test_07_si_el_volumen_esta_vacio_se_reponen_las_imagenes(inv, mundo, tienda_b, db, client):
    _cargar(db, mundo)
    producto = _producto(db, mundo.a, "Chaqueta de Cuero Negra")
    foto = db.scalar(select(ImagenProducto.ruta).where(ImagenProducto.producto_id == producto.id))
    asset = db.scalar(select(ArAsset.ruta).where(ArAsset.producto_id == producto.id))
    assert reponer_imagenes(db) == 0  # nada que reponer
    almacenamiento.borrar_imagen(foto)
    almacenamiento.borrar_imagen(asset)
    assert client.get(almacenamiento.url_media(foto)).status_code == 404
    assert reponer_imagenes(db) == 2
    assert client.get(almacenamiento.url_media(foto)).status_code == 200 and client.get(almacenamiento.url_media(asset)).status_code == 200

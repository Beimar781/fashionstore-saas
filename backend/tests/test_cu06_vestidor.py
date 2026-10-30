"""CU-06 Vestidor virtual — el recurso AR de cada prenda superior por color: PNG con fondo transparente, anclaje, solo prendas superiores y aislamiento por empresa."""
import io

from PIL import Image

from app.primer_parcial.ia.cu06_vestidor.imagen import MSG_PNG
from app.primer_parcial.ia.cu06_vestidor.service import MSG_NO_ADMITE, MSG_SOLO_SUPERIORES, escala_de
from tests.catalogo_util import por_variante, talla_id


def _png(ancho=400, alto=500, transparente=True, formato="PNG"):
    """Una camiseta sencilla: tela roja sobre fondo transparente (o blanco, si se pide opaco)."""
    imagen = Image.new("RGBA", (ancho, alto), (0, 0, 0, 0) if transparente else (255, 255, 255, 255))
    for x in range(ancho // 4, ancho * 3 // 4):
        for y in range(alto // 8, alto * 7 // 8, 3):
            imagen.putpixel((x, y), (200, 30, 30, 255))
    if formato == "JPEG":
        imagen = imagen.convert("RGB")
    salida = io.BytesIO()
    imagen.save(salida, format=formato)
    return salida.getvalue()


def _subir(client, h, producto, color, contenido=None, nombre="camisa.png", **anclaje):
    datos = {k: str(v) for k, v in anclaje.items()}
    return client.put(f"/api/vestidor/productos/{producto['id']}/colores/{color['id']}", files={"archivo": (nombre, contenido if contenido is not None else _png(), "image/png")}, data=datos, headers=h)


def _ver(client, h, producto):
    return client.get(f"/api/vestidor/productos/{producto['id']}", headers=h)


def _jean(inv, mundo):
    jean = inv.producto("Jean", inv.pantalones["id"], inv.col["id"], [talla_id(inv.numerico, "30")], [inv.rojo["id"]], precio="180.00")
    return jean


def test_01_el_administrador_sube_el_png_y_queda_listo_para_el_vestidor(inv, client):
    r = _subir(client, inv.h_admin, inv.camisa, inv.rojo, y_hombros=0.12, ancho_hombros=0.8)
    assert r.status_code == 200, r.text
    d = r.json()
    assert (d["color"], d["listo"], d["ancho"], d["alto"]) == ("Rojo", True, 400, 500)
    assert d["anclaje"] == {"y_hombros": 0.12, "ancho_hombros": 0.8, "y_cadera": 0.92, "ajuste": 1.0}
    assert d["imagen_url"].startswith("/media/") and f"/productos/{inv.camisa['id']}/" in d["imagen_url"]
    archivo = client.get(d["imagen_url"])
    assert archivo.status_code == 200 and archivo.content[:8] == b"\x89PNG\r\n\x1a\n"


def test_02_el_png_grande_se_reduce_a_800_px_de_ancho(inv, client):
    d = _subir(client, inv.h_admin, inv.camisa, inv.rojo, _png(1600, 1200)).json()
    assert (d["ancho"], d["alto"]) == (800, 600)
    guardada = Image.open(io.BytesIO(client.get(d["imagen_url"]).content))
    assert guardada.size == (800, 600) and guardada.mode == "RGBA"


def test_03_subir_otra_vez_reemplaza_el_anterior_y_borra_el_archivo_viejo(inv, client):
    primero = _subir(client, inv.h_admin, inv.camisa, inv.rojo).json()
    segundo = _subir(client, inv.h_admin, inv.camisa, inv.rojo, _png(300, 300)).json()
    assert segundo["imagen_url"] != primero["imagen_url"] and (segundo["ancho"], segundo["alto"]) == (300, 300)
    assert client.get(primero["imagen_url"]).status_code == 404  # el archivo anterior ya no queda en disco
    rojo = next(c for c in _ver(client, inv.h_admin, inv.camisa).json()["colores"] if c["color"] == "Rojo")
    assert rojo["imagen_url"] == segundo["imagen_url"]


def test_04_solo_se_aceptan_png_con_fondo_transparente(inv, client):
    for contenido, nombre in ((_png(formato="JPEG"), "camisa.jpg"), (_png(transparente=False), "opaco.png"), (b"no es una imagen", "texto.png"), (_png()[:60], "cortado.png")):
        r = _subir(client, inv.h_admin, inv.camisa, inv.rojo, contenido, nombre)
        assert r.status_code == 422 and r.json()["detail"] == MSG_PNG, nombre
    assert next(c for c in _ver(client, inv.h_admin, inv.camisa).json()["colores"] if c["color"] == "Rojo")["listo"] is False  # nada quedó guardado


def test_05_solo_las_prendas_superiores_admiten_vestidor(inv, mundo, client):
    jean = _jean(inv, mundo)
    r = _subir(client, inv.h_admin, jean, inv.rojo)
    assert r.status_code == 422 and r.json()["detail"] == MSG_SOLO_SUPERIORES
    d = _ver(client, inv.h_cliente, jean).json()
    assert (d["admite"], d["mensaje"], d["colores"], d["escala_tallas"]) == (False, MSG_NO_ADMITE, [], {}) and MSG_NO_ADMITE == "Esta prenda no admite vestidor."
    assert _ver(client, inv.h_cliente, inv.camisa).json()["admite"] is True


def test_06_el_color_debe_ser_de_una_variante_del_producto(inv, client):
    turquesa = client.post("/api/colores", json={"nombre": "Turquesa", "codigo_hex": "#12ABCD"}, headers=inv.h_admin).json()
    r = _subir(client, inv.h_admin, inv.camisa, turquesa)
    assert r.status_code == 422 and r.json()["detail"] == "El producto no tiene prendas de ese color."


def test_07_los_puntos_de_anclaje_se_validan(inv, client):
    for malo in ({"ancho_hombros": 2}, {"y_hombros": -1}, {"ajuste": 0}):
        r = _subir(client, inv.h_admin, inv.camisa, inv.rojo, **malo)
        assert r.status_code == 422 and r.json()["detail"] == "Los puntos de anclaje de la prenda no son válidos.", malo


def test_08_el_cliente_ve_los_colores_listos_y_la_escala_por_talla(inv, client):
    _subir(client, inv.h_admin, inv.camisa, inv.rojo)
    d = _ver(client, inv.h_cliente, inv.camisa).json()
    assert [(c["color"], c["listo"]) for c in d["colores"]] == [("Azul", False), ("Rojo", True)]
    assert d["colores"][1]["anclaje"]["ancho_hombros"] == 0.85 and d["colores"][0]["imagen_url"] is None
    assert d["escala_tallas"] == {"M": 1.0, "S": 0.96}
    assert (escala_de("30"), escala_de("xl"), escala_de("Única")) == (1.0, 1.10, 1.0)  # por código, con valor por defecto para tallas numéricas u otras


def test_09_quitar_la_imagen_y_roles(inv, client):
    d = _subir(client, inv.h_admin, inv.camisa, inv.rojo).json()
    assert _subir(client, inv.h_cliente, inv.camisa, inv.rojo).status_code == 403  # el Cliente no sube imágenes
    assert client.delete(f"/api/vestidor/productos/{inv.camisa['id']}/colores/{inv.rojo['id']}", headers=inv.h_cajero).status_code == 403
    assert _ver(client, inv.h_cajero, inv.camisa).status_code == 403
    assert client.get(f"/api/vestidor/productos/{inv.camisa['id']}").status_code in (401, 403)
    assert client.delete(f"/api/vestidor/productos/{inv.camisa['id']}/colores/{inv.rojo['id']}", headers=inv.h_admin).status_code == 204
    assert client.get(d["imagen_url"]).status_code == 404
    assert next(c for c in _ver(client, inv.h_admin, inv.camisa).json()["colores"] if c["color"] == "Rojo")["listo"] is False
    assert client.delete(f"/api/vestidor/productos/{inv.camisa['id']}/colores/{inv.rojo['id']}", headers=inv.h_admin).status_code == 404


def test_10_aislamiento_entre_empresas(inv, mundo, tienda_b, datos, client):
    d = _subir(client, inv.h_admin, inv.camisa, inv.rojo).json()
    h_b = datos.login(mundo.admin_b, mundo.b)
    assert _subir(client, h_b, inv.camisa, inv.rojo).status_code == 404  # el producto de EMP-A no existe para EMP-B
    assert _ver(client, h_b, inv.camisa).status_code == 404
    assert client.delete(f"/api/vestidor/productos/{inv.camisa['id']}/colores/{inv.rojo['id']}", headers=h_b).status_code == 404
    assert _ver(client, inv.h_cliente, inv.camisa).json()["colores"][1]["imagen_url"] == d["imagen_url"]  # y a EMP-A no le pasó nada
    # EMP-B sube sus propias prendas sin ver las de A
    camisa_b = tienda_b.producto("Camisa B", tienda_b.camisas["id"], tienda_b.col["id"], [talla_id(tienda_b.alfa, "S")], [tienda_b.rojo["id"]])
    assert _subir(client, h_b, camisa_b, tienda_b.rojo).status_code == 200
    assert [c["listo"] for c in _ver(client, h_b, camisa_b).json()["colores"]] == [True]


def test_11_el_png_de_demostracion_del_seed_es_valido():
    from app.primer_parcial.ia.cu06_vestidor.imagen import preparar_png
    from app.seed_prendas import CARPETA

    png, ancho, alto = preparar_png((CARPETA / "polo-blanco.png").read_bytes())  # 1200 x 1200 en el seed; el vestidor lo guarda a 800 px de ancho
    assert (ancho, alto) == (800, 800) and png[:8] == b"\x89PNG\r\n\x1a\n"

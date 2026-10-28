"""CU-18 Gestionar productos — caja negra (pasos de la ficha), lecciones del primer parcial y aislamiento."""
import pytest

from app.core.config import get_settings
from tests.catalogo_util import PNG, talla_id

SIN_VARIANTES = "Debe especificar al menos una talla y un color para el producto."


@pytest.fixture
def media(tmp_path, monkeypatch):
    monkeypatch.setattr(get_settings(), "media_dir", str(tmp_path))
    return tmp_path


def _camisa(t, **extra):
    tallas = [talla_id(t.alfa, "S"), talla_id(t.alfa, "M")]
    return t.producto("Camisa Oxford", t.camisas["id"], t.col["id"], tallas, [t.rojo["id"], t.azul["id"]], **extra)


def test_01_registrar_producto_con_datos_completos(tienda_a, client):
    p = _camisa(tienda_a, descripcion="Algodón", material="100% algodón", cuidado="Lavar a 30°")
    assert p["nombre"] == "Camisa Oxford" and p["slug"] == "camisa-oxford" and p["activo"] is True
    assert (p["precio_base"], p["material"]) == ("100.00", "100% algodón")


def test_02_asociar_categoria_temporada_y_marca(tienda_a, client):
    marca = client.post("/api/marcas", json={"nombre": "Andes"}, headers=tienda_a.h_admin).json()
    p = _camisa(tienda_a, marca_id=marca["id"])
    assert (p["categoria"], p["coleccion"], p["temporada"], p["marca"]) == ("Camisas", "Colección Urbana", "Primavera-Verano 2026", "Andes")


def test_03_generar_variantes_talla_por_color(tienda_a, client):
    p = _camisa(tienda_a)
    assert len(p["variantes"]) == 4  # 2 tallas × 2 colores
    assert len({v["sku"] for v in p["variantes"]}) == 4
    r = client.post(f"/api/productos/{p['id']}/variantes", headers=tienda_a.h_admin, json={
        "tallas_ids": [talla_id(tienda_a.alfa, "S"), talla_id(tienda_a.alfa, "L")], "colores_ids": [tienda_a.rojo["id"]]})
    assert r.status_code == 201 and (r.json()["creadas"], r.json()["omitidas"]) == (1, 1)  # S/Rojo ya existía


def test_04_publicar_sin_variantes(tienda_a, client):
    h = tienda_a.h_admin
    cuerpo = {"nombre": "Vacía", "categoria_id": tienda_a.camisas["id"], "coleccion_id": tienda_a.col["id"], "genero": "UNISEX", "precio_base": "50"}
    for extra in ({}, {"tallas_ids": [talla_id(tienda_a.alfa, "S")]}, {"colores_ids": [tienda_a.rojo["id"]]}):
        r = client.post("/api/productos", json={**cuerpo, **extra}, headers=h)
        assert r.status_code == 422 and r.json()["detail"] == SIN_VARIANTES
    p = _camisa(tienda_a)
    for v in p["variantes"]:
        client.put(f"/api/productos/{p['id']}/variantes/{v['id']}", json={"activa": False}, headers=h)
    client.post(f"/api/productos/{p['id']}/desactivar", headers=h)
    r = client.post(f"/api/productos/{p['id']}/activar", headers=h)  # publicar sin variantes activas
    assert r.status_code == 422 and r.json()["detail"] == SIN_VARIANTES


def test_05_subir_fotografias_y_ver_el_producto_en_el_catalogo(datos, mundo, tienda_a, client, media):
    p = _camisa(tienda_a)
    r = client.post(f"/api/productos/{p['id']}/imagenes", headers=tienda_a.h_admin, files={"archivo": ("foto.png", PNG, "image/png")},
                    data={"texto_alt": "Frente"})
    assert r.status_code == 201 and r.json()["principal"] is True  # la primera imagen es la principal
    ruta = r.json()["url"].removeprefix("/media/")
    assert ruta.startswith(f"{mundo.a.id}/productos/{p['id']}/") and (media / ruta).exists()  # una carpeta por empresa
    cliente = datos.usuario(mundo.a, "Cliente", email="cliente@emp-a.com")
    catalogo = client.get("/api/catalogo/productos", headers=datos.login(cliente, mundo.a)).json()
    assert [x["nombre"] for x in catalogo["items"]] == ["Camisa Oxford"] and catalogo["items"][0]["imagen"] == r.json()["url"]


def test_imagen_se_valida_por_contenido_no_por_nombre(tienda_a, client, media):
    p = _camisa(tienda_a)
    r = client.post(f"/api/productos/{p['id']}/imagenes", headers=tienda_a.h_admin,
                    files={"archivo": ("virus.png", b"MZ\x90\x00 no soy una imagen", "image/png")})
    assert r.status_code == 422 and r.json()["detail"] == "La imagen debe ser JPG, PNG o WEBP de hasta 5 MB."


def test_cambiar_imagen_principal_y_eliminar(tienda_a, client, media):
    p = _camisa(tienda_a)
    h = tienda_a.h_admin
    ids = [client.post(f"/api/productos/{p['id']}/imagenes", headers=h, files={"archivo": (f"{i}.png", PNG, "image/png")}).json()["id"] for i in range(2)]
    detalle = client.post(f"/api/productos/{p['id']}/imagenes/{ids[1]}/principal", headers=h).json()
    assert [i["id"] for i in detalle["imagenes"] if i["principal"]] == [ids[1]]
    assert client.delete(f"/api/productos/{p['id']}/imagenes/{ids[1]}", headers=h).status_code == 204
    assert [i["principal"] for i in client.get(f"/api/productos/{p['id']}", headers=h).json()["imagenes"]] == [True]  # hereda la principal


def test_sku_corto_y_unico_aunque_los_nombres_sean_largos(tienda_a, client):
    h = tienda_a.h_admin
    larga = client.post("/api/tallas", json={"grupo_id": tienda_a.alfa["id"], "codigo": "XXXXXXXX"}, headers=h).json()
    color = tienda_a.color("Azul petróleo muy oscuro con reflejos plateados")
    p = tienda_a.producto("Camisa", tienda_a.camisas["id"], tienda_a.col["id"], [larga["id"]], [color["id"]])
    sku = p["variantes"][0]["sku"]
    assert len(sku) <= 40 and sku == f"P{p['id']}-XXXXXXXX-{color['codigo']}"  # el código corto del color, no su slug
    client.put(f"/api/colores/{color['id']}", json={"nombre": "Otro nombre"}, headers=h)
    assert client.get(f"/api/productos/{p['id']}", headers=h).json()["variantes"][0]["sku"] == sku  # renombrar no cambia el SKU


def test_talla_de_otro_grupo_se_rechaza(tienda_a, client):
    r = client.post("/api/productos", headers=tienda_a.h_admin, json={
        "nombre": "Mezcla", "categoria_id": tienda_a.camisas["id"], "coleccion_id": tienda_a.col["id"], "genero": "UNISEX",
        "precio_base": "80", "tallas_ids": [talla_id(tienda_a.alfa, "M"), talla_id(tienda_a.numerico, "30")],
        "colores_ids": [tienda_a.rojo["id"]]})
    assert r.status_code == 422 and r.json()["detail"] == "La talla 30 no pertenece al grupo de tallas de la categoría."
    assert client.get("/api/productos", headers=tienda_a.h_admin).json()["total"] == 0  # no quedó nada a medias


def test_subcategoria_hereda_el_grupo_de_tallas(tienda_a, client):
    sub = tienda_a.categoria("Camisas formales", padre_id=tienda_a.camisas["id"])
    p = tienda_a.producto("Formal", sub["id"], tienda_a.col["id"], [talla_id(tienda_a.alfa, "M")], [tienda_a.rojo["id"]])
    assert p["categoria"] == "Camisas formales"
    sin_grupo = tienda_a.categoria("Accesorios")
    r = client.post("/api/productos", headers=tienda_a.h_admin, json={
        "nombre": "Gorra", "categoria_id": sin_grupo["id"], "coleccion_id": tienda_a.col["id"], "genero": "UNISEX",
        "precio_base": "20", "tallas_ids": [talla_id(tienda_a.alfa, "M")], "colores_ids": [tienda_a.rojo["id"]]})
    assert r.status_code == 422 and "no tiene grupo de tallas" in r.json()["detail"]


def test_editar_producto_y_variante(tienda_a, client):
    h = tienda_a.h_admin
    p = _camisa(tienda_a)
    r = client.put(f"/api/productos/{p['id']}", json={"nombre": "Camisa Oxford Slim", "precio_base": "120.50"}, headers=h)
    assert (r.json()["nombre"], r.json()["precio_base"], r.json()["slug"]) == ("Camisa Oxford Slim", "120.50", "camisa-oxford")
    v1, v2 = p["variantes"][:2]
    ok = client.put(f"/api/productos/{p['id']}/variantes/{v1['id']}", json={"precio_especifico": "99", "codigo_barras": "7790001"}, headers=h)
    assert ok.status_code == 200 and ok.json()["precio"] == "99.00"
    dup = client.put(f"/api/productos/{p['id']}/variantes/{v2['id']}", json={"codigo_barras": "7790001"}, headers=h)
    assert dup.status_code == 409 and dup.json()["detail"] == "Ese código de barras ya está en uso."
    # cambiar a una categoría con otro grupo de tallas dejaría variantes inválidas
    r = client.put(f"/api/productos/{p['id']}", json={"categoria_id": tienda_a.pantalones["id"]}, headers=h)
    assert r.status_code == 409


def test_retirar_del_catalogo_y_aislamiento(tienda_a, tienda_b, client):
    p = _camisa(tienda_a)
    h = tienda_a.h_admin
    assert client.post(f"/api/productos/{p['id']}/desactivar", headers=h).json()["activo"] is False
    # la empresa B no ve, no edita ni usa piezas de A
    assert client.get(f"/api/productos/{p['id']}", headers=tienda_b.h_admin).status_code == 404
    assert client.put(f"/api/productos/{p['id']}", json={"nombre": "Xy"}, headers=tienda_b.h_admin).status_code == 404
    assert client.post(f"/api/productos/{p['id']}/imagenes", headers=tienda_b.h_admin, files={"archivo": ("a.png", PNG, "image/png")}).status_code == 404
    assert client.get("/api/productos", headers=tienda_b.h_admin).json()["total"] == 0
    r = client.post("/api/productos", headers=tienda_b.h_admin, json={
        "nombre": "Cruzado", "categoria_id": tienda_a.camisas["id"], "coleccion_id": tienda_b.col["id"], "genero": "UNISEX",
        "precio_base": "10", "tallas_ids": [talla_id(tienda_b.alfa, "S")], "colores_ids": [tienda_b.rojo["id"]]})
    assert r.status_code == 404  # categoría de otra empresa

"""CU-16 Gestionar categorías, tallas y colores — caja negra (pasos de la ficha) + aislamiento entre empresas."""
from app.core.constantes import CLIENTE

DUPLICADO = "Este atributo ya existe en el sistema."


def test_01_seleccionar_tabla_de_tallas_muestra_los_valores(tienda_a, client):
    grupos = client.get("/api/grupos-talla", headers=tienda_a.h_admin).json()
    superior = next(g for g in grupos if g["nombre"] == "Ropa superior")
    assert [t["codigo"] for t in superior["tallas"]] == ["S", "M", "L", "XL"]  # por orden, no por creación


def test_02_registrar_nueva_talla(tienda_a, client):
    r = client.post("/api/tallas", json={"grupo_id": tienda_a.alfa["id"], "codigo": "xxl"}, headers=tienda_a.h_admin)
    assert r.status_code == 201
    assert (r.json()["codigo"], r.json()["orden"]) == ("XXL", 5)  # mayúsculas y al final del grupo


def test_03_registrar_talla_duplicada(tienda_a, client):
    r = client.post("/api/tallas", json={"grupo_id": tienda_a.alfa["id"], "codigo": "m"}, headers=tienda_a.h_admin)
    assert r.status_code == 409 and r.json()["detail"] == DUPLICADO


def test_04_editar_un_color_existente(tienda_a, client):
    r = client.put(f"/api/colores/{tienda_a.rojo['id']}", json={"codigo_hex": "#ff0000", "nombre": "Rojo vino"}, headers=tienda_a.h_admin)
    assert r.status_code == 200
    assert (r.json()["nombre"], r.json()["codigo_hex"]) == ("Rojo vino", "#FF0000")
    assert r.json()["codigo"] == tienda_a.rojo["codigo"]  # el código corto del SKU no cambia al renombrar


def test_05_el_atributo_queda_disponible_al_crear_productos(tienda_a, client):
    nueva = client.post("/api/colores", json={"nombre": "Turquesa", "codigo_hex": "#00CCCC"}, headers=tienda_a.h_admin).json()
    producto = tienda_a.producto("Polo", tienda_a.camisas["id"], tienda_a.col["id"], [tienda_a.alfa["tallas"][0]["id"]], [nueva["id"]])
    assert producto["variantes"][0]["color"] == "Turquesa"


def test_color_y_categoria_duplicados(tienda_a, client):
    r = client.post("/api/colores", json={"nombre": "rojo", "codigo_hex": "#111111"}, headers=tienda_a.h_admin)
    assert r.status_code == 409 and r.json()["detail"] == DUPLICADO
    r = client.post("/api/categorias", json={"nombre": "CAMISAS"}, headers=tienda_a.h_admin)
    assert r.status_code == 409 and r.json()["detail"] == DUPLICADO
    r = client.post("/api/marcas", json={"nombre": "Nike"}, headers=tienda_a.h_admin)
    assert r.status_code == 201
    assert client.post("/api/marcas", json={"nombre": "nike"}, headers=tienda_a.h_admin).status_code == 409


def test_codigo_corto_del_color_es_unico_en_la_empresa(tienda_a, client):
    a = client.post("/api/colores", json={"nombre": "Rojo claro", "codigo_hex": "#EE0000"}, headers=tienda_a.h_admin).json()
    b = client.post("/api/colores", json={"nombre": "Rojo oscuro", "codigo_hex": "#880000"}, headers=tienda_a.h_admin).json()
    assert len({tienda_a.rojo["codigo"], a["codigo"], b["codigo"]}) == 3 and len(b["codigo"]) <= 6


def test_subcategoria_y_ciclos(tienda_a, client):
    sub = tienda_a.categoria("Camisas formales", padre_id=tienda_a.camisas["id"])
    r = client.put(f"/api/categorias/{tienda_a.camisas['id']}", json={"padre_id": sub["id"]}, headers=tienda_a.h_admin)
    assert r.status_code == 422 and "no puede ser hija" in r.json()["detail"]


def test_eliminar_solo_si_no_esta_en_uso(tienda_a, client):
    tienda_a.producto("Polo", tienda_a.camisas["id"], tienda_a.col["id"], [tienda_a.alfa["tallas"][0]["id"]], [tienda_a.rojo["id"]])
    r = client.delete(f"/api/colores/{tienda_a.rojo['id']}", headers=tienda_a.h_admin)
    assert r.status_code == 409 and r.json()["detail"] == "No se puede eliminar: el atributo está en uso."
    assert client.delete(f"/api/colores/{tienda_a.verde['id']}", headers=tienda_a.h_admin).status_code == 204


def test_solo_el_administrador_escribe_y_los_demas_leen_lo_activo(datos, mundo, tienda_a, client):
    client.put(f"/api/categorias/{tienda_a.pantalones['id']}", json={"activa": False}, headers=tienda_a.h_admin)
    cliente = datos.usuario(mundo.a, CLIENTE, email="cliente@emp-a.com")
    h = datos.login(cliente, mundo.a)
    assert client.post("/api/colores", json={"nombre": "Negro", "codigo_hex": "#000000"}, headers=h).status_code == 403
    visibles = [c["nombre"] for c in client.get("/api/categorias", headers=h).json()]
    assert visibles == ["Camisas"]  # la categoría inactiva solo la ve el Administrador
    assert len(client.get("/api/categorias", headers=tienda_a.h_admin).json()) == 2


def test_aislamiento_entre_empresas(tienda_a, tienda_b, client):
    nombres_b = {c["nombre"] for c in client.get("/api/colores", headers=tienda_b.h_admin).json()}
    assert nombres_b == {"Rojo", "Azul", "Verde"}  # los mismos nombres en otra empresa están permitidos
    ids_a = {c["id"] for c in client.get("/api/colores", headers=tienda_a.h_admin).json()}
    assert not ids_a & {c["id"] for c in client.get("/api/colores", headers=tienda_b.h_admin).json()}
    # recurso de otra empresa ⇒ 404
    assert client.put(f"/api/colores/{tienda_a.rojo['id']}", json={"nombre": "Hackeado"}, headers=tienda_b.h_admin).status_code == 404
    assert client.delete(f"/api/categorias/{tienda_a.camisas['id']}", headers=tienda_b.h_admin).status_code == 404
    r = client.post("/api/tallas", json={"grupo_id": tienda_a.alfa["id"], "codigo": "XS"}, headers=tienda_b.h_admin)
    assert r.status_code == 404
    r = client.post("/api/categorias", json={"nombre": "Nueva", "grupo_talla_id": tienda_a.alfa["id"]}, headers=tienda_b.h_admin)
    assert r.status_code == 404

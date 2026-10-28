"""CU-04 Buscar y filtrar prendas — caja negra, errores del primer parcial (sección 9 del plan) y aislamiento."""
import pytest

from tests.catalogo_util import cabecera_cliente, por_variante, talla_id


@pytest.fixture
def mundo_busqueda(datos, mundo, tienda_a, client):
    """Tres prendas: una con M/Rojo y L/Azul (NO existe M/Azul), una solo L/Rojo y un pantalón 30/Verde."""
    t = tienda_a
    t.camisa = t.producto("Camisa Oxford", t.camisas["id"], t.col["id"], [talla_id(t.alfa, "M"), talla_id(t.alfa, "L")], [t.rojo["id"], t.azul["id"]],
                          precio="100", genero="MASCULINO")
    t.camisa_ids = por_variante(t.camisa)
    # a la camisa se le quitan las variantes M/Azul y L/Rojo: quedan M/Rojo y L/Azul
    for combinacion in (("M", "Azul"), ("L", "Rojo")):
        client.put(f"/api/productos/{t.camisa['id']}/variantes/{t.camisa_ids[combinacion]['id']}", json={"activa": False}, headers=t.h_admin)
    t.blusa = t.producto("Blusa Floral", t.camisas["id"], t.col["id"], [talla_id(t.alfa, "L")], [t.rojo["id"]], precio="150", genero="FEMENINO")
    t.jean = t.producto("Jean Clásico", t.pantalones["id"], t.col["id"], [talla_id(t.numerico, "30")], [t.verde["id"]], precio="250", genero="UNISEX")
    t.centro, t.norte = datos.sucursal(mundo.a, "Centro"), datos.sucursal(mundo.a, "Norte")
    t.h_cliente = cabecera_cliente(datos, mundo.a)
    return t


def _buscar(t, client, **filtros):
    r = client.get("/api/catalogo/buscar", params=filtros, headers=t.h_cliente)
    assert r.status_code == 200, r.text
    return [p["nombre"] for p in r.json()["items"]]


def test_01_busqueda_por_texto(mundo_busqueda, client):
    t = mundo_busqueda
    assert _buscar(t, client, q="camisa") == ["Camisa Oxford"]
    assert _buscar(t, client, q="  FLORAL ") == ["Blusa Floral"]
    assert _buscar(t, client, q="zapatilla") == []


def test_02_filtros_de_categoria_marca_genero_y_precio(mundo_busqueda, client):
    t = mundo_busqueda
    assert set(_buscar(t, client, categoria_id=t.camisas["id"])) == {"Camisa Oxford", "Blusa Floral"}
    assert _buscar(t, client, genero="FEMENINO") == ["Blusa Floral"]
    assert set(_buscar(t, client, precio_min=120)) == {"Blusa Floral", "Jean Clásico"}
    assert _buscar(t, client, precio_min=120, precio_max=200) == ["Blusa Floral"]
    assert _buscar(t, client, temporada_id=t.temp["id"]).__len__() == 3


def test_03_orden_de_los_resultados(mundo_busqueda, client):
    t = mundo_busqueda
    assert _buscar(t, client, orden="precio_asc") == ["Camisa Oxford", "Blusa Floral", "Jean Clásico"]
    assert _buscar(t, client, orden="precio_desc") == ["Jean Clásico", "Blusa Floral", "Camisa Oxford"]
    assert _buscar(t, client, orden="nombre") == ["Blusa Floral", "Camisa Oxford", "Jean Clásico"]


def test_04_talla_y_color_se_aplican_a_la_misma_variante(mundo_busqueda, client):
    t = mundo_busqueda
    # La camisa tiene una variante M y otra Azul, pero NO existe M/Azul: no debe salir.
    assert _buscar(t, client, talla="M", color_id=t.azul["id"]) == []
    assert _buscar(t, client, talla="M", color_id=t.rojo["id"]) == ["Camisa Oxford"]
    assert _buscar(t, client, talla="l", color_id=t.azul["id"]) == ["Camisa Oxford"]  # el código no distingue mayúsculas
    assert set(_buscar(t, client, talla="L", color_id=t.rojo["id"])) == {"Blusa Floral"}  # la L/Rojo de la camisa está desactivada


def test_05_sucursal_exige_variante_activa_con_stock_que_coincida(mundo, mundo_busqueda, client):
    t = mundo_busqueda
    ids = por_variante(client.get(f"/api/productos/{t.camisa['id']}", headers=t.h_admin).json())
    t.stock(mundo.a.id, t.centro.id, ids[("M", "Rojo")]["id"], 4)       # activa, con stock
    t.stock(mundo.a.id, t.centro.id, ids[("L", "Rojo")]["id"], 9)       # con stock pero DESACTIVADA
    t.stock(mundo.a.id, t.norte.id, ids[("L", "Azul")]["id"], 2)        # con stock, pero en otra sucursal
    assert _buscar(t, client, sucursal=t.centro.id) == ["Camisa Oxford"]
    assert _buscar(t, client, sucursal=t.centro.id, talla="L") == []     # su L con stock en Centro está desactivada
    assert _buscar(t, client, sucursal=t.centro.id, talla="M", color_id=t.rojo["id"]) == ["Camisa Oxford"]
    assert _buscar(t, client, sucursal=t.centro.id, color_id=t.azul["id"]) == []  # la L/Azul solo tiene stock en Norte
    assert _buscar(t, client, sucursal=t.norte.id, talla="L", color_id=t.azul["id"]) == ["Camisa Oxford"]
    assert _buscar(t, client, solo_disponibles=True) == ["Camisa Oxford"]  # con stock en alguna sucursal


def test_06_la_tarjeta_indica_disponibilidad_en_la_sucursal(mundo, mundo_busqueda, client):
    t = mundo_busqueda
    ids = por_variante(client.get(f"/api/productos/{t.camisa['id']}", headers=t.h_admin).json())
    t.stock(mundo.a.id, t.norte.id, ids[("M", "Rojo")]["id"], 1)
    r = client.get("/api/catalogo/buscar", params={"q": "camisa"}, headers=t.h_cliente).json()["items"][0]
    assert r["disponible"] is True
    r = client.get("/api/catalogo/productos", params={"sucursal": t.centro.id}, headers=t.h_cliente).json()["items"]
    assert next(p for p in r if p["nombre"] == "Camisa Oxford")["disponible"] is False  # en Centro no hay stock


def test_07_rango_de_precios_invalido(mundo_busqueda, client):
    r = client.get("/api/catalogo/buscar", params={"precio_min": 300, "precio_max": 100}, headers=mundo_busqueda.h_cliente)
    assert r.status_code == 422 and r.json()["detail"] == "El precio mínimo no puede ser mayor que el máximo."


def test_08_paginacion(mundo_busqueda, client):
    t = mundo_busqueda
    r = client.get("/api/catalogo/buscar", params={"orden": "nombre", "tamano": 2, "pagina": 2}, headers=t.h_cliente).json()
    assert (r["total"], [p["nombre"] for p in r["items"]]) == (3, ["Jean Clásico"])
    assert client.get("/api/catalogo/buscar", params={"tamano": 500}, headers=t.h_cliente).status_code == 422


def test_09_sucursal_ajena_y_sesion(datos, mundo, mundo_busqueda, client):
    t = mundo_busqueda
    ajena = datos.sucursal(mundo.b, "Ajena")
    r = client.get("/api/catalogo/buscar", params={"sucursal": ajena.id}, headers=t.h_cliente)
    assert r.status_code == 404 and r.json()["detail"] == "Sucursal no encontrada."
    assert client.get("/api/catalogo/buscar").status_code == 401
    assert client.get("/api/catalogo/buscar", headers=datos.superadmin()).status_code == 403


def test_10_aislamiento_entre_empresas(datos, mundo, mundo_busqueda, tienda_b, client):
    tienda_b.producto("Camisa Oxford", tienda_b.camisas["id"], tienda_b.col["id"], [talla_id(tienda_b.alfa, "S")], [tienda_b.rojo["id"]], precio="999")
    h_b = cabecera_cliente(datos, mundo.b)
    r = client.get("/api/catalogo/buscar", params={"q": "oxford"}, headers=h_b).json()
    assert [(p["nombre"], p["precio"]) for p in r["items"]] == [("Camisa Oxford", "999.00")]  # solo la de su empresa
    assert client.get("/api/catalogo/buscar", params={"categoria_id": mundo_busqueda.camisas["id"]}, headers=h_b).json()["total"] == 0
    assert client.get("/api/catalogo/buscar", params={"color_id": mundo_busqueda.rojo["id"]}, headers=h_b).json()["total"] == 0

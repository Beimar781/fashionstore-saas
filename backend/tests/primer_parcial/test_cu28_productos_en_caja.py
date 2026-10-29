"""CU-28 Consultar productos en punto de venta — pasos de la ficha (5.2.1) y aislamiento."""
from datetime import date, timedelta

from tests.caja_util import con_barras, stock_listo
from tests.catalogo_util import entrar

MSG_CODIGO = "El código de barras escaneado no coincide con ningún producto registrado en la base de datos."


def test_01_escanear_un_codigo_de_barras_muestra_los_datos_de_la_prenda(inv, mundo, client):
    stock_listo(inv, mundo, centro=7, norte=3)
    con_barras(client, inv, inv.v_sm_rojo, "7790001234")
    r = client.get("/api/caja/productos/codigo/7790001234", headers=inv.h_cajero)
    assert r.status_code == 200
    p = r.json()
    assert (p["producto"], p["talla"], p["color"], p["sku"], p["codigo_barras"], p["precio"], p["precio_final"], p["promocion"]) == (
        "Camisa Oxford", "S", "Rojo", inv.v_sm_rojo["sku"], "7790001234", "100.00", "100.00", None)
    assert client.get(f"/api/caja/productos/codigo/{inv.v_sm_rojo['sku'].lower()}", headers=inv.h_cajero).json()["variante_id"] == inv.v_sm_rojo["id"]  # el SKU también sirve


def test_02_buscar_por_nombre_muestra_las_coincidencias(inv, mundo, client):
    stock_listo(inv, mundo)
    r = client.get("/api/caja/productos", params={"q": "oxford"}, headers=inv.h_cajero).json()
    assert len(r) == 4 and {(p["talla"], p["color"]) for p in r} == {("S", "Rojo"), ("S", "Azul"), ("M", "Rojo"), ("M", "Azul")}
    assert client.get("/api/caja/productos", params={"q": inv.v_sm_rojo["sku"]}, headers=inv.h_cajero).json()[0]["variante_id"] == inv.v_sm_rojo["id"]
    assert client.get("/api/caja/productos", params={"q": "zapatilla"}, headers=inv.h_cajero).json() == []
    assert client.get("/api/caja/productos", params={"q": "o"}, headers=inv.h_cajero).status_code == 422  # búsqueda demasiado corta


def test_03_cada_cajero_ve_el_stock_de_su_sucursal(inv, mundo, datos, client):
    stock_listo(inv, mundo, centro=7, norte=3)
    centro = next(p for p in client.get("/api/caja/productos", params={"q": inv.v_sm_rojo["sku"]}, headers=inv.h_cajero).json())
    assert centro["disponible"] == 7
    norte = client.get("/api/caja/productos", params={"q": inv.v_sm_rojo["sku"]}, headers=inv.h_enc_norte).json()[0]
    assert norte["disponible"] == 3  # el Encargado de Norte ve el stock de Norte


def test_04_un_codigo_no_registrado(inv, mundo, tienda_b, datos, client):
    stock_listo(inv, mundo)
    r = client.get("/api/caja/productos/codigo/000000", headers=inv.h_cajero)
    assert r.status_code == 404 and r.json()["detail"] == MSG_CODIGO
    con_barras(client, inv, inv.v_sm_rojo, "7790001234")
    datos.usuario(mundo.b, "Cajero", email="cajero@b.com", sucursal=datos.sucursal(mundo.b, "Sucursal B"))
    h_b = entrar(client, mundo.b, "cajero@b.com")  # el cajero de otra empresa no encuentra el código de ésta
    r = client.get("/api/caja/productos/codigo/7790001234", headers=h_b)
    assert r.status_code == 404 and r.json()["detail"] == MSG_CODIGO
    assert client.get("/api/caja/productos", params={"q": "oxford"}, headers=h_b).json() == []


def test_05_la_promocion_activa_muestra_el_precio_con_descuento(inv, mundo, client):
    stock_listo(inv, mundo)
    hoy = date.today()
    client.post("/api/promociones", json={"nombre": "Liquidación", "tipo_descuento": "PORCENTAJE", "valor": "20",
                                          "inicia": (hoy - timedelta(days=1)).isoformat(), "termina": (hoy + timedelta(days=5)).isoformat()}, headers=inv.h_admin)
    p = client.get("/api/caja/productos", params={"q": "oxford"}, headers=inv.h_cajero).json()[0]
    assert (p["precio"], p["precio_final"], p["promocion"]) == ("100.00", "80.00", "Liquidación")


def test_06_no_se_ofrecen_prendas_inactivas(inv, mundo, client):
    stock_listo(inv, mundo)
    con_barras(client, inv, inv.v_sm_rojo, "7790001234")
    client.put(f"/api/productos/{inv.camisa['id']}/variantes/{inv.v_sm_rojo['id']}", json={"activa": False}, headers=inv.h_admin)
    assert client.get("/api/caja/productos/codigo/7790001234", headers=inv.h_cajero).status_code == 404
    assert len(client.get("/api/caja/productos", params={"q": "oxford"}, headers=inv.h_cajero).json()) == 3
    client.post(f"/api/productos/{inv.camisa['id']}/desactivar", headers=inv.h_admin)
    assert client.get("/api/caja/productos", params={"q": "oxford"}, headers=inv.h_cajero).json() == []


def test_07_solo_la_caja_consulta_productos(inv, client):
    for h in (inv.h_cliente, inv.h_admin, inv.h_prov):
        assert client.get("/api/caja/productos", params={"q": "oxford"}, headers=h).status_code == 403
        assert client.get("/api/caja/productos/codigo/abc", headers=h).status_code == 403
    assert client.get("/api/caja/productos", params={"q": "oxford"}).status_code == 401

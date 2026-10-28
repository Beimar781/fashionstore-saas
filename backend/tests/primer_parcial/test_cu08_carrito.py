"""CU-08 Gestionar carrito de compras — pasos de la ficha (5.2.1) + aislamiento entre clientes y empresas."""
from datetime import date, timedelta

from tests.catalogo_util import cabecera_cliente, entrar
from tests.compras_util import agregar, agregar_ok, stock_listo

MSG_STOCK = "La cantidad solicitada supera el stock disponible temporalmente."


def test_01_agregar_una_prenda_actualiza_el_contador(inv, mundo, client):
    stock_listo(inv, mundo)
    c = agregar_ok(client, inv.h_cliente, inv.v_sm_rojo, inv.centro)
    assert c["total_unidades"] == 1 and c["sucursal"] == "Centro" and len(c["items"]) == 1
    assert agregar_ok(client, inv.h_cliente, inv.v_sm_rojo)["total_unidades"] == 2  # la misma prenda se suma en una línea
    assert len(client.get("/api/carrito", headers=inv.h_cliente).json()["items"]) == 1


def test_02_ver_el_carrito_con_resumen_cantidades_y_subtotal(inv, mundo, client):
    stock_listo(inv, mundo)
    agregar_ok(client, inv.h_cliente, inv.v_sm_rojo, inv.centro, 2)
    c = agregar_ok(client, inv.h_cliente, inv.var[("M", "Azul")])
    fila = next(i for i in c["items"] if i["sku"] == inv.v_sm_rojo["sku"])
    assert (fila["producto"], fila["talla"], fila["color"], fila["cantidad"], fila["precio_final"], fila["subtotal"], fila["estado"]) == (
        "Camisa Oxford", "S", "Rojo", 2, "100.00", "200.00", "OK")
    assert (c["subtotal"], c["descuento"], c["total"], c["total_unidades"], c["puede_pagar"]) == ("300.00", "0.00", "300.00", 3, True)
    assert c["iva_incluido"] == "34.51"  # 13 % incluido en el precio: 300 × 13 / 113


def test_03_modificar_la_cantidad_recalcula_el_subtotal(inv, mundo, client):
    stock_listo(inv, mundo)
    item = agregar_ok(client, inv.h_cliente, inv.v_sm_rojo, inv.centro)["items"][0]
    c = client.put(f"/api/carrito/items/{item['id']}", json={"cantidad": 4}, headers=inv.h_cliente).json()
    assert (c["items"][0]["cantidad"], c["total"]) == (4, "400.00")
    assert client.put(f"/api/carrito/items/{item['id']}", json={"cantidad": 0}, headers=inv.h_cliente).status_code == 422


def test_04_eliminar_un_item_actualiza_el_resumen(inv, mundo, client):
    stock_listo(inv, mundo)
    agregar_ok(client, inv.h_cliente, inv.v_sm_rojo, inv.centro)
    c = agregar_ok(client, inv.h_cliente, inv.var[("M", "Azul")])
    primero = c["items"][0]["id"]
    c = client.delete(f"/api/carrito/items/{primero}", headers=inv.h_cliente).json()
    assert len(c["items"]) == 1 and c["total"] == "100.00"
    c = client.delete("/api/carrito", headers=inv.h_cliente).json()
    assert c["items"] == [] and c["total"] == "0.00" and c["puede_pagar"] is False


def test_05_cantidad_igual_al_stock_es_valida(inv, mundo, client):
    stock_listo(inv, mundo, centro=3)
    r = agregar(client, inv.h_cliente, inv.v_sm_rojo, inv.centro, 3)
    assert r.status_code == 201 and r.json()["items"][0]["cantidad"] == 3 and r.json()["avisos"] == []


def test_06_una_unidad_mas_que_el_stock_se_rechaza(inv, mundo, client):
    stock_listo(inv, mundo, centro=3)
    r = agregar(client, inv.h_cliente, inv.v_sm_rojo, inv.centro, 4)
    assert r.status_code == 409 and r.json()["detail"] == MSG_STOCK
    agregar_ok(client, inv.h_cliente, inv.v_sm_rojo, inv.centro, 3)
    r = agregar(client, inv.h_cliente, inv.v_sm_rojo)  # ya tiene 3: una más supera el stock
    assert r.status_code == 409 and r.json()["detail"] == MSG_STOCK
    item = client.get("/api/carrito", headers=inv.h_cliente).json()["items"][0]
    assert client.put(f"/api/carrito/items/{item['id']}", json={"cantidad": 4}, headers=inv.h_cliente).json()["detail"] == MSG_STOCK


def test_07_sin_stock_no_se_agrega(inv, mundo, client):
    inv.stock(mundo.a.id, inv.norte.id, inv.v_sm_rojo["id"], 5)  # solo hay en Norte
    r = agregar(client, inv.h_cliente, inv.v_sm_rojo, inv.centro)
    assert r.status_code == 409 and r.json()["detail"] == MSG_STOCK
    assert agregar(client, inv.h_cliente, inv.v_sm_rojo, inv.norte).status_code == 201


def test_08_variante_inactiva_o_producto_retirado_no_se_agrega(inv, mundo, client):
    stock_listo(inv, mundo)
    client.post(f"/api/productos/{inv.camisa['id']}/desactivar", headers=inv.h_admin)
    r = agregar(client, inv.h_cliente, inv.v_sm_rojo, inv.centro)
    assert r.status_code == 422 and r.json()["detail"] == "La prenda ya no está disponible en el catálogo."
    client.post(f"/api/productos/{inv.camisa['id']}/activar", headers=inv.h_admin)
    client.put(f"/api/productos/{inv.camisa['id']}/variantes/{inv.v_sm_rojo['id']}", json={"activa": False}, headers=inv.h_admin)
    assert agregar(client, inv.h_cliente, inv.v_sm_rojo, inv.centro).status_code == 422


def test_09_hay_que_elegir_sucursal(inv, mundo, client):
    stock_listo(inv, mundo)
    r = agregar(client, inv.h_cliente, inv.v_sm_rojo)
    assert r.status_code == 422 and r.json()["detail"] == "Elija la sucursal en la que desea comprar."
    assert agregar(client, inv.h_cliente, inv.v_sm_rojo, inv.centro).status_code == 201


def test_10_el_carrito_es_de_una_sola_sucursal(inv, mundo, client):
    stock_listo(inv, mundo)
    agregar_ok(client, inv.h_cliente, inv.v_sm_rojo, inv.centro)
    r = agregar(client, inv.h_cliente, inv.var[("M", "Azul")], inv.norte)
    assert r.status_code == 409 and r.json()["detail"] == "Su carrito es para la sucursal Centro. Cambie de sucursal en el carrito o vacíelo."


def test_11_cambiar_de_sucursal_marca_las_prendas_sin_stock(inv, mundo, client):
    stock_listo(inv, mundo)
    agregar_ok(client, inv.h_cliente, inv.v_sm_rojo, inv.centro, 5)
    # Norte tiene 10 y alcanzaría; se ajusta su stock para que no alcance
    client.post("/api/inventario/sucursal/movimientos", json={"variante_id": inv.v_sm_rojo["id"], "tipo": "AJUSTE_SALIDA", "cantidad": 8, "nota": "Conteo"}, headers=inv.h_enc_norte)
    c = client.put("/api/carrito/sucursal", json={"sucursal_id": inv.norte.id}, headers=inv.h_cliente).json()
    assert c["sucursal"] == "Norte" and c["items"][0]["estado"] == "SIN_STOCK" and c["items"][0]["disponible"] == 2
    assert c["puede_pagar"] is False and "en Norte hay 2 disponible(s) y tiene 5 en el carrito" in c["avisos"][0]
    assert client.put("/api/carrito/sucursal", json={"sucursal_id": 99999}, headers=inv.h_cliente).status_code == 404


def test_12_el_stock_se_revisa_al_mostrar_el_carrito(inv, mundo, client):
    stock_listo(inv, mundo)
    agregar_ok(client, inv.h_cliente, inv.v_sm_rojo, inv.centro, 4)
    client.post("/api/inventario/sucursal/movimientos", json={"variante_id": inv.v_sm_rojo["id"], "tipo": "AJUSTE_SALIDA", "cantidad": 8, "nota": "Merma"}, headers=inv.h_enc_centro)
    c = client.get("/api/carrito", headers=inv.h_cliente).json()
    assert c["items"][0]["estado"] == "SIN_STOCK" and c["puede_pagar"] is False
    client.post(f"/api/productos/{inv.camisa['id']}/desactivar", headers=inv.h_admin)
    c = client.get("/api/carrito", headers=inv.h_cliente).json()
    assert c["items"][0]["estado"] == "RETIRADA" and "ya no está disponible en el catálogo" in c["avisos"][0]


def test_13_el_precio_incluye_la_promocion_vigente(inv, mundo, client):
    stock_listo(inv, mundo)
    hoy = date.today()
    r = client.post("/api/promociones", json={"nombre": "Liquidación", "tipo_descuento": "PORCENTAJE", "valor": "20",
                                              "inicia": (hoy - timedelta(days=1)).isoformat(), "termina": (hoy + timedelta(days=5)).isoformat()}, headers=inv.h_admin)
    assert r.status_code == 201
    c = agregar_ok(client, inv.h_cliente, inv.v_sm_rojo, inv.centro, 2)
    assert (c["subtotal"], c["descuento"], c["total"]) == ("200.00", "40.00", "160.00")
    assert (c["items"][0]["precio"], c["items"][0]["precio_final"]) == ("100.00", "80.00")


def test_14_cada_cliente_tiene_su_carrito(inv, mundo, datos, client):
    stock_listo(inv, mundo)
    agregar_ok(client, inv.h_cliente, inv.v_sm_rojo, inv.centro, 2)
    datos.usuario(mundo.a, "Cliente", email="otro@a.com")
    h_otro = entrar(client, mundo.a, "otro@a.com")
    assert client.get("/api/carrito", headers=h_otro).json()["items"] == []
    item = client.get("/api/carrito", headers=inv.h_cliente).json()["items"][0]
    assert client.put(f"/api/carrito/items/{item['id']}", json={"cantidad": 1}, headers=h_otro).status_code == 404
    assert client.delete(f"/api/carrito/items/{item['id']}", headers=h_otro).status_code == 404
    assert client.get("/api/carrito", headers=inv.h_cliente).json()["total_unidades"] == 2


def test_15_aislamiento_entre_empresas(inv, mundo, tienda_b, datos, client):
    from tests.catalogo_util import por_variante, talla_id
    stock_listo(inv, mundo)
    agregar_ok(client, inv.h_cliente, inv.v_sm_rojo, inv.centro)
    centro_b = datos.sucursal(mundo.b, "Centro B")
    camisa_b = tienda_b.producto("Camisa B", tienda_b.camisas["id"], tienda_b.col["id"], [talla_id(tienda_b.alfa, "S")], [tienda_b.rojo["id"]])
    v_b = por_variante(camisa_b)[("S", "Rojo")]
    tienda_b.stock(mundo.b.id, centro_b.id, v_b["id"], 5)
    h_b = cabecera_cliente(datos, mundo.b)
    assert client.get("/api/carrito", headers=h_b).json()["items"] == []  # el cliente de B no ve el carrito del de A
    assert agregar(client, h_b, inv.v_sm_rojo, centro_b).status_code == 422  # ni agrega prendas de A
    assert agregar(client, h_b, v_b, inv.centro).status_code == 404  # ni usa sucursales de A
    assert agregar(client, h_b, v_b, centro_b).status_code == 201
    assert client.get("/api/carrito", headers=inv.h_cliente).json()["total_unidades"] == 1


def test_16_solo_el_cliente_usa_el_carrito(inv, client):
    for h in (inv.h_enc_centro, inv.h_cajero, inv.h_admin, inv.h_prov):
        assert client.get("/api/carrito", headers=h).status_code == 403
    assert client.get("/api/carrito").status_code == 401

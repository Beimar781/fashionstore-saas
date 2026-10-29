"""CU-29 Registrar venta presencial — venta de caja y venta desde una reserva, sucursal del cajero y aislamiento entre empresas."""
from datetime import date, timedelta

from tests.caja_util import cobrar, stock_listo, venta, venta_ok
from tests.catalogo_util import cabecera_cliente, entrar
from tests.compras_util import existencias
from tests.reservas_util import reserva_ok, vencer

MSG_CODIGO_RESERVA = "El código de reserva no existe o ya ha expirado su vigencia."


def _reservada(inv, mundo, client, estado="PREPARADA", cantidades=(2, 1)):
    """Una reserva del cliente en Centro con dos prendas, en el estado pedido (PREPARADA o EN_PROBADOR)."""
    res = reserva_ok(client, inv.h_cliente, inv.centro, (inv.v_sm_rojo, cantidades[0]), (inv.var[("M", "Azul")], cantidades[1]))
    if estado in ("PREPARADA", "EN_PROBADOR"):
        client.post(f"/api/reservas-sucursal/{res['id']}/preparar", headers=inv.h_enc_centro)
    if estado == "EN_PROBADOR":
        client.post(f"/api/atencion-reservas/{res['id']}/atender", headers=inv.h_enc_centro)
    return res


def test_01_la_venta_queda_pendiente_de_cobro_sin_tocar_el_stock(inv, mundo, client):
    stock_listo(inv, mundo)
    p = venta_ok(client, inv.h_cajero, (inv.v_sm_rojo, 2), (inv.var[("M", "Azul")], 1))
    assert (p["estado"], p["canal"], p["tipo_entrega"], p["sucursal"], p["total"], p["total_unidades"]) == ("PENDIENTE_PAGO", "PRESENCIAL", "EN_TIENDA", "Centro", "300.00", 3)
    assert (p["nit_ci"], p["razon_social"], p["cliente"], p["vendedor"], p["comprobante_numero"]) == ("0", "Sin nombre", None, "Cajero Prueba", None)
    assert existencias(client, inv.h_enc_centro, inv.v_sm_rojo)["disponible"] == 10  # el stock se descuenta al cobrar (CU-30)


def test_02_el_precio_incluye_la_promocion_y_los_datos_de_facturacion(inv, mundo, client):
    stock_listo(inv, mundo)
    hoy = date.today()
    client.post("/api/promociones", json={"nombre": "Liquidación", "tipo_descuento": "PORCENTAJE", "valor": "20",
                                          "inicia": (hoy - timedelta(days=1)).isoformat(), "termina": (hoy + timedelta(days=5)).isoformat()}, headers=inv.h_admin)
    p = venta_ok(client, inv.h_cajero, (inv.v_sm_rojo, 2), nit_ci="7654321", razon_social="Mi Empresa SRL")
    assert (p["subtotal"], p["descuento"], p["total"], p["iva_incluido"]) == ("200.00", "40.00", "160.00", "18.41")
    assert (p["nit_ci"], p["razon_social"], p["items"][0]["precio_final"]) == ("7654321", "Mi Empresa SRL", "80.00")


def test_03_sin_prendas_una_prenda_repetida_y_cantidades(inv, mundo, client):
    stock_listo(inv, mundo)
    r = venta(client, inv.h_cajero)
    assert r.status_code == 422 and r.json()["detail"] == "Agregue al menos una prenda a la venta."
    assert venta(client, inv.h_cajero, (inv.v_sm_rojo, 0)).status_code == 422
    p = venta_ok(client, inv.h_cajero, (inv.v_sm_rojo, 1), (inv.v_sm_rojo, 2))
    assert len(p["items"]) == 1 and p["items"][0]["cantidad"] == 3  # la prenda repetida se suma


def test_04_solo_cuenta_el_stock_de_la_sucursal_del_cajero(inv, mundo, client):
    stock_listo(inv, mundo, centro=2, norte=50)
    r = venta(client, inv.h_cajero, (inv.v_sm_rojo, 3))
    assert r.status_code == 409
    assert r.json()["detail"] == "No hay stock suficiente en Centro para: Camisa Oxford (S, Rojo): solicitadas 3, disponibles 2."
    assert venta(client, inv.h_enc_norte, (inv.v_sm_rojo, 3)).status_code == 201  # en Norte sí alcanza


def test_05_prendas_retiradas_del_catalogo(inv, mundo, client):
    stock_listo(inv, mundo)
    client.post(f"/api/productos/{inv.camisa['id']}/desactivar", headers=inv.h_admin)
    r = venta(client, inv.h_cajero, (inv.v_sm_rojo, 1))
    assert r.status_code == 422 and r.json()["detail"] == "Una o más prendas ya no están disponibles en el catálogo."


def test_06_venta_desde_una_reserva_preparada(inv, mundo, client):
    stock_listo(inv, mundo)
    res = _reservada(inv, mundo, client)
    r = client.get(f"/api/caja/reservas/{res['codigo'].lower()}", headers=inv.h_cajero)
    assert r.status_code == 200 and r.json()["id"] == res["id"] and r.json()["estado"] == "PREPARADA"
    p = venta_ok(client, inv.h_cajero, reserva_codigo=res["codigo"])  # sin elegir prendas: se lleva todo lo reservado
    assert (p["reserva_id"], p["total"], p["total_unidades"], p["cliente"], p["estado"]) == (res["id"], "300.00", 3, "Cliente Prueba", "PENDIENTE_PAGO")
    assert existencias(client, inv.h_enc_centro, inv.v_sm_rojo)["reservada"] == 2  # sigue apartado hasta cobrar


def test_07_venta_desde_una_reserva_en_probador_con_menos_prendas(inv, mundo, client):
    stock_listo(inv, mundo)
    res = _reservada(inv, mundo, client, "EN_PROBADOR")
    p = venta_ok(client, inv.h_cajero, (inv.v_sm_rojo, 1), reserva_codigo=res["codigo"])  # el cliente se lleva solo 1 de las 2 camisas
    assert (p["total"], p["total_unidades"]) == ("100.00", 1)
    r = venta(client, inv.h_cajero, (inv.v_sm_rojo, 3), reserva_codigo=res["codigo"])
    assert r.status_code == 422 and r.json()["detail"] == "La venta incluye prendas o cantidades que no están en la reserva."
    r = venta(client, inv.h_cajero, (inv.var[("S", "Azul")], 1), reserva_codigo=res["codigo"])
    assert r.status_code == 422  # una prenda que no estaba en la reserva


def test_08_una_reserva_solo_tiene_una_venta_abierta(inv, mundo, client):
    stock_listo(inv, mundo)
    res = _reservada(inv, mundo, client)
    primera = venta_ok(client, inv.h_cajero, reserva_codigo=res["codigo"])
    segunda = venta_ok(client, inv.h_cajero, (inv.v_sm_rojo, 1), reserva_codigo=res["codigo"])
    assert client.get(f"/api/caja/ventas/{primera['id']}", headers=inv.h_cajero).json()["estado"] == "CANCELADO"
    assert [v["id"] for v in client.get("/api/caja/ventas/pendientes", headers=inv.h_cajero).json()] == [segunda["id"]]


def test_09_codigos_de_reserva_que_no_sirven(inv, mundo, client, db):
    stock_listo(inv, mundo)
    r = client.get("/api/caja/reservas/RSV-NOEXISTE", headers=inv.h_cajero)
    assert r.status_code == 404 and r.json()["detail"] == MSG_CODIGO_RESERVA
    pendiente = _reservada(inv, mundo, client, "PENDIENTE")  # una reserva sin preparar todavía no se cobra
    assert client.get(f"/api/caja/reservas/{pendiente['codigo']}", headers=inv.h_cajero).status_code == 404
    otra = _reservada(inv, mundo, client)  # preparada pero en Centro: el cajero de Norte no la cobra
    r = client.get(f"/api/caja/reservas/{otra['codigo']}", headers=inv.h_enc_norte)
    assert r.status_code == 409 and r.json()["detail"] == "La reserva corresponde a otra sucursal."
    vencer(db, otra["id"])
    assert client.get(f"/api/caja/reservas/{otra['codigo']}", headers=inv.h_cajero).json()["detail"] == MSG_CODIGO_RESERVA
    cancelada = _reservada(inv, mundo, client)
    client.post(f"/api/reservas/{cancelada['id']}/cancelar", json={}, headers=inv.h_cliente)
    assert venta(client, inv.h_cajero, reserva_codigo=cancelada["codigo"]).status_code == 404


def test_10_venta_a_un_cliente_registrado(inv, mundo, client):
    stock_listo(inv, mundo)
    p = venta_ok(client, inv.h_cajero, (inv.v_sm_rojo, 1), cliente_email="CLIENTE@tienda.com")
    assert p["cliente"] == "Cliente Prueba"
    r = venta(client, inv.h_cajero, (inv.v_sm_rojo, 1), cliente_email="nadie@tienda.com")
    assert r.status_code == 404 and r.json()["detail"] == "No hay un cliente registrado con ese correo."
    r = venta(client, inv.h_cajero, (inv.v_sm_rojo, 1), cliente_email="enc_centro@a.com")  # un empleado no es cliente
    assert r.status_code == 404


def test_11_consultar_y_anular_la_venta_en_curso(inv, mundo, client):
    stock_listo(inv, mundo)
    p = venta_ok(client, inv.h_cajero, (inv.v_sm_rojo, 1))
    assert client.get(f"/api/caja/ventas/{p['id']}", headers=inv.h_cajero).json()["codigo"] == p["codigo"]
    anulada = client.delete(f"/api/caja/ventas/{p['id']}", headers=inv.h_cajero)
    assert anulada.status_code == 200 and anulada.json()["estado"] == "CANCELADO" and anulada.json()["pagos"] == []
    assert client.delete(f"/api/caja/ventas/{p['id']}", headers=inv.h_cajero).json()["detail"] == "La venta ya está anulada."
    assert cobrar(client, inv.h_cajero, p["id"], recibido=100).status_code == 409  # una venta anulada no se cobra
    cobrada = venta_ok(client, inv.h_cajero, (inv.v_sm_rojo, 1))
    cobrar(client, inv.h_cajero, cobrada["id"], recibido=100)
    r = client.delete(f"/api/caja/ventas/{cobrada['id']}", headers=inv.h_cajero)
    assert r.status_code == 409 and r.json()["detail"] == "Una venta ya cobrada no se puede anular; registre una devolución."


def test_12_un_cajero_solo_vende_en_su_sucursal(inv, mundo, client):
    stock_listo(inv, mundo)
    p = venta_ok(client, inv.h_cajero, (inv.v_sm_rojo, 1))  # venta de Centro
    assert client.get(f"/api/caja/ventas/{p['id']}", headers=inv.h_enc_norte).status_code == 404
    assert client.delete(f"/api/caja/ventas/{p['id']}", headers=inv.h_enc_norte).status_code == 404
    assert cobrar(client, inv.h_enc_norte, p["id"], recibido=100).status_code == 404
    assert client.get("/api/caja/ventas/pendientes", headers=inv.h_enc_norte).json() == []
    assert [v["id"] for v in client.get("/api/caja/ventas/pendientes", headers=inv.h_cajero).json()] == [p["id"]]


def test_13_un_empleado_sin_sucursal_no_vende(inv, mundo, datos, client):
    stock_listo(inv, mundo)
    datos.usuario(mundo.a, "Cajero", email="sin@a.com")
    h = entrar(client, mundo.a, "sin@a.com")
    r = venta(client, h, (inv.v_sm_rojo, 1))
    assert r.status_code == 403 and r.json()["detail"] == "Su usuario no tiene una sucursal asignada."  # RN10


def test_14_aislamiento_entre_empresas(inv, mundo, tienda_b, datos, client):
    from tests.catalogo_util import por_variante, talla_id
    stock_listo(inv, mundo)
    p = venta_ok(client, inv.h_cajero, (inv.v_sm_rojo, 1))
    res = _reservada(inv, mundo, client)
    centro_b = datos.sucursal(mundo.b, "Centro B")
    datos.usuario(mundo.b, "Cajero", email="cajero@b.com", sucursal=centro_b)
    h_b = entrar(client, mundo.b, "cajero@b.com")
    camisa_b = tienda_b.producto("Camisa B", tienda_b.camisas["id"], tienda_b.col["id"], [talla_id(tienda_b.alfa, "S")], [tienda_b.rojo["id"]])
    v_b = por_variante(camisa_b)[("S", "Rojo")]
    tienda_b.stock(mundo.b.id, centro_b.id, v_b["id"], 5)
    assert venta(client, h_b, (inv.v_sm_rojo, 1)).status_code == 422  # prenda de otra empresa
    assert client.get(f"/api/caja/ventas/{p['id']}", headers=h_b).status_code == 404
    assert client.get(f"/api/caja/reservas/{res['codigo']}", headers=h_b).json()["detail"] == MSG_CODIGO_RESERVA
    assert venta(client, h_b, reserva_codigo=res["codigo"]).status_code == 404
    assert venta(client, h_b, (v_b, 1), cliente_email="cliente@tienda.com").status_code == 404  # el cliente de A no existe en B
    assert venta(client, h_b, (v_b, 1)).status_code == 201
    assert client.get("/api/caja/ventas/pendientes", headers=inv.h_cajero).json()[0]["id"] == p["id"]
    cabecera_cliente(datos, mundo.b)


def test_15_solo_la_caja_registra_ventas(inv, mundo, client):
    stock_listo(inv, mundo)
    for h in (inv.h_cliente, inv.h_admin, inv.h_prov):
        assert venta(client, h, (inv.v_sm_rojo, 1)).status_code == 403
        assert client.get("/api/caja/ventas/pendientes", headers=h).status_code == 403
    assert client.post("/api/caja/ventas", json={}).status_code == 401

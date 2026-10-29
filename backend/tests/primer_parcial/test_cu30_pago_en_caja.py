"""CU-30 Procesar pago y emitir comprobante — pasos de la ficha (5.2.1), cobro con tarjeta, venta sin stock a mitad del cobro y aislamiento."""
from sqlalchemy import select

from app.core.config import get_settings
from app.primer_parcial.ventas.models import Pago
from tests.caja_util import cobrar, stock_listo, vender, venta_ok
from tests.catalogo_util import cabecera_cliente, entrar
from tests.compras_util import MSG_RECHAZO, SIN_FONDOS, VISA_OK, existencias, iniciar, tarjeta
from tests.reservas_util import reserva_ok

MSG_FALLA = "Falla de red con el servicio de impuestos, se generará un comprobante interno temporal."


def _agotar(client, inv, variante, cantidad):
    """Otro empleado da de baja prendas de Centro mientras la venta está a medio cobrar."""
    r = client.post("/api/inventario/sucursal/movimientos", json={"variante_id": variante["id"], "tipo": "AJUSTE_SALIDA", "cantidad": cantidad, "nota": "Merma"}, headers=inv.h_enc_centro)
    assert r.status_code == 201, r.text


def test_01_en_efectivo_el_sistema_calcula_el_cambio(inv, mundo, client):
    stock_listo(inv, mundo)
    p = venta_ok(client, inv.h_cajero, (inv.v_sm_rojo, 2))  # total 200
    r = cobrar(client, inv.h_cajero, p["id"], "EFECTIVO", 250)
    assert r.status_code == 200
    c = r.json()
    assert (c["cambio"], c["pago"]["metodo"], c["pago"]["estado"], c["pago"]["monto_recibido"], c["pago"]["cambio"], c["pago"]["proveedor"]) == (
        "50.00", "EFECTIVO", "APROBADO", "250.00", "50.00", "CAJA")


def test_02_confirmar_el_cobro_descuenta_el_inventario_y_deja_la_bitacora(inv, mundo, client):
    stock_listo(inv, mundo)
    c = vender(client, inv.h_cajero, (inv.v_sm_rojo, 3))
    assert (c["pedido"]["estado"], c["pedido"]["comprobante_numero"]) == ("PAGADO", f"CMP-{inv.centro.id:03d}-000001")
    f = existencias(client, inv.h_enc_centro, inv.v_sm_rojo)
    assert (f["disponible"], f["vendida"]) == (7, 3)
    assert existencias(client, inv.h_enc_norte, inv.v_sm_rojo)["disponible"] == 10  # solo la sucursal del cajero
    m = client.get("/api/inventario/movimientos", params={"tipo": "VENTA"}, headers=inv.h_enc_centro).json()["items"][0]
    assert (m["cantidad"], m["referencia_tipo"], m["referencia_id"], m["usuario"]) == (3, "VENTA", c["pedido"]["id"], "Cajero Prueba")


def test_03_monto_recibido_invalido_o_venta_ya_cobrada(inv, mundo, client):
    stock_listo(inv, mundo)
    p = venta_ok(client, inv.h_cajero, (inv.v_sm_rojo, 1))
    r = cobrar(client, inv.h_cajero, p["id"], "EFECTIVO", 99)
    assert r.status_code == 422 and r.json()["detail"] == "El monto recibido es menor al total de la venta."
    r = cobrar(client, inv.h_cajero, p["id"], "EFECTIVO")
    assert r.status_code == 422 and r.json()["detail"] == "Ingrese el monto recibido."
    assert existencias(client, inv.h_enc_centro, inv.v_sm_rojo)["vendida"] == 0  # los errores no descuentan nada
    assert cobrar(client, inv.h_cajero, p["id"], "EFECTIVO", 100).status_code == 200
    r = cobrar(client, inv.h_cajero, p["id"], "EFECTIVO", 100)  # no se cobra dos veces
    assert r.status_code == 409 and r.json()["detail"] == "La venta no está pendiente de cobro."
    assert existencias(client, inv.h_enc_centro, inv.v_sm_rojo)["vendida"] == 1


def test_04_en_tienda_solo_efectivo_o_tarjeta(inv, mundo, client):
    stock_listo(inv, mundo)
    p = venta_ok(client, inv.h_cajero, (inv.v_sm_rojo, 1))
    assert cobrar(client, inv.h_cajero, p["id"], "QR", 100).status_code == 422  # el QR no es un medio de pago de la tienda
    assert client.get(f"/api/caja/ventas/{p['id']}", headers=inv.h_cajero).json()["estado"] == "PENDIENTE_PAGO"


def test_05_cobro_con_tarjeta_usa_la_pasarela_de_cu32(inv, mundo, client, db):
    stock_listo(inv, mundo)
    p = venta_ok(client, inv.h_cajero, (inv.v_sm_rojo, 2))
    ini = iniciar(client, inv.h_cajero, p["id"])
    assert ini.status_code == 201 and ini.json()["modo"] == "simulado" and ini.json()["monto"] == "200.00"
    r = client.post(f"/api/pagos/{ini.json()['pago_id']}/confirmar", json={"tarjeta": tarjeta()}, headers=inv.h_cajero)
    assert r.status_code == 200 and r.json()["aprobado"] is True
    ped = r.json()["pedido"]
    assert (ped["estado"], ped["canal"], ped["comprobante_numero"]) == ("PAGADO", "PRESENCIAL", f"CMP-{inv.centro.id:03d}-000001")
    assert (r.json()["pago"]["tarjeta_marca"], r.json()["pago"]["tarjeta_ultimos4"]) == ("Visa", "4242")
    assert existencias(client, inv.h_enc_centro, inv.v_sm_rojo)["vendida"] == 2
    m = client.get("/api/inventario/movimientos", params={"tipo": "VENTA"}, headers=inv.h_enc_centro).json()["items"][0]
    assert m["referencia_tipo"] == "VENTA"  # las ventas de caja se registran con referencia VENTA
    pago = db.scalars(select(Pago).where(Pago.pedido_id == p["id"])).one()
    assert (pago.metodo, pago.proveedor, pago.usuario_id is not None) == ("TARJETA", "SIMULADO", True)  # lo registra el cajero que cobra


def test_06_tarjeta_rechazada_en_caja(inv, mundo, client):
    stock_listo(inv, mundo)
    p = venta_ok(client, inv.h_cajero, (inv.v_sm_rojo, 1))
    pago_id = iniciar(client, inv.h_cajero, p["id"]).json()["pago_id"]
    r = client.post(f"/api/pagos/{pago_id}/confirmar", json={"tarjeta": tarjeta(SIN_FONDOS)}, headers=inv.h_cajero)
    assert r.status_code == 402 and r.json()["detail"] == MSG_RECHAZO and r.json()["motivo"] == "Transacción denegada por su banco"
    assert existencias(client, inv.h_enc_centro, inv.v_sm_rojo)["vendida"] == 0
    assert client.get(f"/api/caja/ventas/{p['id']}", headers=inv.h_cajero).json()["estado"] == "PENDIENTE_PAGO"  # se puede cobrar de otra forma
    assert cobrar(client, inv.h_cajero, p["id"], "EFECTIVO", 100).status_code == 200


def test_07_el_comprobante_se_descarga_en_pdf(inv, mundo, client):
    stock_listo(inv, mundo)
    c = vender(client, inv.h_cajero, (inv.v_sm_rojo, 2), metodo="EFECTIVO", recibido=250)
    r = client.get(f"/api/caja/ventas/{c['pedido']['id']}/comprobante", headers=inv.h_cajero)
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf" and r.content.startswith(b"%PDF") and len(r.content) > 1500
    assert c["pedido"]["comprobante_tipo"] == "FACTURA" and c["aviso"] is None
    p = venta_ok(client, inv.h_cajero, (inv.v_sm_rojo, 1))  # sin cobrar no hay comprobante
    r = client.get(f"/api/caja/ventas/{p['id']}/comprobante", headers=inv.h_cajero)
    assert r.status_code == 409 and r.json()["detail"] == "Solo hay comprobante de ventas cobradas."


def test_08_falla_del_servicio_de_impuestos_genera_un_comprobante_interno_temporal(inv, mundo, client, monkeypatch):
    stock_listo(inv, mundo)
    monkeypatch.setattr(get_settings(), "impuestos_simular_falla", True)
    c = vender(client, inv.h_cajero, (inv.v_sm_rojo, 1))
    assert c["aviso"] == MSG_FALLA == c["pedido"]["comprobante_aviso"]
    assert (c["pedido"]["estado"], c["pedido"]["comprobante_tipo"]) == ("PAGADO", "INTERNO_TEMPORAL")  # la venta no se pierde
    assert existencias(client, inv.h_enc_centro, inv.v_sm_rojo)["vendida"] == 1
    r = client.get(f"/api/caja/ventas/{c['pedido']['id']}/comprobante", headers=inv.h_cajero)
    assert r.status_code == 200 and r.content.startswith(b"%PDF")


def test_09_si_el_stock_se_agota_a_mitad_del_cobro_en_efectivo_no_se_cobra(inv, mundo, client):
    stock_listo(inv, mundo)
    p = venta_ok(client, inv.h_cajero, (inv.v_sm_rojo, 5))
    _agotar(client, inv, inv.v_sm_rojo, 8)  # quedan 2
    r = cobrar(client, inv.h_cajero, p["id"], "EFECTIVO", 500)
    assert r.status_code == 409
    assert r.json()["detail"] == ("Algunas prendas se agotaron mientras pagaba: Camisa Oxford (S, Rojo): quedan 2, necesita 5. "
                                  "No se realizó ningún cobro. Anule la venta y regístrela de nuevo con lo disponible.")
    f = existencias(client, inv.h_enc_centro, inv.v_sm_rojo)
    assert (f["disponible"], f["vendida"]) == (2, 0)  # ningún descuento a medias
    v = client.get(f"/api/caja/ventas/{p['id']}", headers=inv.h_cajero).json()
    assert v["estado"] == "PENDIENTE_PAGO" and v["pagos"] == [] and v["comprobante_numero"] is None  # sin cobro registrado ni comprobante


def test_10_si_el_stock_se_agota_a_mitad_del_cobro_con_tarjeta_se_cancela_el_pago(inv, mundo, client):
    stock_listo(inv, mundo)
    p = venta_ok(client, inv.h_cajero, (inv.v_sm_rojo, 5))
    pago_id = iniciar(client, inv.h_cajero, p["id"]).json()["pago_id"]  # la tarjeta se está leyendo…
    _agotar(client, inv, inv.v_sm_rojo, 8)  # …y se agota el stock
    r = client.post(f"/api/pagos/{pago_id}/confirmar", json={"tarjeta": tarjeta()}, headers=inv.h_cajero)
    assert r.status_code == 409 and "se agotaron mientras pagaba" in r.json()["detail"] and "No se realizó ningún cobro" in r.json()["detail"]
    est = client.get(f"/api/pagos/{pago_id}", headers=inv.h_cajero).json()
    assert (est["pago"]["estado"], est["pedido"]["estado"], est["aprobado"]) == ("CANCELADO", "CANCELADO", False)
    assert existencias(client, inv.h_enc_centro, inv.v_sm_rojo)["vendida"] == 0


def test_11_venta_desde_una_reserva_pasa_de_reservado_a_vendido(inv, mundo, client):
    stock_listo(inv, mundo)
    res = reserva_ok(client, inv.h_cliente, inv.centro, (inv.v_sm_rojo, 2), (inv.var[("M", "Azul")], 1))
    client.post(f"/api/reservas-sucursal/{res['id']}/preparar", headers=inv.h_enc_centro)
    antes = existencias(client, inv.h_enc_centro, inv.v_sm_rojo)
    assert (antes["disponible"], antes["reservada"], antes["vendida"]) == (8, 2, 0)
    c = vender(client, inv.h_cajero, (inv.v_sm_rojo, 1), reserva_codigo=res["codigo"])  # el cliente solo se lleva 1 de las 2 camisas y deja la azul
    assert c["pedido"]["estado"] == "PAGADO" and c["pedido"]["total_unidades"] == 1
    rojo = existencias(client, inv.h_enc_centro, inv.v_sm_rojo)
    assert (rojo["disponible"], rojo["reservada"], rojo["vendida"]) == (9, 0, 1)  # 1 vendida; la otra volvió a disponible
    azul = existencias(client, inv.h_enc_centro, inv.var[("M", "Azul")])
    assert (azul["disponible"], azul["reservada"], azul["vendida"]) == (10, 0, 0)  # lo que no se llevó vuelve a disponible
    r = client.get(f"/api/reservas/{res['id']}", headers=inv.h_cliente).json()
    assert r["estado"] == "COMPLETADA" and {i["estado"] for i in r["items"]} == {"VENDIDO", "LIBERADO"}
    tipos = {m["tipo"] for m in client.get("/api/inventario/movimientos", headers=inv.h_enc_centro).json()["items"]}
    assert {"VENTA_RESERVA", "LIBERA_RESERVA"} <= tipos
    assert client.get(f"/api/caja/reservas/{res['codigo']}", headers=inv.h_cajero).status_code == 404  # ya no se puede cobrar de nuevo


def test_12_la_venta_aparece_en_el_historial_del_cliente(inv, mundo, client):
    stock_listo(inv, mundo)
    res = reserva_ok(client, inv.h_cliente, inv.centro, (inv.v_sm_rojo, 1))
    client.post(f"/api/reservas-sucursal/{res['id']}/preparar", headers=inv.h_enc_centro)
    c = vender(client, inv.h_cajero, reserva_codigo=res["codigo"])
    vender(client, inv.h_cajero, (inv.v_sm_rojo, 1))  # venta de mostrador sin cliente: no aparece
    compras = client.get("/api/compras", headers=inv.h_cliente).json()["compras"]
    assert [(x["id"], x["canal"], x["estado"]) for x in compras] == [(c["pedido"]["id"], "PRESENCIAL", "PAGADO")]
    pdf = client.get(f"/api/compras/{c['pedido']['id']}/comprobante", headers=inv.h_cliente)
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")  # el cliente también descarga su comprobante


def test_13_una_reserva_vencida_a_mitad_del_cobro_no_se_cobra(inv, mundo, client, db):
    from tests.reservas_util import vencer
    stock_listo(inv, mundo)
    res = reserva_ok(client, inv.h_cliente, inv.centro, (inv.v_sm_rojo, 2))
    client.post(f"/api/reservas-sucursal/{res['id']}/preparar", headers=inv.h_enc_centro)
    p = venta_ok(client, inv.h_cajero, reserva_codigo=res["codigo"])
    vencer(db, res["id"])
    r = cobrar(client, inv.h_cajero, p["id"], "EFECTIVO", 200)
    assert r.status_code == 409 and r.json()["detail"] == "La reserva ya no está vigente. No se realizó ningún cobro."
    assert existencias(client, inv.h_enc_centro, inv.v_sm_rojo)["vendida"] == 0


def test_14_comprobantes_numerados_por_sucursal(inv, mundo, client):
    stock_listo(inv, mundo)
    numeros = [vender(client, inv.h_cajero, (inv.v_sm_rojo, 1))["pedido"]["comprobante_numero"] for _ in range(2)]
    norte = vender(client, inv.h_enc_norte, (inv.v_sm_rojo, 1))["pedido"]["comprobante_numero"]
    assert numeros == [f"CMP-{inv.centro.id:03d}-000001", f"CMP-{inv.centro.id:03d}-000002"] and norte == f"CMP-{inv.norte.id:03d}-000001"


def test_15_aislamiento_y_roles(inv, mundo, tienda_b, datos, client):
    stock_listo(inv, mundo)
    p = venta_ok(client, inv.h_cajero, (inv.v_sm_rojo, 1))
    datos.usuario(mundo.b, "Cajero", email="cajero@b.com", sucursal=datos.sucursal(mundo.b, "Sucursal B"))
    h_b = entrar(client, mundo.b, "cajero@b.com")
    assert cobrar(client, h_b, p["id"], "EFECTIVO", 100).status_code == 404
    assert client.get(f"/api/caja/ventas/{p['id']}/comprobante", headers=h_b).status_code == 404
    assert iniciar(client, h_b, p["id"]).status_code == 404
    for h in (inv.h_cliente, inv.h_admin, inv.h_prov):
        assert cobrar(client, h, p["id"], "EFECTIVO", 100).status_code == 403
    cabecera_cliente(datos, mundo.b)
    assert existencias(client, inv.h_enc_centro, inv.v_sm_rojo)["vendida"] == 0


def test_16_una_compra_digital_no_se_cobra_en_caja(inv, mundo, client):
    from tests.compras_util import agregar_ok, checkout_ok
    stock_listo(inv, mundo)
    agregar_ok(client, inv.h_cliente, inv.v_sm_rojo, inv.centro, 1)
    digital = checkout_ok(client, inv.h_cliente)
    assert cobrar(client, inv.h_cajero, digital["id"], "EFECTIVO", 100).status_code == 404
    assert client.get(f"/api/caja/ventas/{digital['id']}", headers=inv.h_cajero).status_code == 404

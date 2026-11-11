"""Punto K-8: la venta de caja que queda por pagar a nombre de un cliente se ve en su historial y él puede pagarla con tarjeta sin descontar el stock dos veces."""
from tests.caja_util import cobrar, stock_listo, venta_ok
from tests.compras_util import existencias, iniciar, pagar, tarjeta


def _por_pagar(client, inv, mundo):
    stock_listo(inv, mundo)
    return venta_ok(client, inv.h_cajero, (inv.v_sm_rojo, 2), cliente_email="cliente@tienda.com")


def test_01_la_venta_sin_cobrar_sale_por_pagar_en_su_historial_y_no_toca_el_stock(inv, mundo, client):
    p = _por_pagar(client, inv, mundo)
    antes = 10  # stock_listo deja 10 en Centro
    compras = client.get("/api/compras", headers=inv.h_cliente).json()["compras"]
    assert [(c["id"], c["canal"], c["estado"], c["comprobante_numero"]) for c in compras] == [(p["id"], "PRESENCIAL", "PENDIENTE_PAGO", None)]
    assert existencias(client, inv.h_enc_centro, inv.v_sm_rojo)["disponible"] == antes


def test_02_el_cliente_la_paga_con_tarjeta_y_el_stock_baja_una_sola_vez(inv, mundo, client):
    p = _por_pagar(client, inv, mundo)
    antes = existencias(client, inv.h_enc_centro, inv.v_sm_rojo)["disponible"]
    r = pagar(client, inv.h_cliente, p["id"])
    assert r.status_code == 200 and r.json()["aprobado"], r.text
    pedido = r.json()["pedido"]
    assert pedido["estado"] == "PAGADO" and pedido["comprobante_numero"].startswith(f"CMP-{inv.centro.id:03d}-")
    assert existencias(client, inv.h_enc_centro, inv.v_sm_rojo)["disponible"] == antes - 2
    assert cobrar(client, inv.h_cajero, p["id"], recibido=p["total"]).status_code == 409  # ya está pagada: el cajero no la cobra otra vez
    assert existencias(client, inv.h_enc_centro, inv.v_sm_rojo)["disponible"] == antes - 2


def test_03_si_el_cajero_la_cobra_mientras_el_cliente_pagaba_no_se_cobra_dos_veces(inv, mundo, client):
    p = _por_pagar(client, inv, mundo)
    pago_id = iniciar(client, inv.h_cliente, p["id"]).json()["pago_id"]
    assert cobrar(client, inv.h_cajero, p["id"], recibido=p["total"]).status_code == 200
    antes = existencias(client, inv.h_enc_centro, inv.v_sm_rojo)["disponible"]
    r = client.post(f"/api/pagos/{pago_id}/confirmar", json={"tarjeta": tarjeta()}, headers=inv.h_cliente)
    assert r.status_code == 409
    assert existencias(client, inv.h_enc_centro, inv.v_sm_rojo)["disponible"] == antes


def test_04_otro_cliente_no_puede_pagarla(inv, mundo, datos, client):
    from tests.catalogo_util import entrar

    p = _por_pagar(client, inv, mundo)
    datos.usuario(mundo.a, "Cliente", email="otro@a.com")
    h = entrar(client, mundo.a, "otro@a.com")
    assert iniciar(client, h, p["id"]).status_code == 404

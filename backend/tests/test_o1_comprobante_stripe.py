"""Prompt O · el móvil descarga el comprobante PDF de una compra pagada con Stripe (EMP-A y EMP-B) y nadie ve el de otra empresa."""
import pytest

from app.primer_parcial.ventas.cu32_pago_electronico.pasarela import PasarelaStripe, obtener_pasarela
from app.primer_parcial.ventas.models import Pago
from tests.catalogo_util import cabecera_cliente, por_variante, talla_id
from tests.compras_util import agregar_ok, checkout_ok, stock_listo
from tests.stripe_falso import StripeFalso


@pytest.fixture
def stripe(client):
    """El backend con Stripe de prueba (doble en memoria): el pago se confirma como lo hace la hoja de pago del móvil."""
    falso = StripeFalso()
    client.app.dependency_overrides[obtener_pasarela] = lambda: PasarelaStripe("sk_test_falsa", "pk_test_falsa", sdk=falso)
    yield falso
    client.app.dependency_overrides.pop(obtener_pasarela, None)


def _pagar_con_stripe(client, db, falso, cabecera, pedido_id):
    i = client.post(f"/api/pagos/pedidos/{pedido_id}/iniciar", json={}, headers=cabecera)
    assert i.status_code == 201 and i.json()["modo"] == "stripe", i.text
    falso.autorizar(db.get(Pago, i.json()["pago_id"]).referencia_externa)  # la hoja de pago de Stripe confirmó la tarjeta
    r = client.post(f"/api/pagos/{i.json()['pago_id']}/confirmar", json={"tarjeta": None}, headers=cabecera)
    assert r.status_code == 200 and r.json()["aprobado"], r.text
    return r.json()["pedido"]


def _comprobante(client, cabecera, pedido):
    return client.get(f"/api/compras/{pedido['id']}/comprobante", headers=cabecera)


def test_01_la_compra_pagada_con_stripe_en_emp_a_entrega_un_pdf_valido(inv, mundo, client, db, stripe):
    stock_listo(inv, mundo)
    agregar_ok(client, inv.h_cliente, inv.v_sm_rojo, inv.centro, 1)
    pedido = _pagar_con_stripe(client, db, stripe, inv.h_cliente, checkout_ok(client, inv.h_cliente)["id"])
    r = _comprobante(client, inv.h_cliente, pedido)
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
    assert r.headers["content-disposition"] == f'attachment; filename="{pedido["comprobante_numero"]}.pdf"'
    assert r.content.startswith(b"%PDF") and len(r.content) > 1500


def test_02_la_compra_pagada_con_stripe_en_emp_b_entrega_un_pdf_valido(mundo, tienda_b, datos, client, db, stripe):
    b = tienda_b
    sucursal = datos.sucursal(mundo.b, "Centro B")
    camisa = b.producto("Camisa Andina", b.camisas["id"], b.col["id"], [talla_id(b.alfa, "S")], [b.rojo["id"]])
    variante = por_variante(camisa)[("S", "Rojo")]
    b.stock(mundo.b.id, sucursal.id, variante["id"], 10)
    h_cliente_b = cabecera_cliente(datos, mundo.b)
    agregar_ok(client, h_cliente_b, variante, sucursal, 1)
    pedido = _pagar_con_stripe(client, db, stripe, h_cliente_b, checkout_ok(client, h_cliente_b)["id"])
    r = _comprobante(client, h_cliente_b, pedido)
    assert r.status_code == 200 and r.content.startswith(b"%PDF") and len(r.content) > 1500
    assert pedido["comprobante_numero"].startswith(f"CMP-{sucursal.id:03d}-")


def test_03_un_cliente_de_otra_empresa_recibe_404_al_pedir_el_comprobante(inv, mundo, tienda_b, datos, client, db, stripe):
    stock_listo(inv, mundo)
    agregar_ok(client, inv.h_cliente, inv.v_sm_rojo, inv.centro, 1)
    pedido = _pagar_con_stripe(client, db, stripe, inv.h_cliente, checkout_ok(client, inv.h_cliente)["id"])
    h_cliente_b = cabecera_cliente(datos, mundo.b)
    r = _comprobante(client, h_cliente_b, pedido)
    assert r.status_code == 404 and not r.content.startswith(b"%PDF")

"""Cierre H · Las compras digitales pagadas (CMP-…) de la sucursal también viajan en el catálogo descargado del Encargado y del Cajero, para devolver sin conexión."""
from tests.compras_util import VISA_OK, agregar_ok, checkout_ok, pagar, stock_listo


def test_01_una_compra_digital_pagada_en_la_sucursal_aparece_en_las_ventas_recientes_del_encargado_y_del_cajero(inv, mundo, client):
    stock_listo(inv, mundo)
    agregar_ok(client, inv.h_cliente, inv.var[("M", "Azul")], inv.centro, 1)
    pedido = checkout_ok(client, inv.h_cliente)
    r = pagar(client, inv.h_cliente, pedido["id"], VISA_OK)
    comprobante = r.json()["pedido"]["comprobante_numero"]
    assert comprobante and comprobante.startswith(f"CMP-{inv.centro.id:03d}-")
    for h in (inv.h_enc_centro, inv.h_cajero):
        ventas = client.get("/api/offline/catalogo", headers=h).json()["ventas_recientes"]
        assert comprobante in [v["comprobante"] for v in ventas], "la compra digital pagada no llegó a la copia descargada"

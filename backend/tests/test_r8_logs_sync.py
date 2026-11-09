"""Prompt R · A8 (RNF10): los registros del servidor al sincronizar no llevan correos, NIT, tokens ni datos de tarjeta."""
import logging

from tests.offline_util import op_venta, sincronizar_ok, stock_listo


def test_los_logs_de_sincronizacion_no_traen_datos_personales(inv, mundo, client, caplog):
    stock_listo(inv, mundo)
    token = inv.h_cajero["Authorization"].removeprefix("Bearer ")
    op = op_venta([(inv.v_sm_rojo, 1)], 200, cliente_email="cliente@tienda.com", nit_ci="9988776", razon_social="Cliente Secreto SRL")
    with caplog.at_level(logging.DEBUG):
        r = sincronizar_ok(client, inv.h_cajero, op)[0]
    assert r["estado"] == "CONFIRMADA"
    registro = "\n".join(rec.getMessage() for rec in caplog.records)
    assert "sync operacion=" in registro  # sí queda la traza técnica: operación, tipo, estado, empresa y sucursal
    for dato in ("cliente@tienda.com", "9988776", "Cliente Secreto", token, "4242"):
        assert dato not in registro

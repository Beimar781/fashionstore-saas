"""Defensa D3 · La pantalla de conflictos del Encargado indica cuánto hay que devolver al descartar una venta de contado ya cobrada (CU-40)."""
from tests.offline_util import op_reserva, op_venta, sincronizar_ok, stock_listo


def _limitar_stock(db, inv, disponible):
    from sqlalchemy import text

    db.execute(text("UPDATE existencias SET disponible = :d WHERE variante_id = :v AND sucursal_id = :s"), {"d": disponible, "v": inv.v_sm_rojo["id"], "s": inv.centro.id})
    db.commit()


def _venta_con_precios(inv, cantidad, recibido):
    op = op_venta([(inv.v_sm_rojo, cantidad)], recibido)
    op["payload"]["items"][0]["precio_unitario"] = "100.00"  # el precio con que se registró sin conexión
    return op


def test_01_una_venta_en_conflicto_trae_el_monto_a_devolver_y_el_efectivo_recibido(inv, mundo, client, db):
    stock_listo(inv, mundo)
    _limitar_stock(db, inv, 1)
    assert sincronizar_ok(client, inv.h_cajero, _venta_con_precios(inv, 3, 350))[0]["estado"] == "EN_CONFLICTO"
    c = client.get("/api/offline/conflictos", headers=inv.h_enc_centro).json()[0]
    assert (c["monto_a_devolver"], c["efectivo_recibido"]) == ("300.00", "350.00")  # se devuelve lo vendido; el cambio ya se entregó en caja
    assert c["detalle"]["faltantes"][0]["solicitadas"] == 3 and c["detalle"]["faltantes"][0]["disponibles"] == 1


def test_02_sin_precios_registrados_o_si_no_es_una_venta_no_hay_monto(inv, mundo, client, db):
    stock_listo(inv, mundo)
    _limitar_stock(db, inv, 1)
    sincronizar_ok(client, inv.h_cajero, op_venta([(inv.v_sm_rojo, 3)], 300))  # operación antigua: sin precio_unitario
    sincronizar_ok(client, inv.h_cliente, op_reserva(inv.centro, [(inv.v_sm_rojo, 5)]))
    por_tipo = {c["tipo"]: c for c in client.get("/api/offline/conflictos", headers=inv.h_enc_centro).json()}
    assert por_tipo["VENTA_CONTADO"]["monto_a_devolver"] is None and por_tipo["VENTA_CONTADO"]["efectivo_recibido"] is None
    assert por_tipo["RESERVA"]["monto_a_devolver"] is None

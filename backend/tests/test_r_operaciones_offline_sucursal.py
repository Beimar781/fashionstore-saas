"""Prompt R · B3, B5 y B6: devolución, recepción y ajuste de inventario sin conexión, con la cola del Cajero y el Encargado."""
import uuid

from sqlalchemy import text

from tests.compras_util import existencias
from tests.devoluciones_util import envejecer_venta, venta_en_caja
from tests.offline_util import ahora_iso, sincronizar_ok, stock_listo


def _op(tipo, payload, sucursal=None):
    op = {"id": str(uuid.uuid4()), "tipo": tipo, "creada_en": ahora_iso(), "payload": payload}
    if sucursal is not None:
        op["sucursal_id"] = sucursal.id
    return op


def _stock(client, inv, variante=None):
    return existencias(client, inv.h_enc_centro, variante or inv.v_sm_rojo)["disponible"]


# ---------------- B6: ajuste de inventario por diferencia
def test_b6_el_ajuste_se_aplica_como_diferencia_y_no_pisa_lo_vendido(inv, mundo, client):
    stock_listo(inv, mundo)
    r = sincronizar_ok(client, inv.h_enc_centro, _op("AJUSTE_INVENTARIO", {"variante_id": inv.v_sm_rojo["id"], "diferencia": 4, "motivo": "CONTEO", "nota": "Conteo de cierre"}))[0]
    assert r["estado"] == "CONFIRMADA" and _stock(client, inv) == 14
    r = sincronizar_ok(client, inv.h_enc_centro, _op("AJUSTE_INVENTARIO", {"variante_id": inv.v_sm_rojo["id"], "diferencia": -3, "motivo": "MERMA"}))[0]
    assert r["estado"] == "CONFIRMADA" and _stock(client, inv) == 11


def test_b6_reenviar_el_ajuste_no_lo_aplica_dos_veces(inv, mundo, client):
    stock_listo(inv, mundo)
    op = _op("AJUSTE_INVENTARIO", {"variante_id": inv.v_sm_rojo["id"], "diferencia": 5, "motivo": "CONTEO"})
    primero, segundo = sincronizar_ok(client, inv.h_enc_centro, op)[0], sincronizar_ok(client, inv.h_enc_centro, op)[0]
    assert (primero["estado"], segundo["ya_procesada"]) == ("CONFIRMADA", True) and _stock(client, inv) == 15


def test_b6_un_ajuste_que_dejaria_el_stock_negativo_queda_en_conflicto(inv, mundo, client):
    stock_listo(inv, mundo)
    r = sincronizar_ok(client, inv.h_enc_centro, _op("AJUSTE_INVENTARIO", {"variante_id": inv.v_sm_rojo["id"], "diferencia": -50, "motivo": "DAÑO"}))[0]
    assert r["estado"] == "EN_CONFLICTO" and _stock(client, inv) == 10  # nada se descontó


def test_b6_el_motivo_es_obligatorio_y_la_diferencia_no_puede_ser_cero(inv, mundo, client):
    stock_listo(inv, mundo)
    sin_motivo = sincronizar_ok(client, inv.h_enc_centro, _op("AJUSTE_INVENTARIO", {"variante_id": inv.v_sm_rojo["id"], "diferencia": 2}))[0]
    en_cero = sincronizar_ok(client, inv.h_enc_centro, _op("AJUSTE_INVENTARIO", {"variante_id": inv.v_sm_rojo["id"], "diferencia": 0, "motivo": "CONTEO"}))[0]
    assert sin_motivo["estado"] == "RECHAZADA" and en_cero["estado"] == "RECHAZADA" and _stock(client, inv) == 10


def test_b6_solo_el_encargado_ajusta_y_otra_empresa_no_ve_nada(inv, mundo, tienda_b, client):
    stock_listo(inv, mundo)
    op = _op("AJUSTE_INVENTARIO", {"variante_id": inv.v_sm_rojo["id"], "diferencia": 2, "motivo": "CONTEO"})
    assert sincronizar_ok(client, inv.h_cajero, op)[0]["estado"] == "RECHAZADA"  # el Cajero no ajusta inventario
    assert _stock(client, inv) == 10


# ---------------- B5: recepción de mercadería
def test_b5_la_recepcion_suma_al_inventario_y_deja_su_movimiento(inv, mundo, client, db):
    stock_listo(inv, mundo)
    op = _op("RECEPCION", {"variante_id": inv.v_sm_rojo["id"], "cantidad": 7, "referencia": "Envío TS-0042"})
    r = sincronizar_ok(client, inv.h_enc_centro, op)[0]
    assert r["estado"] == "CONFIRMADA" and r["referencia"] == "Envío TS-0042" and _stock(client, inv) == 17
    assert db.execute(text("SELECT tipo, cantidad, nota FROM movimientos_inventario WHERE tipo = 'ENTRADA_RECEPCION' ORDER BY id DESC LIMIT 1")).one() == ("ENTRADA_RECEPCION", 7, "Recepción sin conexión: Envío TS-0042")
    assert sincronizar_ok(client, inv.h_enc_centro, op)[0]["ya_procesada"] is True and _stock(client, inv) == 17


def test_b5_la_recepcion_exige_referencia_y_solo_la_hace_el_encargado(inv, mundo, client):
    stock_listo(inv, mundo)
    sin_referencia = _op("RECEPCION", {"variante_id": inv.v_sm_rojo["id"], "cantidad": 2, "referencia": ""})
    assert sincronizar_ok(client, inv.h_enc_centro, sin_referencia)[0]["estado"] == "RECHAZADA"
    con_referencia = _op("RECEPCION", {"variante_id": inv.v_sm_rojo["id"], "cantidad": 2, "referencia": "X"})
    assert sincronizar_ok(client, inv.h_cajero, con_referencia)[0]["estado"] == "RECHAZADA"
    assert _stock(client, inv) == 10


# ---------------- B3: devolución sin conexión
def test_b3_la_devolucion_offline_aplica_el_cu41_y_devuelve_la_prenda_al_inventario(inv, mundo, client):
    stock_listo(inv, mundo)
    venta = venta_en_caja(client, inv, (inv.v_sm_rojo, 3))
    despues_de_vender = _stock(client, inv)
    op = _op("DEVOLUCION", {"comprobante": venta["comprobante_numero"], "motivo": "Le quedó pequeña", "items": [{"pedido_item_id": venta["items"][0]["id"], "cantidad": 2}],
                            "condicion": {"sin_danos": True, "sin_desgaste": True, "con_etiquetas": True}})
    r = sincronizar_ok(client, inv.h_cajero, op)[0]
    assert r["estado"] == "CONFIRMADA" and r["referencia"], r
    assert _stock(client, inv) == despues_de_vender + 2
    assert sincronizar_ok(client, inv.h_cajero, op)[0]["ya_procesada"] is True and _stock(client, inv) == despues_de_vender + 2  # reenviar no devuelve dos veces


def test_b3_si_ya_estaba_devuelta_o_venció_el_plazo_queda_rechazada_con_mensaje(inv, mundo, client, db):
    stock_listo(inv, mundo)
    venta = venta_en_caja(client, inv, (inv.v_sm_rojo, 1))
    cuerpo = {"comprobante": venta["comprobante_numero"], "motivo": "x", "items": [{"pedido_item_id": venta["items"][0]["id"], "cantidad": 1}], "condicion": {"sin_danos": True, "sin_desgaste": True, "con_etiquetas": True}}
    assert sincronizar_ok(client, inv.h_cajero, _op("DEVOLUCION", cuerpo))[0]["estado"] == "CONFIRMADA"
    otra = sincronizar_ok(client, inv.h_cajero, _op("DEVOLUCION", cuerpo))[0]  # la misma venta, otra operación: ya no queda nada por devolver
    assert otra["estado"] == "RECHAZADA" and otra["mensaje"]
    vieja = venta_en_caja(client, inv, (inv.v_sm_rojo, 1))
    envejecer_venta(db, vieja["id"], 40)
    cuerpo_vieja = {**cuerpo, "comprobante": vieja["comprobante_numero"], "items": [{"pedido_item_id": vieja["items"][0]["id"], "cantidad": 1}]}
    fuera = sincronizar_ok(client, inv.h_cajero, _op("DEVOLUCION", cuerpo_vieja))[0]
    assert fuera["estado"] == "RECHAZADA" and fuera["mensaje"]


def test_b3_un_comprobante_que_no_es_de_la_sucursal_queda_rechazado_y_no_toca_el_inventario(inv, mundo, tienda_b, client):
    stock_listo(inv, mundo)
    venta = venta_en_caja(client, inv, (inv.v_sm_rojo, 1))
    cuerpo = {"comprobante": venta["comprobante_numero"], "items": [{"pedido_item_id": venta["items"][0]["id"], "cantidad": 1}]}
    r = sincronizar_ok(client, inv.h_cajero, _op("DEVOLUCION", {**cuerpo, "comprobante": "CMP-999-000001"}))[0]
    assert r["estado"] == "RECHAZADA" and _stock(client, inv) == 9

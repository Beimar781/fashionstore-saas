"""Fase K, ajuste 3 · CU-41: la prenda devuelta se revisa (sin daños, sin desgaste, con etiquetas), vuelve al inventario con su talla y color y se acepta solo dentro del plazo (RN15)."""
import pytest

from tests.compras_util import existencias, stock_listo
from tests.devoluciones_util import devolver, devolver_ok, envejecer_venta, venta_en_caja

MSG = "La prenda no cumple las condiciones de devolución: debe estar sin daños, sin desgaste y conservar sus etiquetas."


@pytest.mark.parametrize("condicion", [
    {"sin_danos": False, "sin_desgaste": True, "con_etiquetas": True},
    {"sin_danos": True, "sin_desgaste": False, "con_etiquetas": True},
    {"sin_danos": True, "sin_desgaste": True, "con_etiquetas": False},
    {},  # sin revisar la prenda tampoco se acepta
])
def test_01_una_prenda_con_danos_desgaste_o_sin_etiquetas_no_se_recibe(inv, mundo, client, condicion):
    stock_listo(inv, mundo)
    p = venta_en_caja(client, inv, (inv.v_sm_rojo, 1))
    r = devolver(client, inv.h_cajero, p["comprobante_numero"], [(p["items"][0], 1)], condicion=condicion)
    assert r.status_code == 422 and r.json()["detail"] == MSG
    assert existencias(client, inv.h_enc_centro, inv.v_sm_rojo)["vendida"] == 1  # no se movió nada
    assert client.get("/api/devoluciones", headers=inv.h_cajero).json() == []


def test_02_tambien_el_cambio_exige_revisar_la_prenda(inv, mundo, client):
    stock_listo(inv, mundo)
    p = venta_en_caja(client, inv, (inv.v_sm_rojo, 1))
    r = devolver(client, inv.h_cajero, p["comprobante_numero"], [(p["items"][0], 1)], tipo="CAMBIO", nuevos=[(inv.var[("M", "Rojo")], 1)], condicion={"sin_danos": True, "sin_desgaste": True})
    assert r.status_code == 422 and r.json()["detail"] == MSG
    assert existencias(client, inv.h_enc_centro, inv.var[("M", "Rojo")])["vendida"] == 0


def test_03_la_nota_guarda_la_revision_y_el_inventario_recibe_la_prenda_con_su_talla_y_color(inv, mundo, client):
    stock_listo(inv, mundo)
    p = venta_en_caja(client, inv, (inv.v_sm_rojo, 2))
    d = devolver_ok(client, inv.h_cajero, p["comprobante_numero"], [(p["items"][0], 2)])
    assert (d["sin_danos"], d["sin_desgaste"], d["con_etiquetas"]) == (True, True, True)
    m = client.get("/api/inventario/movimientos", params={"tipo": "DEVOLUCION"}, headers=inv.h_enc_centro).json()["items"][0]
    assert (m["producto"], m["talla"], m["color"], m["cantidad"], m["sucursal"], m["referencia_id"]) == ("Camisa Oxford", "S", "Rojo", 2, "Centro", d["id"])
    assert existencias(client, inv.h_enc_centro, inv.v_sm_rojo)["disponible"] == 10


def test_04_pasado_el_plazo_no_se_recibe_aunque_la_prenda_este_bien(inv, mundo, client, db):
    stock_listo(inv, mundo)
    p = venta_en_caja(client, inv, (inv.v_sm_rojo, 1))
    envejecer_venta(db, p["id"], 20)  # el plazo por defecto es de 15 días
    r = devolver(client, inv.h_cajero, p["comprobante_numero"], [(p["items"][0], 1)])
    assert r.status_code == 409 and r.json()["detail"].endswith("(plazo de 15 días).")
    assert existencias(client, inv.h_enc_centro, inv.v_sm_rojo)["vendida"] == 1

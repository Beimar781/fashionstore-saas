"""Prompt R · A4: venta de contado offline completa (§7.2): forma de pago, precio usado al registrar, reloj del dispositivo."""
from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from tests.offline_util import ahora_iso, op_venta, sincronizar, sincronizar_ok, stock_listo


def _venta(variante, cantidad, precio, recibido=500):
    op = op_venta([(variante, cantidad)], recibido, forma_pago="EFECTIVO")
    op["payload"]["items"][0]["precio_unitario"] = str(precio)
    return op


def test_01_venta_con_precio_vigente_forma_de_pago_y_fecha_del_dispositivo(inv, mundo, client, db):
    stock_listo(inv, mundo)
    r = sincronizar_ok(client, inv.h_cajero, _venta(inv.v_sm_rojo, 1, "100.00"))[0]
    assert r["estado"] == "CONFIRMADA" and r["comprobante"]
    fila = db.execute(text("SELECT payload->>'forma_pago', creada_en_cliente IS NOT NULL FROM operaciones_offline")).one()
    assert tuple(fila) == ("EFECTIVO", True)


def test_02_si_el_precio_cambio_la_venta_queda_en_conflicto_y_no_descuenta(inv, mundo, client, db):
    stock_listo(inv, mundo)
    r = sincronizar_ok(client, inv.h_cajero, _venta(inv.v_sm_rojo, 1, "90.00"))[0]
    assert r["estado"] == "EN_CONFLICTO" and r["mensaje"] == "El precio de una prenda cambió desde que se registró la venta."
    assert r["detalle"]["precios"][0]["precio_registrado"] == "90.00" and r["detalle"]["precios"][0]["precio_actual"] == "100.00"
    assert db.execute(text("SELECT disponible, vendida FROM existencias WHERE variante_id = :v AND sucursal_id = :s"), {"v": inv.v_sm_rojo["id"], "s": inv.centro.id}).one() == (10, 0)


def test_03_reenviar_la_venta_en_conflicto_no_la_duplica(inv, mundo, client):
    stock_listo(inv, mundo)
    op = _venta(inv.v_sm_rojo, 1, "90.00")
    primero = sincronizar_ok(client, inv.h_cajero, op)[0]
    segundo = sincronizar_ok(client, inv.h_cajero, op)[0]
    assert (primero["estado"], segundo["estado"], segundo["ya_procesada"]) == ("EN_CONFLICTO", "EN_CONFLICTO", True)


def test_04_el_encargado_acepta_el_precio_actual_al_reintentar(inv, mundo, client):
    stock_listo(inv, mundo)
    op = _venta(inv.v_sm_rojo, 1, "90.00")
    sincronizar_ok(client, inv.h_cajero, op)
    r = client.post(f"/api/offline/conflictos/{op['id']}/resolver", json={"accion": "REINTENTAR"}, headers=inv.h_enc_centro)
    assert r.status_code == 200, r.text
    assert r.json()["estado"] == "CONFIRMADA"


def test_05_una_venta_sin_precio_registrado_se_acepta_como_antes(inv, mundo, client):
    stock_listo(inv, mundo)
    assert sincronizar_ok(client, inv.h_cajero, op_venta([(inv.v_sm_rojo, 1)], 200))[0]["estado"] == "CONFIRMADA"


def test_06_forma_de_pago_distinta_de_efectivo_se_rechaza(inv, mundo, client):
    stock_listo(inv, mundo)
    op = op_venta([(inv.v_sm_rojo, 1)], 200, forma_pago="TARJETA")
    assert sincronizar_ok(client, inv.h_cajero, op)[0]["estado"] == "RECHAZADA"


def test_07_reloj_del_dispositivo_adelantado_o_atrasado_avisa(inv, mundo, client, db):
    stock_listo(inv, mundo)
    hora = (datetime.now(timezone.utc) + timedelta(minutes=20)).isoformat()
    r = client.post("/api/offline/sincronizar", json={"operaciones": [op_venta([(inv.v_sm_rojo, 1)], 200)], "hora_dispositivo": hora}, headers=inv.h_cajero).json()
    assert r["aviso_reloj"] == "La hora de este dispositivo parece incorrecta; revísela para que sus ventas queden con la fecha correcta."
    assert 1100 < r["desfase_reloj_segundos"] < 1300
    assert db.execute(text("SELECT desfase_reloj_segundos FROM operaciones_offline")).scalar() > 1100


def test_08_reloj_correcto_no_avisa(inv, mundo, client):
    stock_listo(inv, mundo)
    r = client.post("/api/offline/sincronizar", json={"operaciones": [op_venta([(inv.v_sm_rojo, 1)], 200)], "hora_dispositivo": ahora_iso(30)}, headers=inv.h_cajero).json()
    assert r["aviso_reloj"] is None and abs(r["desfase_reloj_segundos"]) < 300

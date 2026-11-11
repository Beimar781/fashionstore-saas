"""Defensa D2 · Cobrar una reserva en caja sin conexión: la venta de contado lleva el código de la reserva (CU-29 con reserva) y se confirma al sincronizar.

El stock de la reserva ya estaba apartado: se vende lo reservado, no se descuenta dos veces; si la reserva no se puede cobrar, la venta se rechaza con el mensaje de la ficha."""
import uuid

from tests.offline_util import ahora_iso, op_venta, sincronizar_ok
from tests.reservas_util import fila, reserva_ok

MSG_CODIGO_RESERVA = "El código de reserva no existe o ya ha expirado su vigencia."
MSG_FUERA_DE_RESERVA = "La venta incluye prendas o cantidades que no están en la reserva."


def _op(tipo, **payload):
    return {"id": str(uuid.uuid4()), "tipo": tipo, "creada_en": ahora_iso(), "payload": payload}


def _reserva_preparada(inv, mundo, client):
    """Reserva de 2 camisas rojas y 1 azul con su stock apartado, ya preparada por el Encargado (cobrable en caja)."""
    inv.stock(mundo.a.id, inv.centro.id, inv.v_sm_rojo["id"], 10)
    inv.stock(mundo.a.id, inv.centro.id, inv.var[("M", "Azul")]["id"], 10)
    r = reserva_ok(client, inv.h_cliente, inv.centro, (inv.v_sm_rojo, 2), (inv.var[("M", "Azul")], 1))
    assert sincronizar_ok(client, inv.h_enc_centro, _op("PREPARAR_RESERVA", reserva_id=r["id"]))[0]["estado"] == "CONFIRMADA"
    return r


def _estado(client, inv, reserva_id):
    return client.get(f"/api/reservas-sucursal/{reserva_id}", headers=inv.h_enc_centro).json()["estado"]


def test_01_el_cajero_descarga_solo_las_reservas_que_ya_se_pueden_cobrar(inv, mundo, client):
    inv.stock(mundo.a.id, inv.centro.id, inv.v_sm_rojo["id"], 10)
    pendiente = reserva_ok(client, inv.h_cliente, inv.centro, (inv.v_sm_rojo, 1))
    assert client.get("/api/offline/catalogo", headers=inv.h_cajero).json()["reservas_sucursal"] == []  # sin preparar no se cobra
    sincronizar_ok(client, inv.h_enc_centro, _op("PREPARAR_RESERVA", reserva_id=pendiente["id"]))
    d = client.get("/api/offline/catalogo", headers=inv.h_cajero).json()["reservas_sucursal"]
    assert [(r["codigo"], r["estado"], r["cliente"]) for r in d] == [(pendiente["codigo"], "PREPARADA", d[0]["cliente"])] and d[0]["cliente"]
    assert d[0]["items"][0]["variante_id"] == inv.v_sm_rojo["id"] and d[0]["items"][0]["cantidad"] == 1


def test_02_cobrar_la_reserva_sin_conexion_la_completa_y_no_descuenta_dos_veces(inv, mundo, client):
    r = _reserva_preparada(inv, mundo, client)
    antes = fila(client, inv.h_enc_centro, inv.v_sm_rojo)
    assert antes["reservada"] == 2
    venta = op_venta([(inv.v_sm_rojo, 2), (inv.var[("M", "Azul")], 1)], 400, reserva_codigo=r["codigo"])
    res = sincronizar_ok(client, inv.h_cajero, venta)[0]
    assert res["estado"] == "CONFIRMADA" and res["comprobante"].startswith(f"CMP-{inv.centro.id:03d}-")
    despues = fila(client, inv.h_enc_centro, inv.v_sm_rojo)
    assert (despues["disponible"], despues["reservada"], despues["vendida"]) == (antes["disponible"], 0, antes["vendida"] + 2)  # lo apartado pasó a vendido
    assert _estado(client, inv, r["id"]) == "COMPLETADA"
    assert sincronizar_ok(client, inv.h_cajero, venta)[0]["ya_procesada"] is True  # reenviarla no cobra otra vez
    assert fila(client, inv.h_enc_centro, inv.v_sm_rojo)["vendida"] == antes["vendida"] + 2


def test_03_una_reserva_sin_preparar_o_con_prendas_de_mas_se_rechaza(inv, mundo, client):
    inv.stock(mundo.a.id, inv.centro.id, inv.v_sm_rojo["id"], 10)
    sin_preparar = reserva_ok(client, inv.h_cliente, inv.centro, (inv.v_sm_rojo, 1))
    r = sincronizar_ok(client, inv.h_cajero, op_venta([(inv.v_sm_rojo, 1)], 100, reserva_codigo=sin_preparar["codigo"]))[0]
    assert r["estado"] == "RECHAZADA" and r["mensaje"] == MSG_CODIGO_RESERVA
    sincronizar_ok(client, inv.h_enc_centro, _op("PREPARAR_RESERVA", reserva_id=sin_preparar["id"]))
    de_mas = sincronizar_ok(client, inv.h_cajero, op_venta([(inv.v_sm_rojo, 3)], 300, reserva_codigo=sin_preparar["codigo"]))[0]
    assert de_mas["estado"] == "RECHAZADA" and de_mas["mensaje"] == MSG_FUERA_DE_RESERVA
    assert _estado(client, inv, sin_preparar["id"]) == "PREPARADA"  # no se tocó

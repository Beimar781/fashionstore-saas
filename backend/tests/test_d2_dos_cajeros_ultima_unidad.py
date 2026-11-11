"""Defensa D2 · Dos cajeros, en dos dispositivos sin red, venden la última unidad de la misma prenda (CU-38, CU-40, CU-41; RN11, RN12, RN14).

Al volver la red, la primera venta que llega se confirma y la segunda queda EN_CONFLICTO sin descontar ni cobrar nada; el Encargado la descarta
devolviendo el efectivo al cliente y el Cajero la ve rechazada con ese motivo."""
from sqlalchemy import text

from tests.catalogo_util import entrar
from tests.compras_util import existencias
from tests.offline_util import contar, op_venta, sincronizar_ok, stock_listo

CONDICION_OK = {"sin_danos": True, "sin_desgaste": True, "con_etiquetas": True}


def _segundo_cajero(datos, mundo, client, inv):
    datos.usuario(mundo.a, "Cajero", email="cajero2@a.com", sucursal=inv.centro)
    return entrar(client, mundo.a, "cajero2@a.com")


def _disponible(db, inv):
    return db.execute(text("SELECT disponible FROM existencias WHERE variante_id = :v AND sucursal_id = :s"), {"v": inv.v_sm_rojo["id"], "s": inv.centro.id}).scalar()


def test_01_la_primera_venta_se_confirma_y_la_segunda_queda_en_conflicto_sin_cobrar_nada(inv, mundo, datos, client, db):
    stock_listo(inv, mundo, centro=1)  # queda UNA sola unidad de la camisa S rojo en Centro
    h_cajero2 = _segundo_cajero(datos, mundo, client, inv)
    primera = op_venta([(inv.v_sm_rojo, 1)], 100)   # UUID distinto en cada dispositivo (RN11)
    segunda = op_venta([(inv.v_sm_rojo, 1)], 100)
    assert primera["id"] != segunda["id"]

    a = sincronizar_ok(client, inv.h_cajero, primera)[0]    # la que llega primero gana
    b = sincronizar_ok(client, h_cajero2, segunda)[0]
    assert a["estado"] == "CONFIRMADA" and a["comprobante"].startswith(f"CMP-{inv.centro.id:03d}-")
    assert b["estado"] == "EN_CONFLICTO" and b["referencia"] is None and b["comprobante"] is None
    assert b["detalle"]["faltantes"] == [{"variante_id": inv.v_sm_rojo["id"], "producto": "Camisa Oxford", "talla": "S", "color": "Rojo", "solicitadas": 1, "disponibles": 0}]
    f = existencias(client, inv.h_enc_centro, inv.v_sm_rojo)
    assert (f["disponible"], f["vendida"]) == (0, 1)  # solo se vendió una unidad (RN14: nada se descuenta a medias)
    assert contar(db, "pedidos", canal="PRESENCIAL") == 1 and contar(db, "pagos") == 1  # la segunda venta no cobró nada

    # reenviar la venta en conflicto (RNF05) ni la duplica ni cambia su resultado
    otra_vez = sincronizar_ok(client, h_cajero2, segunda)[0]
    assert otra_vez["ya_procesada"] is True and otra_vez["estado"] == "EN_CONFLICTO"
    assert contar(db, "pedidos", canal="PRESENCIAL") == 1 and contar(db, "operaciones_offline") == 2


def test_02_el_encargado_descarta_la_segunda_devolviendo_el_efectivo_y_el_cajero_la_ve_rechazada(inv, mundo, datos, client, db):
    stock_listo(inv, mundo, centro=1)
    h_cajero2 = _segundo_cajero(datos, mundo, client, inv)
    sincronizar_ok(client, inv.h_cajero, op_venta([(inv.v_sm_rojo, 1)], 100))
    segunda = op_venta([(inv.v_sm_rojo, 1)], 100)
    assert sincronizar_ok(client, h_cajero2, segunda)[0]["estado"] == "EN_CONFLICTO"

    conflictos = client.get("/api/offline/conflictos", headers=inv.h_enc_centro).json()
    assert [c["id"] for c in conflictos] == [segunda["id"]]  # el Encargado ve solo la que quedó en conflicto
    r = client.post(f"/api/offline/conflictos/{segunda['id']}/resolver", json={"accion": "DESCARTAR", "motivo": "La prenda se agotó", "devolver_dinero": True, "condicion": CONDICION_OK}, headers=inv.h_enc_centro)
    assert r.status_code == 200, r.text
    assert r.json()["estado"] == "RECHAZADA" and "Se devolvieron Bs 100.00 en efectivo al cliente (nota NDV-" in r.json()["mensaje"]

    d = client.get("/api/devoluciones", headers=inv.h_cajero).json()[0]  # se registró la devolución del efectivo (CU-41)
    assert (d["tipo"], d["reembolso"], d["medio_reembolso"]) == ("DEVOLUCION", "100.00", "EFECTIVO")
    assert _disponible(db, inv) == 0  # la unidad vendida primero sigue siendo del primer cliente
    mia = {o["id"]: o for o in client.get("/api/offline/operaciones", headers=h_cajero2).json()}[segunda["id"]]
    assert mia["estado"] == "RECHAZADA" and "Se devolvieron Bs 100.00" in mia["mensaje"]  # lo que muestra «Ventas con problema» en Caja
    assert client.get("/api/offline/conflictos", headers=inv.h_enc_centro).json() == []

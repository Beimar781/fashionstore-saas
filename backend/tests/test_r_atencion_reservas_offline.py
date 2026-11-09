"""Prompt R · B4: el Encargado atiende reservas sin conexión (preparar, prenda no encontrada, atender y completar) y la descarga trae lo necesario."""
import uuid

from tests.offline_util import ahora_iso, sincronizar_ok
from tests.reservas_util import fila, reserva_ok


def _op(tipo, **payload):
    return {"id": str(uuid.uuid4()), "tipo": tipo, "creada_en": ahora_iso(), "payload": payload}


def _reserva(inv, mundo, client):
    if not getattr(inv, "stock_de_reservas", False):  # el stock se crea una sola vez por prueba
        inv.stock(mundo.a.id, inv.centro.id, inv.v_sm_rojo["id"], 10)
        inv.stock(mundo.a.id, inv.centro.id, inv.var[("M", "Azul")]["id"], 10)
        inv.stock_de_reservas = True
    return reserva_ok(client, inv.h_cliente, inv.centro, (inv.v_sm_rojo, 2), (inv.var[("M", "Azul")], 1))


def _estado(client, inv, reserva_id):
    return client.get(f"/api/reservas-sucursal/{reserva_id}", headers=inv.h_enc_centro).json()["estado"]


def test_la_descarga_del_encargado_trae_reservas_y_ventas_recientes_con_el_plazo(inv, mundo, client):
    from tests.devoluciones_util import venta_en_caja
    from tests.compras_util import stock_listo

    stock_listo(inv, mundo)
    reserva = reserva_ok(client, inv.h_cliente, inv.centro, (inv.v_sm_rojo, 1))
    venta = venta_en_caja(client, inv, (inv.v_sm_rojo, 2))
    d = client.get("/api/offline/catalogo", headers=inv.h_enc_centro).json()
    assert d["plazo_devolucion_dias"] == 15
    assert [r["id"] for r in d["reservas_sucursal"]] == [reserva["id"]] and d["reservas_sucursal"][0]["items"][0]["estado"] == "RESERVADO"
    assert [v["comprobante"] for v in d["ventas_recientes"]] == [venta["comprobante_numero"]] and d["ventas_recientes"][0]["items"][0]["devolvible"] == 2
    cajero = client.get("/api/offline/catalogo", headers=inv.h_cajero).json()
    assert cajero["reservas_sucursal"] == [] and len(cajero["ventas_recientes"]) == 1  # el Cajero solo recibe las ventas
    assert client.get("/api/offline/catalogo", headers=inv.h_cliente).json()["ventas_recientes"] == []


def test_preparar_la_reserva_sin_conexion_y_reenviar_no_la_repite(inv, mundo, client):
    r = _reserva(inv, mundo, client)
    op = _op("PREPARAR_RESERVA", reserva_id=r["id"])
    primero, segundo = sincronizar_ok(client, inv.h_enc_centro, op)[0], sincronizar_ok(client, inv.h_enc_centro, op)[0]
    assert (primero["estado"], primero["referencia"], segundo["ya_procesada"]) == ("CONFIRMADA", r["codigo"], True)
    assert _estado(client, inv, r["id"]) == "PREPARADA"


def test_prenda_no_encontrada_ajusta_el_stock_y_avisa_al_cliente(inv, mundo, client):
    r = _reserva(inv, mundo, client)
    item = client.get(f"/api/reservas-sucursal/{r['id']}", headers=inv.h_enc_centro).json()["items"][0]
    antes = fila(client, inv.h_enc_centro, inv.v_sm_rojo)
    res = sincronizar_ok(client, inv.h_enc_centro, _op("PRENDA_NO_ENCONTRADA", reserva_id=r["id"], item_id=item["id"]))[0]
    assert res["estado"] == "CONFIRMADA"
    despues = fila(client, inv.h_enc_centro, inv.v_sm_rojo)
    assert despues["reservada"] < antes["reservada"] and despues["disponible"] <= antes["disponible"]


def test_atender_y_completar_sin_comprar_libera_el_stock_apartado(inv, mundo, client):
    r = _reserva(inv, mundo, client)
    res = sincronizar_ok(client, inv.h_enc_centro, _op("ATENDER_RESERVA", reserva_id=r["id"], llevara_prendas=False))[0]
    assert res["estado"] == "CONFIRMADA"
    assert fila(client, inv.h_enc_centro, inv.v_sm_rojo)["reservada"] == 0


def test_atender_llevando_las_prendas_deja_la_reserva_en_probador_para_la_venta(inv, mundo, client):
    r = _reserva(inv, mundo, client)
    assert sincronizar_ok(client, inv.h_enc_centro, _op("ATENDER_RESERVA", reserva_id=r["id"], llevara_prendas=True))[0]["estado"] == "CONFIRMADA"
    assert _estado(client, inv, r["id"]) == "EN_PROBADOR"


def test_si_otro_dispositivo_ya_la_atendio_o_la_cancelo_queda_rechazada_con_mensaje(inv, mundo, client):
    r = _reserva(inv, mundo, client)
    assert client.post(f"/api/atencion-reservas/{r['id']}/atender", headers=inv.h_enc_centro).status_code == 200  # otro dispositivo la atendió primero
    res = sincronizar_ok(client, inv.h_enc_centro, _op("ATENDER_RESERVA", reserva_id=r["id"]))[0]
    assert res["estado"] == "RECHAZADA" and "pendiente o preparada" in res["mensaje"]
    otra = _reserva(inv, mundo, client)
    assert client.post(f"/api/reservas/{otra['id']}/cancelar", json={"motivo": "x"}, headers=inv.h_cliente).status_code == 200
    res = sincronizar_ok(client, inv.h_enc_centro, _op("PREPARAR_RESERVA", reserva_id=otra["id"]))[0]
    assert res["estado"] == "RECHAZADA" and res["mensaje"]


def test_solo_el_encargado_de_esa_sucursal_atiende(inv, mundo, client):
    r = _reserva(inv, mundo, client)
    assert sincronizar_ok(client, inv.h_cajero, _op("PREPARAR_RESERVA", reserva_id=r["id"]))[0]["estado"] == "RECHAZADA"  # el Cajero no atiende reservas
    assert sincronizar_ok(client, inv.h_enc_norte, _op("PREPARAR_RESERVA", reserva_id=r["id"]))[0]["estado"] == "RECHAZADA"  # otra sucursal: «Reserva no encontrada.»
    assert _estado(client, inv, r["id"]) == "PENDIENTE"

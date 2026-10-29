"""Fase K, ajuste 3 · Compra del cliente sin conexión que ya no se puede cumplir (CU-38, CU-40, CU-41, CU-32).

Escenario de la ingeniera: dos clientes quieren la última unidad; uno compra con conexión y el otro sin conexión. La compra real es la del primero; al segundo se le avisa
(campana + push) sin haberle descontado ni cobrado nada. Si ya había entregado efectivo en caja, el Encargado descarta la venta devolviéndole el dinero con CU-41."""
import uuid

import pytest
from sqlalchemy import text

from tests.catalogo_util import entrar
from tests.compras_util import comprar, existencias, iniciar, tarjeta
from tests.offline_util import agregar_stock, ahora_iso, contar, op_reserva, op_venta, sincronizar, sincronizar_ok, stock_listo

MSG_CONDICION = "La prenda no cumple las condiciones de devolución: debe estar sin daños, sin desgaste y conservar sus etiquetas."
CONDICION_OK = {"sin_danos": True, "sin_desgaste": True, "con_etiquetas": True}


def op_compra(inv, items, id_=None, segundos=0, sucursal=None):
    """Compra del cliente armada sin conexión (pedido por pagar; no lleva datos de tarjeta)."""
    sucursal = sucursal or inv.centro
    payload = {"sucursal_id": sucursal.id, "items": [{"variante_id": v["id"], "cantidad": c} for v, c in items]}
    return {"id": str(id_ or uuid.uuid4()), "tipo": "COMPRA", "creada_en": ahora_iso(segundos), "payload": payload, "sucursal_id": sucursal.id}


def _cliente2(datos, mundo):
    u = datos.usuario(mundo.a, "Cliente", email="cliente2@tienda.com")
    return u, datos.login(u, mundo.a)


def _ultima_unidad(inv, mundo, db):
    """Camisa S Rojo con una sola unidad en Centro."""
    stock_listo(inv, mundo)
    agregar_stock(db, inv.v_sm_rojo, inv.centro, -9)
    assert existencias_de(db, inv.v_sm_rojo, inv.centro) == 1


def existencias_de(db, variante, sucursal):
    return db.execute(text("SELECT disponible FROM existencias WHERE variante_id = :v AND sucursal_id = :s"), {"v": variante["id"], "s": sucursal.id}).scalar()


def _avisos(client, h, tipo="OPERACION_OFFLINE"):
    return [n for n in client.get("/api/notificaciones", headers=h).json() if n["tipo"] == tipo]


def _dispositivo(client, h):
    return client.post("/api/notificaciones/dispositivos", json={"canal": "MOVIL", "token": "simulado-" + uuid.uuid4().hex}, headers=h)


def _resolver(client, h, operacion_id, **cuerpo):
    return client.post(f"/api/offline/conflictos/{operacion_id}/resolver", json=cuerpo, headers=h)


# ---------------- la compra se registra y se paga en línea ----------------
def test_01_con_stock_la_compra_queda_como_pedido_por_pagar_y_el_cliente_la_paga_en_linea(inv, mundo, datos, client, db):
    stock_listo(inv, mundo)
    u2, h2 = _cliente2(datos, mundo)
    _dispositivo(client, h2)
    r = sincronizar_ok(client, h2, op_compra(inv, [(inv.v_sm_rojo, 2)]))[0]
    assert r["estado"] == "CONFIRMADA" and r["referencia"] and r["comprobante"] is None
    pedido = db.execute(text("SELECT id, estado, canal, tipo_entrega, total, comprobante_numero FROM pedidos WHERE cliente_id = :c"), {"c": u2.id}).one()
    assert (pedido.estado, pedido.canal, pedido.tipo_entrega, str(pedido.total), pedido.comprobante_numero) == ("PENDIENTE_PAGO", "DIGITAL", "EN_TIENDA", "200.00", None)
    assert existencias_de(db, inv.v_sm_rojo, inv.centro) == 10  # nada se descontó ni se cobró: la tarjeta se cobra en línea
    assert db.execute(text("SELECT count(*) FROM pagos WHERE pedido_id = :p"), {"p": pedido.id}).scalar() == 0
    aviso = _avisos(client, h2)[0]
    assert aviso["titulo"] == "Su compra está lista para pagar" and r["referencia"] in aviso["mensaje"] and "Pague con tarjeta" in aviso["mensaje"]
    assert db.execute(text("SELECT estado FROM push_envios WHERE usuario_id = :u"), {"u": u2.id}).scalar() == "SIMULADO"
    pago = iniciar(client, h2, pedido.id).json()
    ok = client.post(f"/api/pagos/{pago['pago_id']}/confirmar", json={"tarjeta": tarjeta()}, headers=h2).json()
    assert ok["aprobado"] and ok["pedido"]["estado"] == "PAGADO"
    assert existencias_de(db, inv.v_sm_rojo, inv.centro) == 8  # recién al pagar se descuenta


def test_02_el_reenvio_de_la_misma_compra_no_la_duplica(inv, mundo, datos, client, db):
    stock_listo(inv, mundo)
    u2, h2 = _cliente2(datos, mundo)
    op = op_compra(inv, [(inv.v_sm_rojo, 1)])
    primera = sincronizar_ok(client, h2, op)[0]
    segunda = sincronizar_ok(client, h2, op)[0]
    assert segunda["ya_procesada"] is True and segunda["referencia"] == primera["referencia"]
    assert contar(db, "pedidos", cliente_id=u2.id) == 1 and len(_avisos(client, h2)) == 1


# ---------------- el escenario de la última unidad ----------------
def test_03_dos_clientes_una_unidad_el_que_estaba_sin_conexion_queda_en_conflicto_y_se_le_avisa(inv, mundo, datos, client, db):
    _ultima_unidad(inv, mundo, db)
    u2, h2 = _cliente2(datos, mundo)
    _dispositivo(client, h2)
    comprar(client, inv.h_cliente, inv, inv.v_sm_rojo)  # el cliente con conexión se lleva la última unidad
    assert existencias_de(db, inv.v_sm_rojo, inv.centro) == 0
    op = op_compra(inv, [(inv.v_sm_rojo, 1)])
    r = sincronizar_ok(client, h2, op)[0]
    assert r["estado"] == "EN_CONFLICTO" and r["detalle"]["faltantes"][0]["disponibles"] == 0
    assert contar(db, "pedidos", cliente_id=u2.id) == 0 and existencias_de(db, inv.v_sm_rojo, inv.centro) == 0  # nada creado, nada descontado, nada cobrado
    aviso = _avisos(client, h2)[0]
    codigo = "COM-" + op["id"][:8].upper()
    assert aviso["mensaje"] == f"Su compra {codigo} no se pudo realizar porque la prenda se agotó."
    assert db.execute(text("SELECT estado, titulo FROM push_envios WHERE usuario_id = :u"), {"u": u2.id}).one() == ("SIMULADO", "No se pudo realizar su compra")
    del_personal = [n for n in client.get("/api/notificaciones", headers=inv.h_enc_centro).json() if n["tipo"] == "CONFLICTO_SYNC"]
    assert len(del_personal) == 1 and "compra" in del_personal[0]["mensaje"]  # el aviso al personal se conserva
    assert _avisos(client, inv.h_cliente) == []  # el otro cliente no recibe nada
    assert [c["tipo"] for c in client.get("/api/offline/conflictos", headers=inv.h_enc_centro).json()] == ["COMPRA"]


def test_04_una_reserva_sin_conexion_que_ya_no_alcanza_tambien_se_avisa(inv, mundo, datos, client, db):
    _ultima_unidad(inv, mundo, db)
    u2, h2 = _cliente2(datos, mundo)
    comprar(client, inv.h_cliente, inv, inv.v_sm_rojo)
    op = op_reserva(inv.centro, [(inv.v_sm_rojo, 1)])
    assert sincronizar_ok(client, h2, op)[0]["estado"] == "EN_CONFLICTO"
    aviso = _avisos(client, h2)[0]
    assert aviso["titulo"] == "No se pudo realizar su reserva" and aviso["mensaje"] == f"Su reserva RES-{op['id'][:8].upper()} no se pudo realizar porque la prenda se agotó."


def test_05_si_la_prenda_se_agota_mientras_paga_la_tarjeta_no_se_cobra_y_se_le_avisa(inv, mundo, datos, client, db):
    stock_listo(inv, mundo)
    agregar_stock(db, inv.v_sm_rojo, inv.centro, -9)
    u2, h2 = _cliente2(datos, mundo)
    r = sincronizar_ok(client, h2, op_compra(inv, [(inv.v_sm_rojo, 1)]))[0]
    assert r["estado"] == "CONFIRMADA"
    pedido_id = db.execute(text("SELECT id FROM pedidos WHERE cliente_id = :c"), {"c": u2.id}).scalar()
    pago_id = iniciar(client, h2, pedido_id).json()["pago_id"]  # ya hay una autorización en la pasarela
    agregar_stock(db, inv.v_sm_rojo, inv.centro, -1)  # otra persona se lleva la última unidad antes de confirmar
    c = client.post(f"/api/pagos/{pago_id}/confirmar", json={"tarjeta": tarjeta()}, headers=h2)
    assert c.status_code == 409
    assert db.execute(text("SELECT estado FROM pagos WHERE id = :p"), {"p": pago_id}).scalar() == "CANCELADO"  # la autorización se anuló: no se cobró
    aviso = _avisos(client, h2, "PAGO_SIN_STOCK")[0]
    assert aviso["mensaje"] == f"Su compra {r['referencia']} no se pudo completar porque la prenda se agotó. No se le cobró nada."


# ---------------- el Encargado resuelve el conflicto de la compra ----------------
def test_06_descartar_la_compra_avisa_al_cliente_y_reintentar_con_stock_la_deja_lista_para_pagar(inv, mundo, datos, client, db):
    _ultima_unidad(inv, mundo, db)
    u2, h2 = _cliente2(datos, mundo)
    comprar(client, inv.h_cliente, inv, inv.v_sm_rojo)
    op1, op2 = op_compra(inv, [(inv.v_sm_rojo, 1)]), op_compra(inv, [(inv.v_sm_rojo, 1)], segundos=5)
    sincronizar_ok(client, h2, op1, op2)
    r = _resolver(client, inv.h_enc_centro, op1["id"], accion="DESCARTAR", motivo="La prenda se agotó")
    assert r.status_code == 200 and r.json()["estado"] == "RECHAZADA"
    assert "No se le cobró nada." in [n for n in _avisos(client, h2) if n["titulo"] == "Su compra fue cancelada"][0]["mensaje"]
    agregar_stock(db, inv.v_sm_rojo, inv.centro, 3)  # llega mercadería
    r = _resolver(client, inv.h_enc_centro, op2["id"], accion="REINTENTAR")
    assert r.status_code == 200 and r.json()["estado"] == "CONFIRMADA" and r.json()["referencia"]
    assert contar(db, "pedidos", cliente_id=u2.id, estado="PENDIENTE_PAGO") == 1
    assert _avisos(client, h2)[0]["titulo"] == "Su compra está lista para pagar"


# ---------------- venta de contado ya cobrada: se descarta devolviendo el dinero ----------------
def _venta_en_conflicto(client, inv, mundo, db, datos):
    """El cliente 1 compra en línea la última unidad; el Cajero, sin conexión, le cobró en efectivo la misma prenda a otro cliente identificado."""
    _ultima_unidad(inv, mundo, db)
    u2, h2 = _cliente2(datos, mundo)
    _dispositivo(client, h2)
    comprar(client, inv.h_cliente, inv, inv.v_sm_rojo)
    op = op_venta([(inv.v_sm_rojo, 1)], 100, cliente_email="cliente2@tienda.com")
    assert sincronizar_ok(client, inv.h_cajero, op)[0]["estado"] == "EN_CONFLICTO"
    return u2, h2, op


def test_07_la_venta_de_caja_en_conflicto_avisa_al_cliente_identificado(inv, mundo, datos, client, db):
    u2, h2, op = _venta_en_conflicto(client, inv, mundo, db, datos)
    assert _avisos(client, h2)[0]["mensaje"] == f"Su compra VTA-{op['id'][:8].upper()} no se pudo realizar porque la prenda se agotó."


def test_08_descartar_una_venta_cobrada_devuelve_el_dinero_con_cu41_y_la_prenda_pasa_por_el_inventario(inv, mundo, datos, client, db):
    u2, h2, op = _venta_en_conflicto(client, inv, mundo, db, datos)
    r = _resolver(client, inv.h_enc_centro, op["id"], accion="DESCARTAR", motivo="La prenda se agotó", devolver_dinero=True, condicion=CONDICION_OK)
    assert r.status_code == 200, r.text
    assert r.json()["estado"] == "RECHAZADA" and "Se devolvieron Bs 100.00 en efectivo al cliente (nota NDV-" in r.json()["mensaje"]
    d = client.get("/api/devoluciones", headers=inv.h_cajero).json()[0]
    assert (d["tipo"], d["reembolso"], d["medio_reembolso"], d["registrada_por"], d["sin_danos"], d["con_etiquetas"]) == ("DEVOLUCION", "100.00", "EFECTIVO", "Encargado Prueba", True, True)
    assert d["motivo"] == "Venta sin conexión descartada: La prenda se agotó" and [(i["sentido"], i["talla"], i["color"], i["cantidad"]) for i in d["items"]] == [("DEVUELTA", "S", "Rojo", 1)]
    assert existencias_de(db, inv.v_sm_rojo, inv.centro) == 0  # el inventario queda igual: la unidad sigue siendo del cliente que pagó en línea
    movs = client.get("/api/inventario/movimientos", params={"tipo": "DEVOLUCION"}, headers=inv.h_enc_centro).json()["items"]
    ventas = [m for m in client.get("/api/inventario/movimientos", params={"tipo": "VENTA"}, headers=inv.h_enc_centro).json()["items"] if m["referencia_tipo"] == "DEVOLUCION"]
    assert [(m["talla"], m["color"], m["cantidad"]) for m in movs] == [("S", "Rojo", 1)] and [(m["talla"], m["color"], m["cantidad"]) for m in ventas] == [("S", "Rojo", 1)]
    aviso = [n for n in _avisos(client, h2) if n["titulo"] == "Su compra fue cancelada"][0]
    assert f"Se le devolvieron Bs 100.00 en efectivo (nota {d['numero']})." in aviso["mensaje"]
    assert db.execute(text("SELECT pedido_id FROM operaciones_offline WHERE operacion_id = :o"), {"o": op["id"]}).scalar() is not None
    assert _resolver(client, inv.h_enc_centro, op["id"], accion="DESCARTAR", motivo="otra vez").status_code == 409  # ya está resuelta


def test_09_si_la_prenda_no_esta_en_condiciones_no_se_devuelve_el_dinero_y_sigue_en_conflicto(inv, mundo, datos, client, db):
    u2, h2, op = _venta_en_conflicto(client, inv, mundo, db, datos)
    r = _resolver(client, inv.h_enc_centro, op["id"], accion="DESCARTAR", motivo="La prenda se agotó", devolver_dinero=True, condicion={**CONDICION_OK, "con_etiquetas": False})
    assert r.status_code == 422 and r.json()["detail"] == MSG_CONDICION
    assert client.get("/api/devoluciones", headers=inv.h_cajero).json() == [] and contar(db, "pedidos", canal="PRESENCIAL") == 0
    assert [c["estado"] for c in client.get("/api/offline/conflictos", headers=inv.h_enc_centro).json()] == ["EN_CONFLICTO"]
    assert existencias_de(db, inv.v_sm_rojo, inv.centro) == 0


def test_10_solo_una_venta_de_contado_se_descarta_devolviendo_dinero(inv, mundo, datos, client, db):
    _ultima_unidad(inv, mundo, db)
    u2, h2 = _cliente2(datos, mundo)
    comprar(client, inv.h_cliente, inv, inv.v_sm_rojo)
    op = op_compra(inv, [(inv.v_sm_rojo, 1)])
    sincronizar_ok(client, h2, op)
    r = _resolver(client, inv.h_enc_centro, op["id"], accion="DESCARTAR", motivo="Agotada", devolver_dinero=True, condicion=CONDICION_OK)
    assert r.status_code == 422 and r.json()["detail"] == "Solo una venta de contado ya cobrada se descarta devolviendo el dinero."


# ---------------- permisos y aislamiento ----------------
def test_11_solo_el_cliente_registra_compras_sin_conexion(inv, mundo, client):
    stock_listo(inv, mundo)
    r = sincronizar_ok(client, inv.h_cajero, op_compra(inv, [(inv.v_sm_rojo, 1)]))[0]
    assert r["estado"] == "RECHAZADA" and r["mensaje"] == "No tiene permisos para registrar este tipo de operación sin conexión."


def test_12_aislamiento_la_compra_de_otra_empresa_no_toca_a_la_empresa_a(inv, mundo, tienda_b, datos, client, db):
    _ultima_unidad(inv, mundo, db)
    u2, h2 = _cliente2(datos, mundo)
    comprar(client, inv.h_cliente, inv, inv.v_sm_rojo)
    op = op_compra(inv, [(inv.v_sm_rojo, 1)])
    sincronizar_ok(client, h2, op)  # conflicto en EMP-A
    cb = datos.usuario(mundo.b, "Cliente", email="cliente@emp-b.com")
    hb = datos.login(cb, mundo.b)
    # un cliente de EMP-B intenta comprar prendas y sucursal de EMP-A: no existen para él
    r = sincronizar_ok(client, hb, op_compra(inv, [(inv.v_sm_rojo, 1)]))[0]
    assert r["estado"] == "RECHAZADA" and r["mensaje"] == "Sucursal no encontrada."
    assert contar(db, "pedidos", cliente_id=cb.id) == 0 and _avisos(client, hb) == []
    # y el personal de EMP-B no ve ni resuelve los conflictos de EMP-A
    admin_b = datos.login(mundo.admin_b, mundo.b)
    assert client.get("/api/offline/conflictos", headers=admin_b).json() == []
    assert _resolver(client, admin_b, op["id"], accion="DESCARTAR", motivo="intento ajeno").status_code in (403, 404)
    assert [c["estado"] for c in client.get("/api/offline/conflictos", headers=inv.h_enc_centro).json()] == ["EN_CONFLICTO"]

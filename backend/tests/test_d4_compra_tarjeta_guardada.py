"""Defensa D4 · El Cliente deja pagada su compra sin conexión con una tarjeta GUARDADA; el cobro real lo hace el servidor al sincronizar (CU-38 + CU-32).

Seguridad: la operación solo lleva el identificador de la tarjeta guardada y el total autorizado, nunca número, fecha ni CVC. El cobro va después de confirmar la compra y
nunca la deshace: si falla, el pedido queda por pagar. El operacion_id es la clave de idempotencia (RNF05)."""
import uuid

import pytest
from sqlalchemy import text

from app.primer_parcial.ventas.cu32_pago_electronico import service as servicio_pago
from app.primer_parcial.ventas.cu32_pago_electronico.pasarela import PasarelaStripe
from app.primer_parcial.ventas.models import TarjetaGuardada
from tests.compras_util import VISA_OK, agregar_ok, checkout_ok, existencias, pagar, stock_listo
from tests.offline_util import ahora_iso, contar, sincronizar, sincronizar_ok
from tests.stripe_falso import StripeFalso

MSG_AGOTADA = "La prenda se agotó mientras estaba sin conexión. No se le cobró nada."
MSG_PRECIO = "El precio cambió; confirme el nuevo total."
MSG_COBRADA = "Compra cobrada y confirmada."
MSG_NO_COBRADA = "No pudimos cobrar su tarjeta; complete el pago desde Mis compras."


def _op_compra(inv, cantidad=1, tarjeta_id=None, total=None, **extra):
    """Compra del cliente armada sin conexión; con tarjeta_id lleva su identificador y el total que autorizó (Bs 100 la camisa)."""
    payload = {"sucursal_id": inv.centro.id, "items": [{"variante_id": inv.v_sm_rojo["id"], "cantidad": cantidad}], "tipo_entrega": "RETIRO", "nit_ci": "1234567", "razon_social": "Cliente Prueba", **extra}
    if tarjeta_id is not None:
        payload.update(tarjeta_guardada_id=tarjeta_id, total_autorizado=str(total if total is not None else 100 * cantidad))
    return {"id": str(uuid.uuid4()), "tipo": "COMPRA", "creada_en": ahora_iso(), "payload": payload, "sucursal_id": inv.centro.id}


def _tarjeta_guardada(client, inv, h=None):
    """Una compra aprobada en línea guardando la tarjeta (queda Visa 4242). Devuelve el id de la tarjeta guardada."""
    h = h or inv.h_cliente
    agregar_ok(client, h, inv.var[("M", "Azul")], inv.centro, 1)
    pagar(client, h, checkout_ok(client, h)["id"], VISA_OK, guardar=True)
    return client.get("/api/pagos/tarjetas", headers=h).json()[0]["id"]


def _avisos(client, h):
    return [n for n in client.get("/api/notificaciones", headers=h).json() if n["tipo"] == "OPERACION_OFFLINE"]


def _pedido_de(db, referencia):
    return db.execute(text("SELECT id, estado, total FROM pedidos WHERE codigo = :c"), {"c": referencia}).one()


def test_01_con_stock_la_compra_se_cobra_con_la_tarjeta_guardada_y_queda_confirmada(inv, mundo, client, db):
    stock_listo(inv, mundo)
    tarjeta = _tarjeta_guardada(client, inv)
    antes = existencias(client, inv.h_enc_centro, inv.v_sm_rojo)
    r = sincronizar_ok(client, inv.h_cliente, _op_compra(inv, 2, tarjeta))[0]
    assert r["estado"] == "CONFIRMADA" and r["mensaje"] == MSG_COBRADA
    assert r["referencia"] and r["comprobante"].startswith(f"CMP-{inv.centro.id:03d}-")
    pedido = _pedido_de(db, r["referencia"])
    assert (pedido[1], str(pedido[2])) == ("PAGADO", "200.00")
    pago = db.execute(text("SELECT metodo, estado, monto, tarjeta_ultimos4 FROM pagos WHERE pedido_id = :p"), {"p": pedido[0]}).one()
    assert (pago[0], pago[1], str(pago[2]), pago[3]) == ("TARJETA", "APROBADO", "200.00", "4242")
    despues = existencias(client, inv.h_enc_centro, inv.v_sm_rojo)
    assert despues["vendida"] == antes["vendida"] + 2 and despues["disponible"] == antes["disponible"] - 2  # el stock se descontó al cobrar
    aviso = _avisos(client, inv.h_cliente)[0]
    assert aviso["titulo"] == "Su compra fue cobrada y confirmada" and r["referencia"] in aviso["mensaje"] and r["comprobante"] in aviso["mensaje"]


def test_02_sin_stock_queda_en_conflicto_sin_cobrar_nada(inv, mundo, client, db):
    stock_listo(inv, mundo, centro=1)
    tarjeta = _tarjeta_guardada(client, inv)
    r = sincronizar_ok(client, inv.h_cliente, _op_compra(inv, 5, tarjeta, 500))[0]
    assert r["estado"] == "EN_CONFLICTO" and r["mensaje"] == MSG_AGOTADA and r["referencia"] is None
    assert contar(db, "pagos") == 1 and contar(db, "pedidos", estado="PENDIENTE_PAGO") == 0  # solo el pago de la tarjeta guardada de antes
    assert _avisos(client, inv.h_cliente)[0]["mensaje"].endswith("no se pudo realizar porque la prenda se agotó. No se le cobró nada.")


def test_03_reenviar_la_misma_operacion_no_cobra_dos_veces(inv, mundo, client, db):
    stock_listo(inv, mundo)
    tarjeta = _tarjeta_guardada(client, inv)
    op = _op_compra(inv, 1, tarjeta)
    primera = sincronizar_ok(client, inv.h_cliente, op)[0]
    pagos = contar(db, "pagos")
    segunda = sincronizar_ok(client, inv.h_cliente, op)[0]
    assert segunda["ya_procesada"] is True and (segunda["estado"], segunda["referencia"], segunda["comprobante"]) == (primera["estado"], primera["referencia"], primera["comprobante"])
    assert contar(db, "pagos") == pagos and contar(db, "pedidos", estado="PAGADO") == 2  # la compra en línea de la tarjeta + esta, una sola vez


def test_04_la_tarjeta_de_otro_cliente_se_rechaza_sin_crear_nada(inv, mundo, datos, client, db):
    stock_listo(inv, mundo)
    otro = datos.usuario(mundo.a, "Cliente", email="otro@tienda.com")
    h_otro = datos.login(otro, mundo.a)
    tarjeta_ajena = _tarjeta_guardada(client, inv, h_otro)
    r = sincronizar_ok(client, inv.h_cliente, _op_compra(inv, 1, tarjeta_ajena))[0]
    assert r["estado"] == "RECHAZADA" and r["mensaje"] == "Tarjeta no encontrada."
    assert contar(db, "pedidos", estado="PENDIENTE_PAGO") == 0 and contar(db, "pagos", estado="APROBADO") == 1  # solo el pago del otro cliente


def test_05_si_el_banco_rechaza_el_pedido_queda_por_pagar_con_su_aviso(inv, mundo, client, db):
    stock_listo(inv, mundo)
    tarjeta = _tarjeta_guardada(client, inv)
    db.execute(text("UPDATE tarjetas_guardadas SET escenario = 'FONDOS_INSUFICIENTES' WHERE id = :t"), {"t": tarjeta})
    db.commit()
    r = sincronizar_ok(client, inv.h_cliente, _op_compra(inv, 1, tarjeta))[0]
    assert r["estado"] == "CONFIRMADA" and r["mensaje"] == MSG_NO_COBRADA and r["comprobante"] is None
    pedido = _pedido_de(db, r["referencia"])
    assert pedido[1] == "PENDIENTE_PAGO"  # como cualquier pedido por pagar: se completa desde «Mis compras»
    assert db.execute(text("SELECT estado FROM pagos WHERE pedido_id = :p"), {"p": pedido[0]}).scalar() == "RECHAZADO"
    aviso = _avisos(client, inv.h_cliente)[0]
    assert aviso["titulo"] == "No pudimos cobrar su tarjeta" and "complete el pago desde Mis compras" in aviso["mensaje"]


def test_06_si_el_precio_cambio_no_se_cobra_y_el_cliente_confirma_el_nuevo_total(inv, mundo, client, db):
    stock_listo(inv, mundo)
    tarjeta = _tarjeta_guardada(client, inv)
    pagos = contar(db, "pagos")
    r = sincronizar_ok(client, inv.h_cliente, _op_compra(inv, 1, tarjeta, 90))[0]  # autorizó Bs 90 pero ahora vale Bs 100
    assert r["estado"] == "EN_CONFLICTO" and r["mensaje"] == MSG_PRECIO and r["referencia"] is None
    assert r["detalle"] == {"precios": [{"total_autorizado": "90.00", "total_actual": "100.00"}]}
    assert contar(db, "pagos") == pagos and contar(db, "pedidos", estado="PENDIENTE_PAGO") == 0
    aviso = _avisos(client, inv.h_cliente)[0]
    assert aviso["titulo"] == "El precio de su compra cambió" and MSG_PRECIO in aviso["mensaje"] and "no se le cobró nada" in aviso["mensaje"]


def test_07_nunca_viajan_datos_de_tarjeta_en_la_operacion(inv, mundo, client, db):
    stock_listo(inv, mundo)
    for dato in ({"numero": "4242 4242 4242 4242"}, {"cvc": "123"}, {"tarjeta": {"numero": "4242"}}, {"exp_mes": 12}):
        r = sincronizar_ok(client, inv.h_cliente, _op_compra(inv, 1, **dato))[0]
        assert r["estado"] == "RECHAZADA" and r["mensaje"] == "La operación no tiene el formato esperado."
    assert contar(db, "pedidos", estado="PENDIENTE_PAGO") == 0
    assert db.execute(text("SELECT count(*) FROM operaciones_offline WHERE payload::text ILIKE '%4242 4242%' OR payload::text ILIKE '%cvc%'")).scalar() == 0  # ni rastro en la cola


def test_08_una_compra_sin_tarjeta_sigue_como_antes_por_pagar(inv, mundo, client, db):
    stock_listo(inv, mundo)
    r = sincronizar_ok(client, inv.h_cliente, _op_compra(inv, 1))[0]
    assert r["estado"] == "CONFIRMADA" and r["mensaje"] == "Operación confirmada." and r["comprobante"] is None
    assert _pedido_de(db, r["referencia"])[1] == "PENDIENTE_PAGO"
    assert _avisos(client, inv.h_cliente)[0]["titulo"] == "Su compra está lista para pagar"


def test_09_falta_el_total_autorizado(inv, mundo, client):
    stock_listo(inv, mundo)
    tarjeta = _tarjeta_guardada(client, inv)
    op = _op_compra(inv, 1, tarjeta)
    del op["payload"]["total_autorizado"]
    r = sincronizar(client, inv.h_cliente, op).json()["resultados"][0]
    assert r["estado"] == "RECHAZADA" and r["mensaje"] == "La operación no tiene el formato esperado."


# ---------------- con Stripe (doble en memoria): el servidor confirma fuera de sesión y usa el operacion_id como clave de idempotencia ----------------
@pytest.fixture
def con_stripe(monkeypatch, inv, mundo, db, client):
    stripe = StripeFalso()
    monkeypatch.setattr(servicio_pago, "obtener_pasarela", lambda: PasarelaStripe("sk_test_falsa", "pk_test_falsa", sdk=stripe))
    cliente_id = db.execute(text("SELECT id FROM usuarios WHERE empresa_id = :e AND email = 'cliente@tienda.com'"), {"e": mundo.a.id}).scalar()
    tarjeta = TarjetaGuardada(empresa_id=mundo.a.id, cliente_id=cliente_id, proveedor="STRIPE", referencia="pm_guardada", marca="Visa", ultimos4="4242", exp_mes=12, exp_anio=2099)
    db.add(tarjeta)
    db.commit()
    stock_listo(inv, mundo)
    return stripe, tarjeta.id


def test_10_con_stripe_el_servidor_confirma_la_tarjeta_guardada_fuera_de_sesion(con_stripe, inv, client, db):
    stripe, tarjeta = con_stripe
    op = _op_compra(inv, 1, tarjeta)
    r = sincronizar_ok(client, inv.h_cliente, op)[0]
    assert r["estado"] == "CONFIRMADA" and r["mensaje"] == MSG_COBRADA and r["comprobante"]
    crear = stripe.hizo("crear")[0][1]
    assert (crear["amount"], crear["currency"], crear["payment_method"], crear["customer"]) == (10000, "bob", "pm_guardada", "cus_prueba")
    assert crear["confirm"] is True and crear["off_session"] is True and crear["capture_method"] == "manual"
    assert crear["idempotency_key"] == op["id"]  # la misma operación nunca cobra dos veces
    assert len(stripe.hizo("capturar")) == 1
    sincronizar_ok(client, inv.h_cliente, op)  # reenvío: no vuelve a hablar con Stripe
    assert len(stripe.hizo("crear")) == 1 and len(stripe.hizo("capturar")) == 1


def test_11_con_stripe_si_el_banco_rechaza_la_compra_queda_por_pagar(con_stripe, inv, client, db):
    stripe, tarjeta = con_stripe
    stripe.rechazar_fuera_de_sesion = "authentication_required"  # por ejemplo, la tarjeta pide 3D Secure
    r = sincronizar_ok(client, inv.h_cliente, _op_compra(inv, 1, tarjeta))[0]
    assert r["estado"] == "CONFIRMADA" and r["mensaje"] == MSG_NO_COBRADA and r["comprobante"] is None
    assert _pedido_de(db, r["referencia"])[1] == "PENDIENTE_PAGO" and stripe.hizo("capturar") == []
    assert _avisos(client, inv.h_cliente)[0]["titulo"] == "No pudimos cobrar su tarjeta"


def test_12_una_compra_cobrada_asi_se_devuelve_a_la_tarjeta_con_el_flujo_de_devoluciones(inv, mundo, client, db):
    from tests.devoluciones_util import devolver_ok

    stock_listo(inv, mundo)
    tarjeta = _tarjeta_guardada(client, inv)
    r = sincronizar_ok(client, inv.h_cliente, _op_compra(inv, 2, tarjeta))[0]
    assert r["mensaje"] == MSG_COBRADA
    pedido = client.get(f"/api/compras/{_pedido_de(db, r['referencia'])[0]}", headers=inv.h_cliente).json()
    d = devolver_ok(client, inv.h_cajero, r["comprobante"], [(pedido["items"][0], 1)])  # CU-41: devuelve una de las dos prendas
    assert (d["tipo"], d["medio_reembolso"], d["reembolso"]) == ("DEVOLUCION", "TARJETA", "100.00")  # vuelve a la misma tarjeta
    assert any("Bs 100.00" in a["mensaje"] for a in client.get("/api/notificaciones", headers=inv.h_cliente).json() if a["tipo"] != "OPERACION_OFFLINE")  # el cliente recibe el aviso con el monto

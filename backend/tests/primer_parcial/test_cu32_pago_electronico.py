"""CU-32 Procesar pago electrónico — pasos de la ficha (5.2.1), tarjetas guardadas y pago rechazado (pasarela simulada)."""
from sqlalchemy import text

from tests.catalogo_util import cabecera_cliente, entrar
from tests.compras_util import (
    CVC_MALO, MASTERCARD_OK, MOTIVO_BANCO, MSG_RECHAZO, RECHAZADA, REAL_NO_DE_PRUEBA, SIN_FONDOS, TIMEOUT, VENCIDA, VISA_OK,
    agregar_ok, checkout_ok, existencias, iniciar, pagar, stock_listo, tarjeta,
)


def _pedido(inv, mundo, client, cantidad=2):
    stock_listo(inv, mundo)
    agregar_ok(client, inv.h_cliente, inv.v_sm_rojo, inv.centro, cantidad)
    return checkout_ok(client, inv.h_cliente)


def test_01_enviar_el_payload_consolida_el_monto_del_pedido(inv, mundo, client):
    p = _pedido(inv, mundo, client)
    r = iniciar(client, inv.h_cliente, p["id"])
    assert r.status_code == 201
    i = r.json()
    assert (i["modo"], i["monto"], i["moneda"], i["monto_pasarela"], i["moneda_pasarela"]) == ("simulado", "200.00", "BOB", 28.74, "USD")  # 200 / 6,96
    assert i["client_secret"] is None and i["publishable_key"] is None  # sin claves de Stripe: pasarela simulada
    estado = client.get(f"/api/pagos/{i['pago_id']}", headers=inv.h_cliente).json()
    assert estado["pago"]["estado"] == "PENDIENTE" and estado["pago"]["monto"] == "200.00" and estado["aprobado"] is False


def test_02_pago_con_fondos_suficientes_queda_aprobado(inv, mundo, client):
    p = _pedido(inv, mundo, client)
    r = pagar(client, inv.h_cliente, p["id"], VISA_OK)
    assert r.status_code == 200
    res = r.json()
    assert (res["aprobado"], res["pendiente"], res["mensaje"]) == (True, False, "Pago aprobado.")
    assert (res["pago"]["estado"], res["pago"]["tarjeta_marca"], res["pago"]["tarjeta_ultimos4"]) == ("APROBADO", "Visa", "4242")
    assert res["pedido"]["estado"] == "PAGADO"
    r = pagar(client, inv.h_cliente, checkout_ok_aparte(inv, mundo, client), MASTERCARD_OK)
    assert r.json()["pago"]["tarjeta_marca"] == "Mastercard"


def checkout_ok_aparte(inv, mundo, client):
    agregar_ok(client, inv.h_cliente, inv.v_sm_rojo, inv.centro, 1)
    return checkout_ok(client, inv.h_cliente)["id"]


def test_03_fondos_insuficientes_muestra_transaccion_denegada(inv, mundo, client):
    p = _pedido(inv, mundo, client)
    r = pagar(client, inv.h_cliente, p["id"], SIN_FONDOS)
    assert r.status_code == 402
    assert r.json()["motivo"] == MOTIVO_BANCO == "Transacción denegada por su banco"
    assert r.json()["detail"] == MSG_RECHAZO


def test_04_el_estado_del_pedido_refleja_el_resultado(inv, mundo, client):
    p = _pedido(inv, mundo, client)
    r = pagar(client, inv.h_cliente, p["id"], SIN_FONDOS)
    pago = client.get(f"/api/pagos/{r.json()['pago_id']}", headers=inv.h_cliente).json()
    assert (pago["pago"]["estado"], pago["pedido"]["estado"], pago["pago"]["motivo"]) == ("RECHAZADO", "PENDIENTE_PAGO", MOTIVO_BANCO)
    r = pagar(client, inv.h_cliente, p["id"], VISA_OK)  # con otra tarjeta el mismo pedido se puede pagar
    assert r.json()["pedido"]["estado"] == "PAGADO"
    estados = [g["estado"] for g in client.get(f"/api/compras/{p['id']}", headers=inv.h_cliente).json()["pagos"]]
    assert estados == ["RECHAZADO", "APROBADO"]  # el intento fallido queda registrado


def test_05_timeout_deja_el_pedido_pendiente_de_confirmacion_y_se_concilia(inv, mundo, client):
    p = _pedido(inv, mundo, client)
    r = pagar(client, inv.h_cliente, p["id"], TIMEOUT)
    assert r.status_code == 200
    res = r.json()
    assert (res["aprobado"], res["pendiente"], res["pago"]["estado"], res["pedido"]["estado"]) == (False, True, "PENDIENTE_CONFIRMACION", "PENDIENTE_CONFIRMACION")
    assert "Pendiente de confirmación" in res["mensaje"]
    assert existencias(client, inv.h_enc_centro, inv.v_sm_rojo)["vendida"] == 0  # mientras no se confirme, no se descuenta
    r = client.post(f"/api/pagos/{res['pago']['id']}/reconciliar", headers=inv.h_cliente)  # conciliación posterior
    assert r.status_code == 200 and r.json()["aprobado"] is True and r.json()["pedido"]["estado"] == "PAGADO"
    f = existencias(client, inv.h_enc_centro, inv.v_sm_rojo)
    assert (f["disponible"], f["vendida"]) == (8, 2)
    assert client.post(f"/api/pagos/{res['pago']['id']}/reconciliar", headers=inv.h_cliente).json()["aprobado"] is True  # no se aplica dos veces
    assert existencias(client, inv.h_enc_centro, inv.v_sm_rojo)["vendida"] == 2


def test_06_otras_causas_de_rechazo(inv, mundo, client):
    p = _pedido(inv, mundo, client)
    casos = [(RECHAZADA, MOTIVO_BANCO, {}), (VENCIDA, "Su tarjeta está vencida.", {}), (CVC_MALO, "El código de seguridad (CVC) es incorrecto.", {}),
             (VISA_OK, "Su tarjeta está vencida.", {"mes": 1, "anio": 2020}),  # una tarjeta buena con fecha pasada también se rechaza
             (REAL_NO_DE_PRUEBA, "Este entorno solo admite tarjetas de prueba.", {})]
    for numero, motivo, extra in casos:
        r = pagar(client, inv.h_cliente, p["id"], numero, **extra)
        assert r.status_code == 402 and r.json()["motivo"] == motivo and r.json()["detail"] == MSG_RECHAZO, (numero, r.text)
    assert existencias(client, inv.h_enc_centro, inv.v_sm_rojo)["vendida"] == 0


def test_07_datos_de_tarjeta_invalidos_no_son_un_rechazo(inv, mundo, client):
    p = _pedido(inv, mundo, client)
    pago_id = iniciar(client, inv.h_cliente, p["id"]).json()["pago_id"]
    url = f"/api/pagos/{pago_id}/confirmar"
    r = client.post(url, json={"tarjeta": tarjeta("1234 5678 9012 3456")}, headers=inv.h_cliente)
    assert r.status_code == 422 and r.json()["detail"] == "El número de la tarjeta no es válido."
    r = client.post(url, json={"tarjeta": tarjeta(cvc="12")}, headers=inv.h_cliente)
    assert r.status_code == 422 and "CVC" in r.json()["detail"]
    assert client.post(url, json={}, headers=inv.h_cliente).json()["detail"] == "Ingrese los datos de la tarjeta."
    assert client.get(f"/api/pagos/{pago_id}", headers=inv.h_cliente).json()["pago"]["estado"] == "PENDIENTE"  # sigue pudiendo pagarse
    assert client.post(url, json={"tarjeta": tarjeta()}, headers=inv.h_cliente).json()["aprobado"] is True


def test_08_guardar_la_tarjeta_para_la_siguiente_compra(inv, mundo, client):
    p = _pedido(inv, mundo, client)
    assert client.get("/api/pagos/tarjetas", headers=inv.h_cliente).json() == []
    pagar(client, inv.h_cliente, p["id"], VISA_OK, guardar=True)
    tarjetas = client.get("/api/pagos/tarjetas", headers=inv.h_cliente).json()
    assert [(t["marca"], t["ultimos4"], t["exp_mes"], t["exp_anio"]) for t in tarjetas] == [("Visa", "4242", 12, 2099)]
    # segunda compra: se paga con la tarjeta guardada, sin volver a escribir sus datos
    agregar_ok(client, inv.h_cliente, inv.v_sm_rojo, inv.centro, 1)
    p2 = checkout_ok(client, inv.h_cliente)
    i = iniciar(client, inv.h_cliente, p2["id"], guardada=tarjetas[0]["id"]).json()
    assert i["tarjeta_guardada"]["ultimos4"] == "4242"
    r = client.post(f"/api/pagos/{i['pago_id']}/confirmar", json={}, headers=inv.h_cliente)
    assert r.status_code == 200 and r.json()["aprobado"] is True and r.json()["pago"]["tarjeta_ultimos4"] == "4242"
    assert len(client.get("/api/pagos/tarjetas", headers=inv.h_cliente).json()) == 1  # no se duplica


def test_09_una_tarjeta_guardada_conserva_su_resultado(inv, mundo, client):
    p = _pedido(inv, mundo, client)
    pagar(client, inv.h_cliente, p["id"], VISA_OK, guardar=True)
    agregar_ok(client, inv.h_cliente, inv.v_sm_rojo, inv.centro, 1)
    # una tarjeta rechazada no se guarda
    p2 = checkout_ok(client, inv.h_cliente)
    pagar(client, inv.h_cliente, p2["id"], SIN_FONDOS, guardar=True)
    assert [t["ultimos4"] for t in client.get("/api/pagos/tarjetas", headers=inv.h_cliente).json()] == ["4242"]


def test_10_eliminar_una_tarjeta_guardada(inv, mundo, client):
    p = _pedido(inv, mundo, client)
    pagar(client, inv.h_cliente, p["id"], VISA_OK, guardar=True)
    tid = client.get("/api/pagos/tarjetas", headers=inv.h_cliente).json()[0]["id"]
    assert client.delete(f"/api/pagos/tarjetas/{tid}", headers=inv.h_cliente).status_code == 204
    assert client.get("/api/pagos/tarjetas", headers=inv.h_cliente).json() == []
    assert client.delete(f"/api/pagos/tarjetas/{tid}", headers=inv.h_cliente).status_code == 404


def test_11_nunca_se_guarda_el_numero_completo_ni_el_cvc(inv, mundo, client, db):
    p = _pedido(inv, mundo, client)
    pagar(client, inv.h_cliente, p["id"], VISA_OK, guardar=True, cvc="987")
    for tabla in ("pagos", "tarjetas_guardadas", "pedidos"):
        for fila in db.execute(text(f"SELECT * FROM {tabla}")).mappings():
            texto = " ".join(str(v) for v in fila.values())
            assert "4242424242424242" not in texto and "4242 4242 4242 4242" not in texto and "987" not in texto.split(), (tabla, texto)


def test_12_las_tarjetas_guardadas_son_del_cliente_y_de_su_empresa(inv, mundo, tienda_b, datos, client):
    p = _pedido(inv, mundo, client)
    pagar(client, inv.h_cliente, p["id"], VISA_OK, guardar=True)
    tid = client.get("/api/pagos/tarjetas", headers=inv.h_cliente).json()[0]["id"]
    datos.usuario(mundo.a, "Cliente", email="otro@a.com")
    for h in (entrar(client, mundo.a, "otro@a.com"), cabecera_cliente(datos, mundo.b)):
        assert client.get("/api/pagos/tarjetas", headers=h).json() == []
        assert client.delete(f"/api/pagos/tarjetas/{tid}", headers=h).status_code == 404


def test_13_un_pago_de_otro_cliente_o_empresa_no_existe(inv, mundo, tienda_b, datos, client):
    p = _pedido(inv, mundo, client)
    pago_id = iniciar(client, inv.h_cliente, p["id"]).json()["pago_id"]
    datos.usuario(mundo.a, "Cliente", email="otro@a.com")
    for h in (entrar(client, mundo.a, "otro@a.com"), cabecera_cliente(datos, mundo.b)):
        assert client.get(f"/api/pagos/{pago_id}", headers=h).status_code == 404
        assert client.post(f"/api/pagos/{pago_id}/confirmar", json={"tarjeta": tarjeta()}, headers=h).status_code == 404
        assert client.post(f"/api/pagos/{pago_id}/reconciliar", headers=h).status_code == 404


def test_14_un_pago_rechazado_no_se_puede_confirmar_otra_vez(inv, mundo, client):
    p = _pedido(inv, mundo, client)
    pago_id = iniciar(client, inv.h_cliente, p["id"]).json()["pago_id"]
    url = f"/api/pagos/{pago_id}/confirmar"
    assert client.post(url, json={"tarjeta": tarjeta(SIN_FONDOS)}, headers=inv.h_cliente).status_code == 402
    r = client.post(url, json={"tarjeta": tarjeta(VISA_OK)}, headers=inv.h_cliente)
    assert r.status_code == 409 and r.json()["detail"] == "Este pago ya fue procesado. Inicie un nuevo pago."
    r = client.post(f"/api/pagos/{pago_id}/reconciliar", headers=inv.h_cliente)
    assert r.status_code == 409 and r.json()["detail"] == "Este pago no está pendiente de confirmación."


def test_15_configuracion_de_pago_y_tarjetas_de_prueba(inv, client):
    c = client.get("/api/pagos/config", headers=inv.h_cliente).json()
    assert c["modo"] == "simulado" and c["publishable_key"] is None and c["moneda_pasarela"] == "USD"
    assert {t["numero"] for t in c["tarjetas_prueba"]} >= {"4242 4242 4242 4242", "4000 0000 0000 9995", "4000 0000 0000 0119"}


def test_16_quien_puede_pagar_una_compra_digital(inv, mundo, client):
    p = _pedido(inv, mundo, client)
    for h in (inv.h_admin, inv.h_prov):  # roles que no cobran
        assert iniciar(client, h, p["id"]).status_code == 403
        assert client.get("/api/pagos/config", headers=h).status_code == 403
    for h in (inv.h_enc_centro, inv.h_cajero):  # la caja solo cobra ventas presenciales: una compra digital no es suya
        assert iniciar(client, h, p["id"]).status_code == 404
    for h in (inv.h_enc_centro, inv.h_cajero, inv.h_admin):  # las tarjetas guardadas son solo del cliente
        assert client.get("/api/pagos/tarjetas", headers=h).status_code == 403


def test_17_el_pago_online_es_siempre_con_tarjeta(inv, mundo, client, db):
    from tests.caja_util import cobrar
    p = _pedido(inv, mundo, client)
    # el efectivo no existe para una compra digital: caja no la cobra, solo el cliente paga con tarjeta por la pasarela
    assert cobrar(client, inv.h_cajero, p["id"], "EFECTIVO", 500).status_code == 404
    assert pagar(client, inv.h_cliente, p["id"]).json()["aprobado"] is True
    pagos = db.execute(text("SELECT DISTINCT p.metodo FROM pagos p JOIN pedidos o ON o.id = p.pedido_id WHERE o.canal = 'DIGITAL'")).scalars().all()
    assert pagos == ["TARJETA"]

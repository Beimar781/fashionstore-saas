"""CU-41 Cambios de prendas — sujetos a disponibilidad, con diferencia a cobrar o a reembolsar (RN15)."""
from tests.compras_util import existencias, stock_listo
from tests.devoluciones_util import devolver, devolver_ok, venta_en_caja


def _cambio(client, h, p, nueva, cantidad=1, devueltas=1, nueva_cantidad=None, **extra):
    return devolver(client, h, p["comprobante_numero"], [(p["items"][0], devueltas)], tipo="CAMBIO", motivo="Quiero otra talla", nuevos=[(nueva, nueva_cantidad or cantidad)], **extra)


def test_01_cambio_por_una_prenda_del_mismo_valor(inv, mundo, client):
    stock_listo(inv, mundo)
    p = venta_en_caja(client, inv, (inv.v_sm_rojo, 1))  # camisa S Rojo, Bs 100
    r = _cambio(client, inv.h_cajero, p, inv.var[("M", "Rojo")])
    assert r.status_code == 201
    d = r.json()
    assert (d["tipo"], d["monto_devuelto"], d["monto_nuevo"], d["reembolso"], d["cobro_adicional"], d["medio_reembolso"], d["medio_cobro"]) == (
        "CAMBIO", "100.00", "100.00", "0.00", "0.00", None, None)
    assert sorted((i["sentido"], i["talla"]) for i in d["items"]) == [("DEVUELTA", "S"), ("ENTREGADA", "M")]
    chica = existencias(client, inv.h_enc_centro, inv.v_sm_rojo)
    grande = existencias(client, inv.h_enc_centro, inv.var[("M", "Rojo")])
    assert (chica["disponible"], chica["vendida"]) == (10, 0)  # la devuelta vuelve al inventario
    assert (grande["disponible"], grande["vendida"]) == (9, 1)  # la nueva se descuenta
    movs = client.get("/api/inventario/movimientos", headers=inv.h_enc_centro).json()["items"]
    assert {(m["tipo"], m["referencia_tipo"]) for m in movs if m["referencia_tipo"] == "DEVOLUCION" and m["referencia_id"] == d["id"]} == {("DEVOLUCION", "DEVOLUCION"), ("VENTA", "DEVOLUCION")}


def test_02_si_la_prenda_nueva_vale_mas_el_cliente_paga_la_diferencia(inv, mundo, client):
    stock_listo(inv, mundo)
    caro = inv.producto_caro if hasattr(inv, "producto_caro") else None
    from tests.catalogo_util import por_variante, talla_id
    jean = inv.producto("Jean", inv.pantalones["id"], inv.col["id"], [talla_id(inv.numerico, "30")], [inv.rojo["id"]], precio="180.00")
    v_jean = por_variante(jean)[("30", "Rojo")]
    inv.stock(mundo.a.id, inv.centro.id, v_jean["id"], 5)
    p = venta_en_caja(client, inv, (inv.v_sm_rojo, 1))  # Bs 100 → jean de Bs 180: diferencia de Bs 80
    r = _cambio(client, inv.h_cajero, p, v_jean)
    assert r.status_code == 422 and r.json()["detail"] == "El cambio tiene una diferencia de Bs 80.00 a cobrar: indique cómo paga el cliente."
    r = _cambio(client, inv.h_cajero, p, v_jean, cobro={"metodo": "EFECTIVO", "monto_recibido": "50"})
    assert r.status_code == 422 and r.json()["detail"] == "El monto recibido es menor a la diferencia a cobrar."
    assert existencias(client, inv.h_enc_centro, v_jean)["vendida"] == 0  # los errores no mueven nada
    d = _cambio(client, inv.h_cajero, p, v_jean, cobro={"metodo": "EFECTIVO", "monto_recibido": "100"}).json()
    assert (d["cobro_adicional"], d["medio_cobro"], d["monto_recibido"], d["cambio_entregado"], d["reembolso"]) == ("80.00", "EFECTIVO", "100.00", "20.00", "0.00")
    p2 = venta_en_caja(client, inv, (inv.v_sm_rojo, 1))
    assert _cambio(client, inv.h_cajero, p2, v_jean, cobro={"metodo": "QR"}).status_code == 422  # la diferencia solo se paga en efectivo


def test_03_si_la_prenda_nueva_vale_menos_se_reembolsa_la_diferencia(inv, mundo, client):
    from tests.catalogo_util import por_variante, talla_id
    stock_listo(inv, mundo)
    barata = inv.producto("Polo", inv.camisas["id"], inv.col["id"], [talla_id(inv.alfa, "M")], [inv.rojo["id"]], precio="70.00")
    v_polo = por_variante(barata)[("M", "Rojo")]
    inv.stock(mundo.a.id, inv.centro.id, v_polo["id"], 5)
    p = venta_en_caja(client, inv, (inv.v_sm_rojo, 1))  # Bs 100 → polo de Bs 70
    d = _cambio(client, inv.h_cajero, p, v_polo).json()
    assert (d["monto_devuelto"], d["monto_nuevo"], d["reembolso"], d["cobro_adicional"], d["medio_reembolso"]) == ("100.00", "70.00", "30.00", "0.00", "EFECTIVO")


def test_04_el_cambio_esta_sujeto_a_disponibilidad(inv, mundo, client):
    stock_listo(inv, mundo)
    p = venta_en_caja(client, inv, (inv.v_sm_rojo, 1))
    client.post("/api/inventario/sucursal/movimientos", json={"variante_id": inv.var[("M", "Rojo")]["id"], "tipo": "AJUSTE_SALIDA", "cantidad": 10, "nota": "Agotada"}, headers=inv.h_enc_centro)
    r = _cambio(client, inv.h_cajero, p, inv.var[("M", "Rojo")])
    assert r.status_code == 409
    assert r.json()["detail"] == "No hay stock suficiente en Centro para el cambio: Camisa Oxford (M, Rojo): solicitadas 1, disponibles 0."
    f = existencias(client, inv.h_enc_centro, inv.v_sm_rojo)
    assert (f["disponible"], f["vendida"]) == (9, 1)  # nada a medias: la devuelta no reingresó
    assert client.get("/api/devoluciones", headers=inv.h_cajero).json() == []
    assert devolver_ok(client, inv.h_cajero, p["comprobante_numero"], [(p["items"][0], 1)])["tipo"] == "DEVOLUCION"  # la devolución simple sí se puede


def test_05_se_puede_cambiar_por_la_misma_prenda_que_se_devuelve(inv, mundo, client):
    stock_listo(inv, mundo, centro=1)
    p = venta_en_caja(client, inv, (inv.v_sm_rojo, 1))  # queda 0 de esa camisa
    assert existencias(client, inv.h_enc_centro, inv.v_sm_rojo)["disponible"] == 0
    r = _cambio(client, inv.h_cajero, p, inv.v_sm_rojo)  # la que vuelve alcanza para el cambio
    assert r.status_code == 201
    f = existencias(client, inv.h_enc_centro, inv.v_sm_rojo)
    assert (f["disponible"], f["vendida"]) == (0, 1)


def test_06_reglas_del_cambio(inv, mundo, client):
    stock_listo(inv, mundo)
    p = venta_en_caja(client, inv, (inv.v_sm_rojo, 1))
    c, linea = p["comprobante_numero"], p["items"][0]
    r = devolver(client, inv.h_cajero, c, [(linea, 1)], tipo="CAMBIO")
    assert r.status_code == 422 and r.json()["detail"] == "Un cambio requiere al menos una prenda nueva."
    r = devolver(client, inv.h_cajero, c, [(linea, 1)], nuevos=[(inv.var[("M", "Rojo")], 1)])  # tipo devolución con prendas nuevas
    assert r.status_code == 422 and r.json()["detail"] == "Una devolución no lleva prendas nuevas; registre un cambio."
    client.post(f"/api/productos/{inv.camisa['id']}/desactivar", headers=inv.h_admin)
    r = _cambio(client, inv.h_cajero, p, inv.var[("M", "Rojo")])
    assert r.status_code == 422 and r.json()["detail"] == "Una o más prendas del cambio ya no están disponibles en el catálogo."


def test_07_el_cambio_respeta_las_cantidades_ya_devueltas(inv, mundo, client):
    stock_listo(inv, mundo)
    p = venta_en_caja(client, inv, (inv.v_sm_rojo, 2))
    assert _cambio(client, inv.h_cajero, p, inv.var[("M", "Rojo")], devueltas=2).status_code == 201
    r = _cambio(client, inv.h_cajero, p, inv.var[("M", "Rojo")], devueltas=1)
    assert r.status_code == 409 and r.json()["detail"] == "Camisa Oxford (S, Rojo) ya fue devuelto por completo."


def test_08_el_cambio_aparece_en_el_reporte_de_la_sucursal(inv, mundo, client):
    from tests.catalogo_util import por_variante, talla_id
    stock_listo(inv, mundo)
    jean = inv.producto("Jean", inv.pantalones["id"], inv.col["id"], [talla_id(inv.numerico, "30")], [inv.rojo["id"]], precio="180.00")
    v_jean = por_variante(jean)[("30", "Rojo")]
    inv.stock(mundo.a.id, inv.centro.id, v_jean["id"], 5)
    p = venta_en_caja(client, inv, (inv.v_sm_rojo, 1))  # Bs 100
    _cambio(client, inv.h_cajero, p, v_jean, cobro={"metodo": "EFECTIVO", "monto_recibido": "80"})  # devuelve Bs 100, entrega Bs 180, paga Bs 80 en efectivo
    s = client.get("/api/reportes/sucursal/resumen", headers=inv.h_enc_centro).json()
    assert (s["total_vendido"], s["ventas_netas"]) == ("100.00", "180.00")  # 100 − 100 devueltos + 180 entregados
    assert (s["devoluciones"]["entregado_en_cambios"], s["devoluciones"]["cobrado_efectivo"]) == ("180.00", "80.00")
    assert s["efectivo_en_caja"] == "180.00"  # 100 cobrados + 80 de la diferencia


# ---- la diferencia se paga como el cliente prefiera: efectivo o tarjeta ----
def _jean(inv, mundo, precio="180.00"):
    from tests.catalogo_util import por_variante, talla_id
    jean = inv.producto("Jean", inv.pantalones["id"], inv.col["id"], [talla_id(inv.numerico, "30")], [inv.rojo["id"]], precio=precio)
    v = por_variante(jean)[("30", "Rojo")]
    inv.stock(mundo.a.id, inv.centro.id, v["id"], 5)
    return v


def _con_tarjeta(intento_id, numero=None):
    from tests.compras_util import VISA_OK
    return {"metodo": "TARJETA", "intento_id": intento_id, "tarjeta": {"numero": numero or VISA_OK, "mes": 12, "anio": 2099, "cvc": "123", "titular": "Cliente"}}


def _iniciar(client, inv, p, v_jean):
    from tests.devoluciones_util import iniciar_diferencia
    r = iniciar_diferencia(client, inv.h_cajero, p["comprobante_numero"], [(p["items"][0], 1)], [(v_jean, 1)])
    assert r.status_code == 201, r.text
    return r.json()


def test_09_la_diferencia_se_paga_con_tarjeta(inv, mundo, client, db):
    from sqlalchemy import text
    stock_listo(inv, mundo)
    v_jean = _jean(inv, mundo)
    p = venta_en_caja(client, inv, (inv.v_sm_rojo, 1))  # Bs 100 → jean de Bs 180: diferencia de Bs 80
    ini = _iniciar(client, inv, p, v_jean)
    assert (ini["monto"], ini["modo"], ini["moneda_pasarela"]) == ("80.00", "simulado", "USD") and ini["client_secret"] is None
    r = _cambio(client, inv.h_cajero, p, v_jean, cobro=_con_tarjeta(ini["pago_id"]))
    assert r.status_code == 201, r.text
    d = r.json()
    assert (d["cobro_adicional"], d["medio_cobro"], d["tarjeta_cobro"], d["monto_recibido"], d["reembolso"]) == ("80.00", "TARJETA", "Visa ****4242", None, "0.00")
    assert existencias(client, inv.h_enc_centro, v_jean)["vendida"] == 1 and existencias(client, inv.h_enc_centro, inv.v_sm_rojo)["disponible"] == 10
    assert db.execute(text("SELECT estado FROM intentos_diferencia WHERE id = :i"), {"i": ini["pago_id"]}).scalar() == "USADO"
    assert _cambio(client, inv.h_cajero, p, v_jean, cobro=_con_tarjeta(ini["pago_id"])).status_code == 409  # el mismo cobro no se usa dos veces
    s = client.get("/api/reportes/sucursal/resumen", headers=inv.h_enc_centro).json()
    assert (s["devoluciones"]["cobrado_tarjeta"], s["devoluciones"]["cobrado_efectivo"], s["efectivo_en_caja"]) == ("80.00", "0.00", "100.00")  # lo de la tarjeta no entra al cajón
    assert client.get(f"/api/devoluciones/{d['id']}/nota", headers=inv.h_cajero).status_code == 200


def test_10_tarjeta_rechazada_no_registra_el_cambio_y_se_reintenta(inv, mundo, client):
    from tests.compras_util import MSG_RECHAZO, SIN_FONDOS
    stock_listo(inv, mundo)
    v_jean = _jean(inv, mundo)
    p = venta_en_caja(client, inv, (inv.v_sm_rojo, 1))
    ini = _iniciar(client, inv, p, v_jean)
    r = _cambio(client, inv.h_cajero, p, v_jean, cobro=_con_tarjeta(ini["pago_id"], SIN_FONDOS))
    assert r.status_code == 402 and r.json()["detail"] == MSG_RECHAZO and r.json()["motivo"]
    assert existencias(client, inv.h_enc_centro, inv.v_sm_rojo)["vendida"] == 1 and existencias(client, inv.h_enc_centro, v_jean)["vendida"] == 0
    assert client.get("/api/devoluciones", headers=inv.h_cajero).json() == []
    assert _cambio(client, inv.h_cajero, p, v_jean, cobro=_con_tarjeta(ini["pago_id"])).status_code == 201  # con otra tarjeta sí


def test_11_si_se_agota_la_prenda_se_anula_la_autorizacion(inv, mundo, client, db, monkeypatch):
    from sqlalchemy import text
    from app.primer_parcial.ventas.cu32_pago_electronico.pasarela import PasarelaSimulada
    stock_listo(inv, mundo)
    v_jean = _jean(inv, mundo)
    p = venta_en_caja(client, inv, (inv.v_sm_rojo, 1))
    ini = _iniciar(client, inv, p, v_jean)
    client.post("/api/inventario/sucursal/movimientos", json={"variante_id": v_jean["id"], "tipo": "AJUSTE_SALIDA", "cantidad": 5, "nota": "Agotado"}, headers=inv.h_enc_centro)
    anuladas, capturadas = [], []
    monkeypatch.setattr(PasarelaSimulada, "cancelar", lambda self, ref: anuladas.append(ref))
    monkeypatch.setattr(PasarelaSimulada, "capturar", lambda self, ref: capturadas.append(ref))
    r = _cambio(client, inv.h_cajero, p, v_jean, cobro=_con_tarjeta(ini["pago_id"]))
    assert r.status_code == 409 and r.json()["detail"].startswith("No hay stock suficiente en Centro para el cambio")
    assert len(anuladas) == 1 and capturadas == []  # se anuló la autorización: no se cobró nada
    assert db.execute(text("SELECT estado FROM intentos_diferencia WHERE id = :i"), {"i": ini["pago_id"]}).scalar() == "CANCELADO"
    assert existencias(client, inv.h_enc_centro, inv.v_sm_rojo)["vendida"] == 1


def test_12_reglas_del_cobro_con_tarjeta(inv, mundo, client):
    from tests.devoluciones_util import iniciar_diferencia
    stock_listo(inv, mundo)
    v_jean = _jean(inv, mundo)
    p = venta_en_caja(client, inv, (inv.v_sm_rojo, 1))
    r = iniciar_diferencia(client, inv.h_cajero, p["comprobante_numero"], [(p["items"][0], 1)], [(inv.var[("M", "Rojo")], 1)])  # mismo valor: no hay diferencia
    assert r.status_code == 422 and r.json()["detail"] == "El cambio no tiene una diferencia a cobrar."
    r = _cambio(client, inv.h_cajero, p, v_jean, cobro={"metodo": "TARJETA"})
    assert r.status_code == 422 and r.json()["detail"] == "Inicie el cobro con tarjeta de la diferencia antes de registrar el cambio."
    ini = _iniciar(client, inv, p, v_jean)
    r = _cambio(client, inv.h_cajero, p, v_jean, cobro={"metodo": "TARJETA", "intento_id": ini["pago_id"]})  # sin datos de la tarjeta
    assert r.status_code == 422 and r.json()["detail"] == "Ingrese los datos de la tarjeta."
    assert _cambio(client, inv.h_cajero, p, v_jean, cobro=_con_tarjeta(99999)).status_code == 404
    otra = venta_en_caja(client, inv, (inv.v_sm_rojo, 1))
    r = _cambio(client, inv.h_cajero, otra, v_jean, cobro=_con_tarjeta(ini["pago_id"]))  # el cobro es de otra venta
    assert r.status_code == 404 and r.json()["detail"] == "Cobro de la diferencia no encontrado."
    r = _cambio(client, inv.h_cajero, p, v_jean, nueva_cantidad=2, cobro=_con_tarjeta(ini["pago_id"]))  # el monto ya no coincide
    assert r.status_code == 409 and r.json()["detail"] == "El cobro de la diferencia ya no coincide con el cambio. Inicie el cobro con tarjeta nuevamente."
    assert existencias(client, inv.h_enc_centro, v_jean)["vendida"] == 0
    for h in (inv.h_cliente, inv.h_admin):
        assert client.post("/api/devoluciones/diferencia", json={}, headers=h).status_code == 403


def test_13_con_stripe_la_tarjeta_la_confirma_el_navegador(inv, mundo, client, monkeypatch):
    from app.modules.ventas.cu41_devoluciones import service
    from app.primer_parcial.ventas.cu32_pago_electronico.pasarela import PasarelaStripe, centavos_pasarela
    from tests.stripe_falso import StripeFalso
    stock_listo(inv, mundo)
    v_jean = _jean(inv, mundo)
    falso = StripeFalso()
    stripe = PasarelaStripe("sk_test_falsa", "pk_test_falsa", sdk=falso)
    monkeypatch.setattr(service, "obtener_pasarela", lambda: stripe)
    monkeypatch.setattr(service, "pasarela_para", lambda proveedor: stripe if proveedor == "STRIPE" else None)
    p = venta_en_caja(client, inv, (inv.v_sm_rojo, 1))
    ini = _iniciar(client, inv, p, v_jean)
    assert ini["modo"] == "stripe" and ini["publishable_key"] == "pk_test_falsa" and ini["client_secret"]
    assert falso.hizo("crear")[0][1]["amount"] == centavos_pasarela(80) and falso.hizo("crear")[0][1]["capture_method"] == "manual"
    falso.rechazar("pi_1", "insufficient_funds")  # el navegador intentó y el banco lo rechazó
    r = _cambio(client, inv.h_cajero, p, v_jean, cobro={"metodo": "TARJETA", "intento_id": ini["pago_id"]})
    assert r.status_code == 402 and falso.hizo("capturar") == []
    falso.autorizar("pi_1")  # nuevo intento en el navegador: aprobado
    r = _cambio(client, inv.h_cajero, p, v_jean, cobro={"metodo": "TARJETA", "intento_id": ini["pago_id"]})
    assert r.status_code == 201 and r.json()["tarjeta_cobro"] == "Visa ****4242" and r.json()["medio_cobro"] == "TARJETA"
    assert falso.hizo("capturar") == [("capturar", "pi_1")]  # recién con el cambio registrado se cobra

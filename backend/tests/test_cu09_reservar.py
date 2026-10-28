"""CU-09 Realizar reserva de múltiples prendas — caja negra, reglas de stock y horario, y aislamiento entre empresas."""
from app.modules.sucursales.models import Sucursal
from tests.reservas_util import avisos, fila, reserva_ok, reservar


def _con_stock(inv, mundo, centro=10, norte=0):
    inv.stock(mundo.a.id, inv.centro.id, inv.v_sm_rojo["id"], centro)
    inv.stock(mundo.a.id, inv.centro.id, inv.var[("M", "Azul")]["id"], centro)
    if norte:
        inv.stock(mundo.a.id, inv.norte.id, inv.v_sm_rojo["id"], norte)


def test_01_reservar_varias_prendas_aparta_el_stock(inv, mundo, client):
    _con_stock(inv, mundo)
    r = reservar(client, inv.h_cliente, inv.centro, (inv.v_sm_rojo, 2), (inv.var[("M", "Azul")], 1), notas="Voy con mi hermana")
    assert r.status_code == 201
    res = r.json()
    assert res["estado"] == "PENDIENTE" and res["codigo"].startswith("RSV-") and len(res["codigo"]) == 12
    assert res["total_unidades"] == 3 and res["sucursal"] == "Centro" and res["puede_cancelar"] is True
    assert {(i["sku"], i["cantidad"], i["estado"]) for i in res["items"]} == {
        (inv.v_sm_rojo["sku"], 2, "RESERVADO"), (inv.var[("M", "Azul")]["sku"], 1, "RESERVADO")}
    f = fila(client, inv.h_enc_centro, inv.v_sm_rojo)
    assert (f["disponible"], f["reservada"]) == (8, 2)  # pasó de disponible a reservada, no se vendió


def test_02_el_movimiento_de_reserva_queda_en_la_bitacora(inv, mundo, client):
    _con_stock(inv, mundo)
    res = reserva_ok(client, inv.h_cliente, inv.centro, (inv.v_sm_rojo, 2))
    m = client.get("/api/inventario/movimientos", params={"tipo": "RESERVA"}, headers=inv.h_enc_centro).json()["items"][0]
    assert (m["cantidad"], m["referencia_tipo"], m["referencia_id"], m["nota"]) == (2, "RESERVA", res["id"], f"Reserva {res['codigo']}")


def test_03_horario_pasado_o_muy_lejano(inv, mundo, client):
    _con_stock(inv, mundo)
    r = reservar(client, inv.h_cliente, inv.centro, (inv.v_sm_rojo, 1), dias=-1)
    assert r.status_code == 422 and r.json()["detail"] == "El horario de la reserva debe ser posterior al momento actual."
    r = reservar(client, inv.h_cliente, inv.centro, (inv.v_sm_rojo, 1), dias=30)
    assert r.status_code == 422 and r.json()["detail"] == "La reserva no puede programarse con más de 14 días de anticipación."
    assert reservar(client, inv.h_cliente, inv.centro, (inv.v_sm_rojo, 1), dias=13, hora=10).status_code == 201


def test_04_horario_dentro_de_la_atencion_de_la_sucursal(inv, mundo, client, db):
    _con_stock(inv, mundo)
    db.query(Sucursal).filter_by(id=inv.centro.id).update({"horario": "Lun-Sáb 9:00-20:00"})
    db.commit()
    r = reservar(client, inv.h_cliente, inv.centro, (inv.v_sm_rojo, 1), hora=22)
    assert r.status_code == 422 and r.json()["detail"] == "El horario debe estar dentro del horario de atención de la sucursal (09:00 a 20:00)."
    assert reservar(client, inv.h_cliente, inv.centro, (inv.v_sm_rojo, 1), hora=7).status_code == 422
    assert reservar(client, inv.h_cliente, inv.centro, (inv.v_sm_rojo, 1), hora=18).status_code == 201


def test_05_sin_prendas_o_cantidad_invalida(inv, mundo, client):
    r = reservar(client, inv.h_cliente, inv.centro)
    assert r.status_code == 422 and r.json()["detail"] == "Seleccione al menos una prenda para reservar."
    assert reservar(client, inv.h_cliente, inv.centro, (inv.v_sm_rojo, 0)).status_code == 422
    assert reservar(client, inv.h_cliente, inv.centro, (inv.v_sm_rojo, 11)).status_code == 422


def test_06_stock_insuficiente_es_todo_o_nada(inv, mundo, client):
    _con_stock(inv, mundo, centro=3)
    r = reservar(client, inv.h_cliente, inv.centro, (inv.v_sm_rojo, 2), (inv.var[("M", "Azul")], 5))
    assert r.status_code == 409
    assert r.json()["detail"] == "No hay stock suficiente en Centro para: Camisa Oxford (M, Azul): solicitadas 5, disponibles 3."
    f = fila(client, inv.h_enc_centro, inv.v_sm_rojo)
    assert (f["disponible"], f["reservada"]) == (3, 0)  # la prenda que sí alcanzaba tampoco se apartó
    assert client.get("/api/reservas", headers=inv.h_cliente).json() == []


def test_07_el_stock_se_valida_en_la_sucursal_elegida(inv, mundo, client):
    _con_stock(inv, mundo, centro=0, norte=5)  # solo Norte tiene la camisa S Rojo
    assert reservar(client, inv.h_cliente, inv.centro, (inv.v_sm_rojo, 1)).status_code == 409
    assert reservar(client, inv.h_cliente, inv.norte, (inv.v_sm_rojo, 1)).status_code == 201
    assert fila(client, inv.h_enc_norte, inv.v_sm_rojo)["disponible"] == 4


def test_08_una_prenda_repetida_se_suma(inv, mundo, client):
    _con_stock(inv, mundo)
    res = reserva_ok(client, inv.h_cliente, inv.centro, (inv.v_sm_rojo, 2), (inv.v_sm_rojo, 3))
    assert len(res["items"]) == 1 and res["items"][0]["cantidad"] == 5


def test_09_prenda_retirada_del_catalogo(inv, mundo, client):
    _con_stock(inv, mundo)
    client.post(f"/api/productos/{inv.camisa['id']}/desactivar", headers=inv.h_admin)
    r = reservar(client, inv.h_cliente, inv.centro, (inv.v_sm_rojo, 1))
    assert r.status_code == 422 and r.json()["detail"] == "Una o más prendas ya no están disponibles en el catálogo."


def test_10_sucursal_inactiva_o_de_otra_empresa(inv, mundo, datos, client):
    _con_stock(inv, mundo)
    otra = datos.sucursal(mundo.b, "Sucursal de B")
    inactiva = datos.sucursal(mundo.a, "Cerrada", activa=False)
    for sucursal in (otra, inactiva):
        assert reservar(client, inv.h_cliente, sucursal, (inv.v_sm_rojo, 1)).status_code == 404


def test_11_solo_el_cliente_reserva(inv, mundo, client):
    _con_stock(inv, mundo)
    for h in (inv.h_enc_centro, inv.h_cajero, inv.h_admin, inv.h_prov):
        assert reservar(client, h, inv.centro, (inv.v_sm_rojo, 1)).status_code == 403
    assert client.post("/api/reservas", json={}).status_code == 401


def test_12_la_sucursal_recibe_el_aviso_y_el_cliente_su_confirmacion(inv, mundo, client):  # RF11
    _con_stock(inv, mundo)
    res = reserva_ok(client, inv.h_cliente, inv.centro, (inv.v_sm_rojo, 2))
    nuevo = next(n for n in avisos(client, inv.h_enc_centro) if n["tipo"] == "RESERVA_NUEVA")
    assert res["codigo"] in nuevo["titulo"] and "2 prenda(s)" in nuevo["mensaje"] and nuevo["referencia_id"] == res["id"]
    assert not any(n["tipo"] == "RESERVA_NUEVA" for n in avisos(client, inv.h_enc_norte))  # otra sucursal no se entera
    confirmacion = next(n for n in avisos(client, inv.h_cliente) if n["tipo"] == "RESERVA_CREADA")
    assert res["codigo"] in confirmacion["mensaje"]


def test_13_los_codigos_son_distintos(inv, mundo, client):
    _con_stock(inv, mundo)
    codigos = {reserva_ok(client, inv.h_cliente, inv.centro, (inv.v_sm_rojo, 1))["codigo"] for _ in range(4)}
    assert len(codigos) == 4


def test_14_aislamiento_entre_empresas(inv, mundo, tienda_b, datos, client):
    from tests.catalogo_util import cabecera_cliente, por_variante, talla_id
    _con_stock(inv, mundo)
    centro_b = datos.sucursal(mundo.b, "Centro B")
    camisa_b = tienda_b.producto("Camisa B", tienda_b.camisas["id"], tienda_b.col["id"], [talla_id(tienda_b.alfa, "S")], [tienda_b.rojo["id"]])
    v_b = por_variante(camisa_b)[("S", "Rojo")]
    tienda_b.stock(mundo.b.id, centro_b.id, v_b["id"], 5)
    h_cli_b = cabecera_cliente(datos, mundo.b)
    # el cliente de B no reserva ni la sucursal ni la prenda de A
    assert reservar(client, h_cli_b, inv.centro, (v_b, 1)).status_code == 404
    assert reservar(client, h_cli_b, centro_b, (inv.v_sm_rojo, 1)).status_code == 422
    assert reservar(client, h_cli_b, centro_b, (v_b, 1)).status_code == 201
    assert client.get("/api/reservas", headers=inv.h_cliente).json() == []  # y la reserva de B no aparece en A


def test_15_una_sucursal_con_reservas_activas_no_se_desactiva(inv, mundo, client):  # gancho de CU-14
    _con_stock(inv, mundo)
    res = reserva_ok(client, inv.h_cliente, inv.centro, (inv.v_sm_rojo, 1))
    r = client.post(f"/api/sucursales/{inv.centro.id}/desactivar", headers=inv.h_admin)
    assert r.status_code == 409
    assert r.json()["detail"] == "La sucursal tiene reservas pendientes u operaciones sin sincronizar. Resuélvalas antes de desactivarla."
    client.post(f"/api/reservas/{res['id']}/cancelar", json={}, headers=inv.h_cliente)
    assert client.post(f"/api/sucursales/{inv.centro.id}/desactivar", headers=inv.h_admin).json()["activa"] is False

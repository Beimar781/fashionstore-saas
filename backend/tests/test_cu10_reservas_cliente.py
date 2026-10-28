"""CU-10 Consultar y cancelar reservas — caja negra, expiración y aislamiento."""
from tests.catalogo_util import cabecera_cliente, entrar
from tests.reservas_util import avisos, fila, reserva_ok, vencer


def _lista(inv, mundo, cantidad=10):
    inv.stock(mundo.a.id, inv.centro.id, inv.v_sm_rojo["id"], cantidad)
    inv.stock(mundo.a.id, inv.centro.id, inv.var[("M", "Azul")]["id"], cantidad)


def test_01_el_cliente_ve_solo_sus_reservas(inv, mundo, datos, client):
    _lista(inv, mundo)
    mia = reserva_ok(client, inv.h_cliente, inv.centro, (inv.v_sm_rojo, 1))
    datos.usuario(mundo.a, "Cliente", email="otro@a.com")
    h_otro = entrar(client, mundo.a, "otro@a.com")
    ajena = reserva_ok(client, h_otro, inv.centro, (inv.v_sm_rojo, 1))
    assert [r["id"] for r in client.get("/api/reservas", headers=inv.h_cliente).json()] == [mia["id"]]
    assert [r["id"] for r in client.get("/api/reservas", headers=h_otro).json()] == [ajena["id"]]


def test_02_consultar_el_estado_de_una_reserva(inv, mundo, client):  # RF12
    _lista(inv, mundo)
    res = reserva_ok(client, inv.h_cliente, inv.centro, (inv.v_sm_rojo, 2), (inv.var[("M", "Azul")], 1))
    r = client.get(f"/api/reservas/{res['id']}", headers=inv.h_cliente).json()
    assert (r["codigo"], r["estado"], r["sucursal"], r["total_unidades"]) == (res["codigo"], "PENDIENTE", "Centro", 3)
    assert {i["sku"] for i in r["items"]} == {inv.v_sm_rojo["sku"], inv.var[("M", "Azul")]["sku"]}
    # el Encargado prepara y el cliente ve el cambio de estado
    client.post(f"/api/reservas-sucursal/{res['id']}/preparar", headers=inv.h_enc_centro)
    assert client.get(f"/api/reservas/{res['id']}", headers=inv.h_cliente).json()["estado"] == "PREPARADA"


def test_03_filtrar_por_estado(inv, mundo, client):
    _lista(inv, mundo)
    a = reserva_ok(client, inv.h_cliente, inv.centro, (inv.v_sm_rojo, 1))
    b = reserva_ok(client, inv.h_cliente, inv.centro, (inv.v_sm_rojo, 1))
    client.post(f"/api/reservas/{a['id']}/cancelar", json={}, headers=inv.h_cliente)
    assert [r["id"] for r in client.get("/api/reservas?estado=PENDIENTE", headers=inv.h_cliente).json()] == [b["id"]]
    assert [r["id"] for r in client.get("/api/reservas?estado=CANCELADA", headers=inv.h_cliente).json()] == [a["id"]]
    assert len(client.get("/api/reservas", headers=inv.h_cliente).json()) == 2


def test_04_cancelar_devuelve_el_stock(inv, mundo, client):
    _lista(inv, mundo)
    res = reserva_ok(client, inv.h_cliente, inv.centro, (inv.v_sm_rojo, 3))
    assert fila(client, inv.h_enc_centro, inv.v_sm_rojo)["reservada"] == 3
    r = client.post(f"/api/reservas/{res['id']}/cancelar", json={"motivo": "Cambié de planes"}, headers=inv.h_cliente)
    assert r.status_code == 200 and r.json()["estado"] == "CANCELADA" and r.json()["puede_cancelar"] is False
    assert r.json()["items"][0]["estado"] == "LIBERADO" and "Cambié de planes" in r.json()["notas"]
    f = fila(client, inv.h_enc_centro, inv.v_sm_rojo)
    assert (f["disponible"], f["reservada"]) == (10, 0)
    tipos = [m["tipo"] for m in client.get("/api/inventario/movimientos", headers=inv.h_enc_centro).json()["items"]]
    assert "LIBERA_RESERVA" in tipos


def test_05_cancelar_avisa_a_la_sucursal(inv, mundo, client):  # RF11
    _lista(inv, mundo)
    res = reserva_ok(client, inv.h_cliente, inv.centro, (inv.v_sm_rojo, 1))
    client.post(f"/api/reservas/{res['id']}/cancelar", json={}, headers=inv.h_cliente)
    aviso = next(n for n in avisos(client, inv.h_enc_centro) if n["tipo"] == "RESERVA_CANCELADA")
    assert res["codigo"] in aviso["titulo"]


def test_06_se_puede_cancelar_una_reserva_preparada(inv, mundo, client):
    _lista(inv, mundo)
    res = reserva_ok(client, inv.h_cliente, inv.centro, (inv.v_sm_rojo, 1))
    client.post(f"/api/reservas-sucursal/{res['id']}/preparar", headers=inv.h_enc_centro)
    assert client.post(f"/api/reservas/{res['id']}/cancelar", json={}, headers=inv.h_cliente).json()["estado"] == "CANCELADA"
    assert fila(client, inv.h_enc_centro, inv.v_sm_rojo)["disponible"] == 10


def test_07_no_se_cancela_dos_veces_ni_una_atendida(inv, mundo, client):
    _lista(inv, mundo)
    res = reserva_ok(client, inv.h_cliente, inv.centro, (inv.v_sm_rojo, 1))
    client.post(f"/api/reservas/{res['id']}/cancelar", json={}, headers=inv.h_cliente)
    r = client.post(f"/api/reservas/{res['id']}/cancelar", json={}, headers=inv.h_cliente)
    assert r.status_code == 409 and r.json()["detail"] == "No se puede cancelar una reserva cancelada."
    otra = reserva_ok(client, inv.h_cliente, inv.centro, (inv.v_sm_rojo, 1))
    client.post(f"/api/atencion-reservas/{otra['id']}/atender", headers=inv.h_enc_centro)  # el cliente ya está en el probador
    r = client.post(f"/api/reservas/{otra['id']}/cancelar", json={}, headers=inv.h_cliente)
    assert r.status_code == 409 and r.json()["detail"] == "No se puede cancelar una reserva en probador."
    assert fila(client, inv.h_enc_centro, inv.v_sm_rojo)["reservada"] == 1  # el stock de la atendida sigue apartado


def test_08_una_reserva_vencida_expira_y_devuelve_el_stock(inv, mundo, client, db):
    _lista(inv, mundo)
    res = reserva_ok(client, inv.h_cliente, inv.centro, (inv.v_sm_rojo, 4))
    vencer(db, res["id"])
    r = client.get(f"/api/reservas/{res['id']}", headers=inv.h_cliente).json()
    assert r["estado"] == "EXPIRADA" and r["items"][0]["estado"] == "LIBERADO"
    f = fila(client, inv.h_enc_centro, inv.v_sm_rojo)
    assert (f["disponible"], f["reservada"]) == (10, 0)
    assert any(n["tipo"] == "RESERVA_EXPIRADA" for n in avisos(client, inv.h_cliente))
    r = client.post(f"/api/reservas/{res['id']}/cancelar", json={}, headers=inv.h_cliente)
    assert r.status_code == 409 and r.json()["detail"] == "No se puede cancelar una reserva expirada."


def test_09_la_expiracion_la_dispara_la_sucursal_tambien(inv, mundo, client, db):
    _lista(inv, mundo)
    res = reserva_ok(client, inv.h_cliente, inv.centro, (inv.v_sm_rojo, 4))
    vencer(db, res["id"])
    assert client.get("/api/reservas-sucursal", headers=inv.h_enc_centro).json() == []  # ya no es una reserva activa
    assert fila(client, inv.h_enc_centro, inv.v_sm_rojo)["disponible"] == 10


def test_10_reserva_ajena_o_de_otra_empresa(inv, mundo, tienda_b, datos, client):
    _lista(inv, mundo)
    res = reserva_ok(client, inv.h_cliente, inv.centro, (inv.v_sm_rojo, 1))
    datos.usuario(mundo.a, "Cliente", email="otro@a.com")
    h_otro = entrar(client, mundo.a, "otro@a.com")
    h_b = cabecera_cliente(datos, mundo.b)
    for h in (h_otro, h_b):
        assert client.get(f"/api/reservas/{res['id']}", headers=h).status_code == 404
        assert client.post(f"/api/reservas/{res['id']}/cancelar", json={}, headers=h).status_code == 404
    assert client.get(f"/api/reservas/{res['id']}", headers=inv.h_cliente).json()["estado"] == "PENDIENTE"


def test_11_solo_el_cliente_consulta_sus_reservas(inv, client):
    for h in (inv.h_enc_centro, inv.h_cajero, inv.h_admin):
        assert client.get("/api/reservas", headers=h).status_code == 403

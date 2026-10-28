"""RF11 Notificar las reservas a la sucursal (y avisos al cliente) — quién ve qué, lectura y aislamiento."""
from tests.catalogo_util import cabecera_cliente, entrar
from tests.reservas_util import avisos, reserva_ok


def _reserva(inv, mundo, client):
    if not getattr(inv, "con_stock", False):
        inv.stock(mundo.a.id, inv.centro.id, inv.v_sm_rojo["id"], 10)
        inv.con_stock = True
    return reserva_ok(client, inv.h_cliente, inv.centro, (inv.v_sm_rojo, 1))


def test_01_la_sucursal_recibe_el_aviso_de_la_reserva(inv, mundo, client):
    res = _reserva(inv, mundo, client)
    n = next(x for x in avisos(client, inv.h_enc_centro) if x["tipo"] == "RESERVA_NUEVA")
    assert (n["leida"], n["referencia_tipo"], n["referencia_id"]) == (False, "RESERVA", res["id"])
    assert client.get("/api/notificaciones/resumen", headers=inv.h_enc_centro).json() == {"no_leidas": 1}


def test_02_cada_sucursal_ve_solo_lo_suyo_y_el_administrador_todo(inv, mundo, client):
    _reserva(inv, mundo, client)
    assert avisos(client, inv.h_enc_norte) == []
    assert any(n["tipo"] == "RESERVA_NUEVA" for n in avisos(client, inv.h_admin))
    assert any(n["tipo"] == "RESERVA_NUEVA" for n in avisos(client, inv.h_cajero))  # el Cajero es de Centro


def test_03_el_cliente_ve_solo_sus_avisos(inv, mundo, datos, client):
    _reserva(inv, mundo, client)
    assert [n["tipo"] for n in avisos(client, inv.h_cliente)] == ["RESERVA_CREADA"]
    datos.usuario(mundo.a, "Cliente", email="otro@a.com")
    assert avisos(client, entrar(client, mundo.a, "otro@a.com")) == []


def test_04_marcar_como_leida(inv, mundo, client):
    _reserva(inv, mundo, client)
    n = next(x for x in avisos(client, inv.h_enc_centro) if x["tipo"] == "RESERVA_NUEVA")
    assert client.post(f"/api/notificaciones/{n['id']}/leer", headers=inv.h_enc_centro).json()["leida"] is True
    assert client.get("/api/notificaciones/resumen", headers=inv.h_enc_centro).json() == {"no_leidas": 0}
    assert avisos(client, inv.h_enc_centro)[0]["leida"] is True
    assert client.get("/api/notificaciones?solo_no_leidas=true", headers=inv.h_enc_centro).json() == []


def test_05_marcar_todas_como_leidas(inv, mundo, client):
    _reserva(inv, mundo, client)
    _reserva(inv, mundo, client)
    assert client.get("/api/notificaciones/resumen", headers=inv.h_cliente).json() == {"no_leidas": 2}
    assert client.post("/api/notificaciones/leer-todas", headers=inv.h_cliente).json() == {"no_leidas": 0}
    assert client.get("/api/notificaciones/resumen", headers=inv.h_enc_centro).json() == {"no_leidas": 2}  # lo de otros no se toca


def test_06_no_se_lee_el_aviso_de_otro(inv, mundo, client):
    _reserva(inv, mundo, client)
    n = next(x for x in avisos(client, inv.h_enc_centro) if x["tipo"] == "RESERVA_NUEVA")
    assert client.post(f"/api/notificaciones/{n['id']}/leer", headers=inv.h_enc_norte).status_code == 404
    assert client.post(f"/api/notificaciones/{n['id']}/leer", headers=inv.h_cliente).status_code == 404


def test_07_aislamiento_entre_empresas(inv, mundo, tienda_b, datos, client):
    _reserva(inv, mundo, client)
    h_admin_b, h_cli_b = tienda_b.h_admin, cabecera_cliente(datos, mundo.b)
    assert avisos(client, h_admin_b) == [] and avisos(client, h_cli_b) == []
    n = next(x for x in avisos(client, inv.h_enc_centro) if x["tipo"] == "RESERVA_NUEVA")
    assert client.post(f"/api/notificaciones/{n['id']}/leer", headers=h_admin_b).status_code == 404


def test_08_requiere_sesion(client):
    assert client.get("/api/notificaciones").status_code == 401

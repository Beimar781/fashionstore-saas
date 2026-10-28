"""CU-25 Confirmar recepción y atención del cliente — pasos de la ficha (5.2.1) y aislamiento."""
from tests.reservas_util import fila, reserva_ok, vencer

MSG_CODIGO = "El código de reserva no existe o ya ha expirado su vigencia."


def _reserva(inv, mundo, client, sucursal=None):
    if not getattr(inv, "con_stock", False):
        for suc in (inv.centro, inv.norte):
            inv.stock(mundo.a.id, suc.id, inv.v_sm_rojo["id"], 10)
        inv.con_stock = True
    return reserva_ok(client, inv.h_cliente, sucursal or inv.centro, (inv.v_sm_rojo, 2))


def _validar(client, h, codigo):
    return client.post("/api/atencion-reservas/validar", json={"codigo": codigo}, headers=h)


def test_01_validar_el_codigo_presentado(inv, mundo, client):
    res = _reserva(inv, mundo, client)
    for codigo in (res["codigo"], res["codigo"].lower(), f"  {res['codigo']} "):  # se tolera mayúsculas y espacios
        r = _validar(client, inv.h_enc_centro, codigo)
        assert r.status_code == 200 and r.json()["id"] == res["id"] and r.json()["estado"] == "PENDIENTE"
    client.post(f"/api/reservas-sucursal/{res['id']}/preparar", headers=inv.h_enc_centro)
    assert _validar(client, inv.h_enc_centro, res["codigo"]).json()["estado"] == "PREPARADA"  # también preparada


def test_02_codigo_invalido_o_expirado(inv, mundo, client, db):
    res = _reserva(inv, mundo, client)
    r = _validar(client, inv.h_enc_centro, "RSV-NOEXISTE")
    assert r.status_code == 404 and r.json()["detail"] == MSG_CODIGO
    vencer(db, res["id"])
    r = _validar(client, inv.h_enc_centro, res["codigo"])
    assert r.status_code == 404 and r.json()["detail"] == MSG_CODIGO
    assert fila(client, inv.h_enc_centro, inv.v_sm_rojo)["disponible"] == 10  # al vencer devolvió su stock


def test_03_la_reserva_debe_pertenecer_a_la_sucursal(inv, mundo, client):
    res = _reserva(inv, mundo, client)  # en Centro
    r = _validar(client, inv.h_enc_norte, res["codigo"])
    assert r.status_code == 409 and r.json()["detail"] == "La reserva corresponde a otra sucursal."
    assert client.post(f"/api/atencion-reservas/{res['id']}/atender", headers=inv.h_enc_norte).status_code == 404
    assert _validar(client, inv.h_enc_centro, res["codigo"]).status_code == 200


def test_04_entregar_las_prendas_y_completar_la_atencion(inv, mundo, client):
    res = _reserva(inv, mundo, client)
    r = client.post(f"/api/atencion-reservas/{res['id']}/atender", headers=inv.h_enc_centro)
    assert r.status_code == 200 and r.json()["estado"] == "EN_PROBADOR"
    assert fila(client, inv.h_enc_centro, inv.v_sm_rojo)["reservada"] == 2  # en el probador sigue apartado
    r = client.post(f"/api/atencion-reservas/{res['id']}/completar", json={"llevara_prendas": False}, headers=inv.h_enc_centro)
    assert r.status_code == 200 and r.json()["reserva"]["estado"] == "COMPLETADA" and r.json()["habilita_venta"] is False
    f = fila(client, inv.h_enc_centro, inv.v_sm_rojo)
    assert (f["disponible"], f["reservada"]) == (10, 0)  # no compró: las prendas vuelven a estar disponibles
    assert _validar(client, inv.h_enc_centro, res["codigo"]).status_code == 404  # un código ya completado no sirve


def test_05_si_decide_llevar_las_prendas_se_habilita_la_venta(inv, mundo, client):
    res = _reserva(inv, mundo, client)
    client.post(f"/api/atencion-reservas/{res['id']}/atender", headers=inv.h_enc_centro)
    r = client.post(f"/api/atencion-reservas/{res['id']}/completar", json={"llevara_prendas": True}, headers=inv.h_enc_centro)
    assert r.status_code == 200 and r.json()["habilita_venta"] is True and r.json()["reserva"]["estado"] == "EN_PROBADOR"
    assert fila(client, inv.h_enc_centro, inv.v_sm_rojo)["reservada"] == 2  # el cobro (CU-29) usará este stock apartado


def test_06_reglas_del_flujo(inv, mundo, client):
    res = _reserva(inv, mundo, client)
    r = client.post(f"/api/atencion-reservas/{res['id']}/completar", json={}, headers=inv.h_enc_centro)
    assert r.status_code == 409 and r.json()["detail"] == "Primero debe atender al cliente (entregar las prendas)."
    client.post(f"/api/atencion-reservas/{res['id']}/atender", headers=inv.h_enc_centro)
    r = client.post(f"/api/atencion-reservas/{res['id']}/atender", headers=inv.h_enc_centro)
    assert r.status_code == 409 and r.json()["detail"] == "La reserva debe estar pendiente o preparada para atender al cliente."


def test_07_una_reserva_cancelada_no_se_atiende(inv, mundo, client):
    res = _reserva(inv, mundo, client)
    client.post(f"/api/reservas/{res['id']}/cancelar", json={}, headers=inv.h_cliente)
    assert _validar(client, inv.h_enc_centro, res["codigo"]).json()["detail"] == MSG_CODIGO
    assert client.post(f"/api/atencion-reservas/{res['id']}/atender", headers=inv.h_enc_centro).status_code == 409


def test_08_solo_el_encargado_atiende(inv, mundo, client):
    res = _reserva(inv, mundo, client)
    for h in (inv.h_cliente, inv.h_cajero, inv.h_admin):
        assert _validar(client, h, res["codigo"]).status_code == 403
        assert client.post(f"/api/atencion-reservas/{res['id']}/atender", headers=h).status_code == 403


def test_09_el_codigo_de_otra_empresa_no_existe(inv, mundo, tienda_b, datos, client):
    from tests.catalogo_util import entrar
    res = _reserva(inv, mundo, client)
    datos.usuario(mundo.b, "Encargado", email="enc@b.com", sucursal=datos.sucursal(mundo.b, "Sucursal B"))
    h_b = entrar(client, mundo.b, "enc@b.com")
    r = _validar(client, h_b, res["codigo"])
    assert r.status_code == 404 and r.json()["detail"] == MSG_CODIGO  # no se revela que existe en otra empresa
    assert client.post(f"/api/atencion-reservas/{res['id']}/atender", headers=h_b).status_code == 404

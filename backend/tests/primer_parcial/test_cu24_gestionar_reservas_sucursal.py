"""CU-24 Gestionar reservas de la sucursal — pasos de la ficha (5.2.1) y aislamiento entre sucursales y empresas."""
from tests.catalogo_util import cabecera_cliente
from tests.reservas_util import avisos, fecha_local, fila, reserva_ok


def _reserva(inv, mundo, client, *prendas, sucursal=None):
    for suc in (inv.centro, inv.norte):
        for v in (inv.v_sm_rojo, inv.var[("M", "Azul")]):
            if not getattr(inv, f"stock_{suc.id}_{v['id']}", False):
                inv.stock(mundo.a.id, suc.id, v["id"], 10)
                setattr(inv, f"stock_{suc.id}_{v['id']}", True)
    return reserva_ok(client, inv.h_cliente, sucursal or inv.centro, *(prendas or [(inv.v_sm_rojo, 2), (inv.var[("M", "Azul")], 1)]))


def test_01_lista_las_reservas_pendientes_del_dia(inv, mundo, client):
    hoy = _reserva(inv, mundo, client)  # mañana 11:00
    otro_dia = reserva_ok(client, inv.h_cliente, inv.centro, (inv.v_sm_rojo, 1), dias=3)
    r = client.get(f"/api/reservas-sucursal?estado=PENDIENTE&fecha={fecha_local(1)}", headers=inv.h_enc_centro).json()
    assert [x["id"] for x in r] == [hoy["id"]]
    todas = client.get("/api/reservas-sucursal", headers=inv.h_enc_centro).json()
    assert [x["id"] for x in todas] == [hoy["id"], otro_dia["id"]]  # ordenadas por horario de visita
    assert todas[0]["cliente"] == "Cliente Prueba"


def test_02_el_detalle_muestra_sku_talla_y_color(inv, mundo, client):
    res = _reserva(inv, mundo, client)
    d = client.get(f"/api/reservas-sucursal/{res['id']}", headers=inv.h_enc_centro).json()
    assert {(i["sku"], i["talla"], i["color"], i["cantidad"]) for i in d["items"]} == {
        (inv.v_sm_rojo["sku"], "S", "Rojo", 2), (inv.var[("M", "Azul")]["sku"], "M", "Azul", 1)}


def test_03_preparar_las_prendas(inv, mundo, client):
    res = _reserva(inv, mundo, client)
    r = client.post(f"/api/reservas-sucursal/{res['id']}/preparar", headers=inv.h_enc_centro)
    assert r.status_code == 200 and r.json()["estado"] == "PREPARADA"
    assert fila(client, inv.h_enc_centro, inv.v_sm_rojo)["reservada"] == 2  # sigue apartado hasta que el cliente llegue
    r = client.post(f"/api/reservas-sucursal/{res['id']}/preparar", headers=inv.h_enc_centro)
    assert r.status_code == 409 and r.json()["detail"] == "No se puede pasar una reserva preparada a preparada."


def test_04_una_prenda_no_encontrada_ajusta_el_stock_y_avisa(inv, mundo, client):
    res = _reserva(inv, mundo, client)
    item = next(i for i in res["items"] if i["sku"] == inv.v_sm_rojo["sku"])
    r = client.post(f"/api/reservas-sucursal/{res['id']}/items/{item['id']}/no-encontrado", headers=inv.h_enc_centro)
    assert r.status_code == 200 and r.json()["estado"] == "PENDIENTE"
    assert next(i for i in r.json()["items"] if i["id"] == item["id"])["estado"] == "NO_ENCONTRADO"
    f = fila(client, inv.h_enc_centro, inv.v_sm_rojo)
    assert (f["disponible"], f["reservada"]) == (8, 0)  # la prenda perdida sale del inventario, no vuelve a venderse
    tipos = {m["tipo"]: m for m in client.get("/api/inventario/movimientos", headers=inv.h_enc_centro).json()["items"]}
    assert "AJUSTE_SALIDA" in tipos and "No encontrado en físico" in tipos["AJUSTE_SALIDA"]["nota"]
    assert any(n["tipo"] == "AJUSTE_STOCK" for n in avisos(client, inv.h_enc_centro))  # ajuste de stock para la sucursal
    disculpas = next(n for n in avisos(client, inv.h_cliente) if n["tipo"] == "RESERVA_AJUSTE")
    assert "Lamentamos" in disculpas["mensaje"] and "Preparamos el resto" in disculpas["mensaje"]
    r = client.post(f"/api/reservas-sucursal/{res['id']}/items/{item['id']}/no-encontrado", headers=inv.h_enc_centro)
    assert r.status_code == 409 and r.json()["detail"] == "La prenda ya fue marcada."


def test_05_el_cliente_recibe_el_aviso_de_que_puede_pasar(inv, mundo, client):
    res = _reserva(inv, mundo, client)
    client.post(f"/api/reservas-sucursal/{res['id']}/preparar", headers=inv.h_enc_centro)
    aviso = next(n for n in avisos(client, inv.h_cliente) if n["tipo"] == "RESERVA_PREPARADA")
    assert "puede pasar a la tienda" in aviso["mensaje"] and res["codigo"] in aviso["titulo"]


def test_06_si_no_queda_ninguna_prenda_la_reserva_se_cancela(inv, mundo, client):
    res = _reserva(inv, mundo, client)
    for item in res["items"]:
        r = client.post(f"/api/reservas-sucursal/{res['id']}/items/{item['id']}/no-encontrado", headers=inv.h_enc_centro)
    assert r.json()["estado"] == "CANCELADA"
    assert client.post(f"/api/reservas-sucursal/{res['id']}/preparar", headers=inv.h_enc_centro).status_code == 409
    assert "cancelada" in next(n for n in avisos(client, inv.h_cliente) if n["tipo"] == "RESERVA_AJUSTE")["mensaje"]


def test_07_no_se_marca_un_item_de_una_reserva_atendida(inv, mundo, client):
    res = _reserva(inv, mundo, client)
    client.post(f"/api/atencion-reservas/{res['id']}/atender", headers=inv.h_enc_centro)
    r = client.post(f"/api/reservas-sucursal/{res['id']}/items/{res['items'][0]['id']}/no-encontrado", headers=inv.h_enc_centro)
    assert r.status_code == 409 and r.json()["detail"] == "No se puede modificar una reserva en probador."
    assert client.post(f"/api/reservas-sucursal/{res['id']}/items/99999/no-encontrado", headers=inv.h_enc_norte).status_code == 404


def test_08_el_encargado_solo_ve_su_sucursal(inv, mundo, client):
    res = _reserva(inv, mundo, client)  # en Centro
    assert client.get("/api/reservas-sucursal", headers=inv.h_enc_norte).json() == []
    assert client.get(f"/api/reservas-sucursal/{res['id']}", headers=inv.h_enc_norte).status_code == 404
    assert client.post(f"/api/reservas-sucursal/{res['id']}/preparar", headers=inv.h_enc_norte).status_code == 404
    en_norte = _reserva(inv, mundo, client, (inv.v_sm_rojo, 1), sucursal=inv.norte)
    assert [r["id"] for r in client.get("/api/reservas-sucursal", headers=inv.h_enc_norte).json()] == [en_norte["id"]]


def test_09_solo_el_encargado_gestiona_las_reservas_de_la_sucursal(inv, mundo, client):
    res = _reserva(inv, mundo, client)
    for h in (inv.h_cliente, inv.h_cajero, inv.h_admin, inv.h_prov):
        assert client.get("/api/reservas-sucursal", headers=h).status_code == 403
        assert client.post(f"/api/reservas-sucursal/{res['id']}/preparar", headers=h).status_code == 403


def test_10_aislamiento_entre_empresas(inv, mundo, tienda_b, datos, client):
    from tests.catalogo_util import entrar
    res = _reserva(inv, mundo, client)
    datos.usuario(mundo.b, "Encargado", email="enc@b.com", sucursal=datos.sucursal(mundo.b, "Sucursal B"))
    h_b = entrar(client, mundo.b, "enc@b.com")
    assert client.get("/api/reservas-sucursal", headers=h_b).json() == []
    assert client.get(f"/api/reservas-sucursal/{res['id']}", headers=h_b).status_code == 404
    assert client.post(f"/api/reservas-sucursal/{res['id']}/preparar", headers=h_b).status_code == 404

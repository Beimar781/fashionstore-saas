"""CU-26 Gestionar disponibilidad e inventario de la sucursal — caja negra, núcleo de movimientos, recepción de lotes y aislamiento."""
from sqlalchemy import select

from app.modules.inventario.models import Existencia, MovimientoInventario
from app.modules.inventario.publico import aplicar_movimientos


def _ajuste(variante, cantidad, tipo="AJUSTE_ENTRADA", nota="Conteo físico"):
    return {"variante_id": variante["id"], "tipo": tipo, "cantidad": cantidad, "nota": nota}


def _fila(client, h, **params):
    return client.get("/api/inventario/sucursal", params=params, headers=h).json()


def test_01_el_encargado_ve_solo_el_inventario_de_su_sucursal(mundo, inv, client):
    inv.stock(mundo.a.id, inv.centro.id, inv.v_sm_rojo["id"], 7)
    inv.stock(mundo.a.id, inv.norte.id, inv.v_sm_rojo["id"], 30)
    r = _fila(client, inv.h_enc_centro, q="oxford")
    fila = next(x for x in r["items"] if x["sku"] == inv.v_sm_rojo["sku"])
    assert fila["disponible"] == 7 and fila["producto"] == "Camisa Oxford" and r["por_sucursal"] == []
    assert next(x for x in _fila(client, inv.h_enc_norte)["items"] if x["sku"] == inv.v_sm_rojo["sku"])["disponible"] == 30


def test_02_ajuste_de_entrada_suma_y_deja_bitacora(inv, client):
    r = client.post("/api/inventario/sucursal/movimientos", json=_ajuste(inv.v_sm_rojo, 12), headers=inv.h_enc_centro)
    assert r.status_code == 201 and (r.json()["disponible"], r.json()["reservada"], r.json()["vendida"]) == (12, 0, 0)
    m = client.get("/api/inventario/movimientos", headers=inv.h_enc_centro).json()["items"][0]
    assert (m["tipo"], m["cantidad"], m["referencia_tipo"], m["usuario"], m["nota"], m["sucursal"]) == (
        "AJUSTE_ENTRADA", 12, "MANUAL", "Encargado Prueba", "Conteo físico", "Centro")
    assert (m["sku"], m["talla"], m["color"]) == (inv.v_sm_rojo["sku"], "S", "Rojo")


def test_03_ajuste_de_salida_y_stock_insuficiente(inv, client):
    h = inv.h_enc_centro
    client.post("/api/inventario/sucursal/movimientos", json=_ajuste(inv.v_sm_rojo, 5), headers=h)
    r = client.post("/api/inventario/sucursal/movimientos", json=_ajuste(inv.v_sm_rojo, 2, "AJUSTE_SALIDA", "Prenda dañada"), headers=h)
    assert r.json()["disponible"] == 3
    r = client.post("/api/inventario/sucursal/movimientos", json=_ajuste(inv.v_sm_rojo, 10, "AJUSTE_SALIDA", "Robo"), headers=h)
    assert r.status_code == 409 and r.json()["detail"] == "Stock insuficiente: se requieren 10 unidades, pero solo hay 3 disponibles."
    total = client.get("/api/inventario/movimientos", headers=h).json()["total"]
    assert total == 2  # el intento fallido no dejó movimiento


def test_04_todo_ajuste_lleva_motivo_y_cantidad_valida(inv, client):
    h = inv.h_enc_centro
    for cuerpo in (_ajuste(inv.v_sm_rojo, 3, nota=""), _ajuste(inv.v_sm_rojo, 0), _ajuste(inv.v_sm_rojo, 3, tipo="VENTA")):
        assert client.post("/api/inventario/sucursal/movimientos", json=cuerpo, headers=h).status_code == 422
    assert client.post("/api/inventario/sucursal/movimientos", json=_ajuste({"id": 99999}, 3), headers=h).status_code == 404


def test_05_umbral_de_reposicion_y_filtro_bajo_minimo(inv, client):
    h = inv.h_enc_centro
    client.post("/api/inventario/sucursal/movimientos", json=_ajuste(inv.v_sm_rojo, 4), headers=h)
    client.post("/api/inventario/sucursal/movimientos", json=_ajuste(inv.var[("M", "Rojo")], 40), headers=h)
    r = client.put(f"/api/inventario/sucursal/variantes/{inv.v_sm_rojo['id']}/umbral", json={"umbral_minimo": 5}, headers=h)
    assert r.json()["umbral_minimo"] == 5
    client.put(f"/api/inventario/sucursal/variantes/{inv.var[('M', 'Rojo')]['id']}/umbral", json={"umbral_minimo": 5}, headers=h)
    bajos = _fila(client, h, solo_bajo_minimo=True)["items"]
    assert [(x["sku"], x["bajo_minimo"]) for x in bajos] == [(inv.v_sm_rojo["sku"], True)]  # la de 40 unidades no está bajo el mínimo


def test_06_estados_agotada_disponible_y_filtros(mundo, inv, client):
    inv.stock(mundo.a.id, inv.centro.id, inv.v_sm_rojo["id"], 3)
    todo = _fila(client, inv.h_enc_centro)
    assert todo["total"] == 4 and todo["resumen"]["agotadas"] == 3 and todo["resumen"]["disponibles"] == 3
    assert [x["sku"] for x in _fila(client, inv.h_enc_centro, estado="DISPONIBLE")["items"]] == [inv.v_sm_rojo["sku"]]
    assert len(_fila(client, inv.h_enc_centro, estado="AGOTADA")["items"]) == 3


def test_07_movimientos_filtros_y_alcance_por_sucursal(inv, client):
    client.post("/api/inventario/sucursal/movimientos", json=_ajuste(inv.v_sm_rojo, 5), headers=inv.h_enc_centro)
    client.post("/api/inventario/sucursal/movimientos", json=_ajuste(inv.v_sm_rojo, 9), headers=inv.h_enc_norte)
    # el Encargado de Centro no ve lo de Norte aunque lo pida
    visibles = client.get(f"/api/inventario/movimientos?sucursal={inv.norte.id}", headers=inv.h_enc_centro).json()
    assert [(m["sucursal"], m["cantidad"]) for m in visibles["items"]] == [("Centro", 5)]
    # el Administrador ve todo y puede filtrar
    admin = client.get("/api/inventario/movimientos", headers=inv.h_admin).json()
    assert admin["total"] == 2
    assert client.get(f"/api/inventario/movimientos?sucursal={inv.norte.id}&tipo=AJUSTE_ENTRADA", headers=inv.h_admin).json()["total"] == 1
    assert client.get("/api/inventario/movimientos?tipo=VENTA", headers=inv.h_admin).json()["total"] == 0


def test_08_recibir_un_lote_suma_al_inventario(inv, client):
    items = [{"sku": inv.v_sm_rojo["sku"], "cantidad": 10}, {"sku": inv.var[("M", "Azul")]["sku"], "cantidad": 6}]
    lote = client.post("/api/abastecimiento/lotes", json={"sucursal_id": inv.centro.id, "items": items}, headers=inv.h_prov).json()
    pendientes = client.get("/api/inventario/recepciones", headers=inv.h_enc_centro).json()
    assert [x["id"] for x in pendientes] == [lote["id"]]
    assert client.get("/api/inventario/recepciones", headers=inv.h_enc_norte).json() == []  # el lote va a otra sucursal

    r = client.post(f"/api/inventario/recepciones/{lote['id']}/recibir", json={}, headers=inv.h_enc_centro)
    assert r.status_code == 200 and r.json()["estado"] == "RECIBIDO" and [i["cantidad_recibida"] for i in r.json()["items"]] == [10, 6]
    stock = {x["sku"]: x["disponible"] for x in _fila(client, inv.h_enc_centro)["items"]}
    assert (stock[inv.v_sm_rojo["sku"]], stock[inv.var[("M", "Azul")]["sku"]]) == (10, 6)
    m = client.get("/api/inventario/movimientos?tipo=ENTRADA_RECEPCION", headers=inv.h_enc_centro).json()["items"]
    assert len(m) == 2 and {(x["referencia_tipo"], x["referencia_id"]) for x in m} == {("RECEPCION", lote["id"])}
    assert client.post(f"/api/inventario/recepciones/{lote['id']}/recibir", json={}, headers=inv.h_enc_centro).status_code == 409  # no se recibe dos veces
    assert client.get("/api/inventario/recepciones", headers=inv.h_enc_centro).json() == []


def test_09_recepcion_parcial_y_exceso(inv, client):
    lote = client.post("/api/abastecimiento/lotes", headers=inv.h_prov, json={
        "sucursal_id": inv.centro.id, "items": [{"sku": inv.v_sm_rojo["sku"], "cantidad": 10}]}).json()
    item = lote["items"][0]["id"]
    r = client.post(f"/api/inventario/recepciones/{lote['id']}/recibir", json={"items": [{"item_id": item, "cantidad_recibida": 11}]}, headers=inv.h_enc_centro)
    assert r.status_code == 422 and r.json()["detail"] == "No puede recibir más unidades de las que despachó el proveedor."
    r = client.post(f"/api/inventario/recepciones/{lote['id']}/recibir", json={"items": [{"item_id": item, "cantidad_recibida": 7}]}, headers=inv.h_enc_centro)
    assert r.json()["items"][0]["cantidad_recibida"] == 7
    assert next(x for x in _fila(client, inv.h_enc_centro)["items"] if x["sku"] == inv.v_sm_rojo["sku"])["disponible"] == 7


def test_10_solo_se_recibe_en_la_propia_sucursal(inv, client):
    lote = client.post("/api/abastecimiento/lotes", headers=inv.h_prov, json={
        "sucursal_id": inv.centro.id, "items": [{"sku": inv.v_sm_rojo["sku"], "cantidad": 4}]}).json()
    assert client.post(f"/api/inventario/recepciones/{lote['id']}/recibir", json={}, headers=inv.h_enc_norte).status_code == 404
    r = client.post(f"/api/inventario/recepciones/{lote['id']}/recibir", json={}, headers=inv.h_admin)  # el Administrador sí puede
    assert r.status_code == 200
    assert next(x for x in _fila(client, inv.h_enc_centro)["items"] if x["sku"] == inv.v_sm_rojo["sku"])["disponible"] == 4


def test_11_la_proxima_a_ingresar_se_ve_mientras_el_lote_viaja(inv, client):
    client.post("/api/abastecimiento/lotes", headers=inv.h_prov, json={
        "sucursal_id": inv.centro.id, "items": [{"sku": inv.v_sm_rojo["sku"], "cantidad": 8}]})
    fila = next(x for x in _fila(client, inv.h_enc_centro)["items"] if x["sku"] == inv.v_sm_rojo["sku"])
    assert fila["proxima"] == 8 and fila["disponible"] == 0
    assert next(x for x in _fila(client, inv.h_enc_norte)["items"] if x["sku"] == inv.v_sm_rojo["sku"])["proxima"] == 0


def test_12_nucleo_de_movimientos_reserva_venta_y_devolucion(mundo, inv, db):
    v = inv.v_sm_rojo["id"]
    emp, suc = mundo.a.id, inv.centro.id
    aplicar_movimientos(db, emp, suc, [(v, 10)], "AJUSTE_ENTRADA", "MANUAL", nota="inicial")
    aplicar_movimientos(db, emp, suc, [(v, 4)], "RESERVA", "RESERVA", 1)            # disponible → reservada
    aplicar_movimientos(db, emp, suc, [(v, 1)], "LIBERA_RESERVA", "RESERVA", 1)     # reservada → disponible
    aplicar_movimientos(db, emp, suc, [(v, 3)], "VENTA_RESERVA", "VENTA", 7)        # reservada → vendida
    aplicar_movimientos(db, emp, suc, [(v, 2)], "VENTA", "VENTA", 8)                # disponible → vendida
    aplicar_movimientos(db, emp, suc, [(v, 1)], "DEVOLUCION", "DEVOLUCION", 8)      # vendida → disponible
    db.commit()
    e = db.scalar(select(Existencia).where(Existencia.sucursal_id == suc, Existencia.variante_id == v))
    assert (e.disponible, e.reservada, e.vendida) == (10 - 4 + 1 - 2 + 1, 0, 3 + 2 - 1)
    assert db.query(MovimientoInventario).filter_by(variante_id=v).count() == 6


def test_13_el_nucleo_nunca_deja_cantidades_negativas_y_es_todo_o_nada(mundo, inv, db):
    import pytest
    from app.core.errors import Conflicto
    a, b = inv.v_sm_rojo["id"], inv.var[("M", "Rojo")]["id"]
    emp, suc = mundo.a.id, inv.centro.id
    aplicar_movimientos(db, emp, suc, [(a, 5)], "AJUSTE_ENTRADA", "MANUAL")
    db.commit()
    for tipo, mensaje in (("LIBERA_RESERVA", "No se pueden liberar"), ("DEVOLUCION", "No se pueden devolver"), ("VENTA_RESERVA", "No se pueden liberar")):
        with pytest.raises(Conflicto, match=mensaje):
            aplicar_movimientos(db, emp, suc, [(a, 1)], tipo, "VENTA")
        db.rollback()
    with pytest.raises(Conflicto, match="Stock insuficiente"):  # la segunda línea falla: la primera tampoco se aplica
        aplicar_movimientos(db, emp, suc, [(a, 2), (b, 1)], "VENTA", "VENTA")
    db.rollback()
    assert db.scalar(select(Existencia.disponible).where(Existencia.sucursal_id == suc, Existencia.variante_id == a)) == 5
    assert db.query(MovimientoInventario).count() == 1


def test_14_roles(inv, client):
    assert client.get("/api/inventario/sucursal", headers=inv.h_admin).status_code == 403  # el Administrador usa el inventario global
    for cabecera in (inv.h_cajero, inv.h_cliente, inv.h_prov):
        assert client.get("/api/inventario/sucursal", headers=cabecera).status_code == 403
        assert client.post("/api/inventario/sucursal/movimientos", json=_ajuste(inv.v_sm_rojo, 1), headers=cabecera).status_code == 403
        assert client.get("/api/inventario/movimientos", headers=cabecera).status_code == 403
        assert client.get("/api/inventario/recepciones", headers=cabecera).status_code == 403
    assert client.post("/api/inventario/sucursal/movimientos", json=_ajuste(inv.v_sm_rojo, 1), headers=inv.h_admin).status_code == 403


def test_15_aislamiento_entre_empresas(datos, mundo, inv, tienda_b, client):
    from tests.catalogo_util import entrar
    from tests.catalogo_util import talla_id
    suc_b = datos.sucursal(mundo.b, "Central B")
    datos.usuario(mundo.b, "Encargado", email="enc@b.com", sucursal=suc_b)
    h_b = entrar(client, mundo.b, "enc@b.com")
    # no puede ajustar una variante de la empresa A ni ver sus movimientos
    assert client.post("/api/inventario/sucursal/movimientos", json=_ajuste(inv.v_sm_rojo, 5), headers=h_b).status_code == 404
    client.post("/api/inventario/sucursal/movimientos", json=_ajuste(inv.v_sm_rojo, 5), headers=inv.h_enc_centro)
    assert client.get("/api/inventario/movimientos", headers=h_b).json()["total"] == 0
    assert client.put(f"/api/inventario/sucursal/variantes/{inv.v_sm_rojo['id']}/umbral", json={"umbral_minimo": 1}, headers=h_b).status_code == 404
    # ni recibir un lote de A
    lote = client.post("/api/abastecimiento/lotes", headers=inv.h_prov, json={
        "sucursal_id": inv.centro.id, "items": [{"sku": inv.v_sm_rojo["sku"], "cantidad": 3}]}).json()
    assert client.post(f"/api/inventario/recepciones/{lote['id']}/recibir", json={}, headers=h_b).status_code == 404
    assert client.get("/api/inventario/recepciones", headers=h_b).json() == []
    tienda_b.producto("Camisa B", tienda_b.camisas["id"], tienda_b.col["id"], [talla_id(tienda_b.alfa, "S")], [tienda_b.rojo["id"]])
    assert {x["producto"] for x in client.get("/api/inventario/sucursal", headers=h_b).json()["items"]} == {"Camisa B"}

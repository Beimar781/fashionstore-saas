"""CU-05 Consultar tallas, colores y disponibilidad por sucursal — caja negra, consulta agrupada y aislamiento."""
from sqlalchemy import event

from app.modules.inventario.publico import aplicar_movimientos


def _url(inv):
    return f"/api/inventario/productos/{inv.camisa['id']}/disponibilidad"


def _stock(mundo, inv, db):
    aplicar_movimientos(db, mundo.a.id, inv.centro.id, [(inv.var[("S", "Rojo")]["id"], 4), (inv.var[("M", "Azul")]["id"], 6)], "AJUSTE_ENTRADA", "MANUAL")
    aplicar_movimientos(db, mundo.a.id, inv.norte.id, [(inv.var[("S", "Azul")]["id"], 2)], "AJUSTE_ENTRADA", "MANUAL")
    db.commit()


def test_01_disponibilidad_de_la_prenda_en_cada_sucursal(mundo, inv, db, client):
    _stock(mundo, inv, db)
    r = client.get(_url(inv), headers=inv.h_cliente)
    assert r.status_code == 200
    por_nombre = {s["sucursal"]: s for s in r.json()["sucursales"]}
    centro, norte = por_nombre["Centro"], por_nombre["Norte"]
    assert (centro["total"], centro["tallas"], centro["colores"], centro["disponible"]) == (10, ["S", "M"], ["Azul", "Rojo"], True)
    assert (norte["total"], norte["tallas"], norte["colores"]) == (2, ["S"], ["Azul"])
    assert {(v["talla"], v["color"]): v["cantidad"] for v in centro["variantes"]} == {("S", "Rojo"): 4, ("M", "Azul"): 6, ("S", "Azul"): 0, ("M", "Rojo"): 0}


def test_02_primero_la_sucursal_con_mas_unidades_y_tallas_en_orden(mundo, inv, db, client):
    _stock(mundo, inv, db)
    r = client.get(_url(inv), headers=inv.h_cliente).json()
    assert [s["sucursal"] for s in r["sucursales"]] == ["Centro", "Norte"]
    assert [v["talla"] for v in r["sucursales"][0]["variantes"]] == ["S", "S", "M", "M"]  # S, M por orden de talla, no L, M, S


def test_03_sucursal_sin_unidades_aparece_como_no_disponible_y_las_inactivas_no(datos, mundo, inv, db, client):
    datos.sucursal(mundo.a, "Cerrada", activa=False)
    r = client.get(_url(inv), headers=inv.h_cliente).json()
    assert {s["sucursal"]: s["disponible"] for s in r["sucursales"]} == {"Centro": False, "Norte": False}


def test_04_una_variante_desactivada_no_se_muestra(mundo, inv, db, client):
    _stock(mundo, inv, db)
    client.put(f"/api/productos/{inv.camisa['id']}/variantes/{inv.var[('S', 'Rojo')]['id']}", json={"activa": False}, headers=inv.h_admin)
    centro = next(s for s in client.get(_url(inv), headers=inv.h_cliente).json()["sucursales"] if s["sucursal"] == "Centro")
    assert centro["total"] == 6 and ("S", "Rojo") not in {(v["talla"], v["color"]) for v in centro["variantes"]}


def test_05_una_sola_consulta_agrupada_de_existencias(mundo, inv, db, client, engine):
    _stock(mundo, inv, db)
    consultas = []
    contar = lambda conn, cursor, statement, *a: consultas.append(statement)  # noqa: E731
    event.listen(engine, "before_cursor_execute", contar)
    try:
        assert client.get(_url(inv), headers=inv.h_cliente).status_code == 200
    finally:
        event.remove(engine, "before_cursor_execute", contar)
    assert sum("existencias" in c for c in consultas) == 1  # no una por sucursal ni por variante


def test_06_todos_los_roles_consultan_y_el_superadmin_no(datos, inv, client):
    for cabecera in (inv.h_admin, inv.h_enc_centro, inv.h_cajero, inv.h_cliente):
        assert client.get(_url(inv), headers=cabecera).status_code == 200
    assert client.get(_url(inv), headers=inv.h_prov).status_code == 403
    assert client.get(_url(inv)).status_code == 401
    assert client.get(_url(inv), headers=datos.superadmin()).status_code == 403


def test_07_producto_retirado_inexistente_o_de_otra_empresa(inv, tienda_b, client):
    assert client.get(_url(inv), headers=tienda_b.h_admin).status_code == 404  # recurso de otra empresa
    assert client.get("/api/inventario/productos/99999/disponibilidad", headers=inv.h_cliente).status_code == 404
    client.post(f"/api/productos/{inv.camisa['id']}/desactivar", headers=inv.h_admin)
    r = client.get(_url(inv), headers=inv.h_cliente)
    assert r.status_code == 404 and r.json()["detail"] == "Producto no encontrado."

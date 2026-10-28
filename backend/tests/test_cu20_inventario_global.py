"""CU-20 Consultar inventario global — caja negra (estados de existencias), filtros, roles y aislamiento."""
from app.modules.inventario.publico import aplicar_movimientos


def _global(client, h, **params):
    r = client.get("/api/inventario/global", params=params, headers=h)
    assert r.status_code == 200, r.text
    return r.json()


def _armar(mundo, inv, db):
    """Camisa S/Rojo: Centro 10 (3 reservadas, 2 vendidas) y Norte 5. M/Rojo: Norte 2. Un lote de 8 S/Rojo viaja hacia Norte."""
    s_rojo, m_rojo = inv.v_sm_rojo["id"], inv.var[("M", "Rojo")]["id"]
    aplicar_movimientos(db, mundo.a.id, inv.centro.id, [(s_rojo, 15)], "AJUSTE_ENTRADA", "MANUAL")
    aplicar_movimientos(db, mundo.a.id, inv.centro.id, [(s_rojo, 3)], "RESERVA", "RESERVA", 1)
    aplicar_movimientos(db, mundo.a.id, inv.centro.id, [(s_rojo, 2)], "VENTA", "VENTA", 1)
    aplicar_movimientos(db, mundo.a.id, inv.norte.id, [(s_rojo, 5), (m_rojo, 2)], "AJUSTE_ENTRADA", "MANUAL")
    db.commit()


def test_01_consolida_las_existencias_de_todas_las_sucursales(mundo, inv, db, client, datos):
    _armar(mundo, inv, db)
    r = _global(client, inv.h_admin, q=inv.v_sm_rojo["sku"])
    fila = r["items"][0]
    assert (fila["disponible"], fila["reservada"], fila["vendida"]) == (10 + 5, 3, 2)  # 15-3-2 en Centro + 5 en Norte
    assert {s["sucursal"]: (s["disponibles"], s["reservadas"], s["vendidas"]) for s in r["por_sucursal"]} == {"Centro": (10, 3, 2), "Norte": (5, 0, 0)}


def test_02_resumen_disponibles_reservadas_vendidas_agotadas_y_proximas(mundo, inv, db, client):
    _armar(mundo, inv, db)
    client.post("/api/abastecimiento/lotes", headers=inv.h_prov, json={
        "sucursal_id": inv.norte.id, "items": [{"sku": inv.v_sm_rojo["sku"], "cantidad": 8}, {"sku": inv.var[("S", "Azul")]["sku"], "cantidad": 4}]})
    r = _global(client, inv.h_admin)
    assert r["resumen"] == {"disponibles": 17, "reservadas": 3, "vendidas": 2, "agotadas": 2, "proximas_a_ingresar": 12}
    assert r["total"] == 4  # las 4 variantes de la camisa


def test_03_filtro_por_estado(mundo, inv, db, client):
    _armar(mundo, inv, db)
    client.post("/api/abastecimiento/lotes", headers=inv.h_prov, json={
        "sucursal_id": inv.norte.id, "items": [{"sku": inv.var[("S", "Azul")]["sku"], "cantidad": 4}]})
    skus = lambda **f: sorted(x["sku"] for x in _global(client, inv.h_admin, **f)["items"])  # noqa: E731
    s_rojo, m_rojo, s_azul, m_azul = (inv.var[k]["sku"] for k in (("S", "Rojo"), ("M", "Rojo"), ("S", "Azul"), ("M", "Azul")))
    assert skus(estado="DISPONIBLE") == sorted([s_rojo, m_rojo])
    assert skus(estado="AGOTADA") == sorted([s_azul, m_azul])
    assert skus(estado="RESERVADA") == [s_rojo]
    assert skus(estado="VENDIDA") == [s_rojo]
    assert skus(estado="PROXIMA") == [s_azul]  # agotada hoy, pero viene en camino
    assert _global(client, inv.h_admin, estado="PROXIMA")["resumen"]["proximas_a_ingresar"] == 4


def test_04_filtro_por_sucursal(mundo, inv, db, client):
    _armar(mundo, inv, db)
    r = _global(client, inv.h_admin, sucursal=inv.norte.id)
    assert r["resumen"]["disponibles"] == 7 and r["resumen"]["reservadas"] == 0 and r["por_sucursal"] == []
    assert _global(client, inv.h_admin, sucursal=inv.centro.id)["resumen"]["disponibles"] == 10


def test_05_busqueda_por_categoria_temporada_y_texto(mundo, inv, db, client):
    _armar(mundo, inv, db)
    h = inv.h_admin
    from tests.catalogo_util import talla_id
    inv.producto("Jean Clásico", inv.pantalones["id"], inv.col["id"], [talla_id(inv.numerico, "30")], [inv.azul["id"]])
    assert _global(client, h)["total"] == 5
    assert _global(client, h, categoria_id=inv.pantalones["id"])["total"] == 1
    assert _global(client, h, q="jean")["items"][0]["producto"] == "Jean Clásico"
    assert _global(client, h, temporada_id=inv.temp["id"])["total"] == 5
    assert _global(client, h, categoria_id=inv.camisas["id"], estado="AGOTADA")["total"] == 2
    otra = inv.temporada("OI26", "Otoño 2026")
    assert _global(client, h, temporada_id=otra["id"])["total"] == 0


def test_06_paginacion_y_variantes_inactivas(mundo, inv, db, client):
    _armar(mundo, inv, db)
    h = inv.h_admin
    p = _global(client, h, tamano=3, pagina=2)
    assert (p["total"], len(p["items"])) == (4, 1)
    client.put(f"/api/productos/{inv.camisa['id']}/variantes/{inv.var[('M', 'Azul')]['id']}", json={"activa": False}, headers=h)
    assert _global(client, h)["total"] == 3  # una variante desactivada no cuenta
    assert client.get("/api/inventario/global?tamano=500", headers=h).status_code == 422


def test_07_sucursal_ajena_roles_y_sesion(datos, mundo, inv, client):
    ajena = datos.sucursal(mundo.b, "Ajena")
    r = client.get("/api/inventario/global", params={"sucursal": ajena.id}, headers=inv.h_admin)
    assert r.status_code == 404 and r.json()["detail"] == "Sucursal no encontrada."
    for cabecera in (inv.h_enc_centro, inv.h_cajero, inv.h_cliente, inv.h_prov):
        assert client.get("/api/inventario/global", headers=cabecera).status_code == 403
    assert client.get("/api/inventario/global").status_code == 401
    assert client.get("/api/inventario/global", headers=datos.superadmin()).status_code == 403


def test_08_aislamiento_entre_empresas(mundo, inv, tienda_b, db, client):
    _armar(mundo, inv, db)
    assert _global(client, tienda_b.h_admin) == {
        "resumen": {"disponibles": 0, "reservadas": 0, "vendidas": 0, "agotadas": 0, "proximas_a_ingresar": 0},
        "por_sucursal": [], "total": 0, "pagina": 1, "tamano": 25, "items": []}
    assert _global(client, inv.h_admin, q="oxford")["resumen"]["disponibles"] == 17

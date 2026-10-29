"""CU-22 Indicadores empresariales — KPIs con su variación frente al periodo anterior, inventario y alertas, plan y aislamiento."""
from sqlalchemy import text

from tests.reportes_util import envejecer, movimiento, sin_reportes


def test_01_los_indicadores_del_periodo(inv, mundo, client):
    movimiento(client, inv, mundo)
    r = client.get("/api/reportes/indicadores", params={"dias": 7}, headers=inv.h_admin)
    assert r.status_code == 200, r.text
    i = r.json()
    assert (i["dias"], i["ventas_netas"]["valor"], i["ventas"]["valor"], i["ticket_promedio"]["valor"]) == (7, 500.0, 3.0, 200.0)
    assert (i["reservas"]["valor"], i["conversion_reservas"]["valor"], i["productos_activos"]) == (2.0, 50.0, 1)
    assert i["ventas_netas"]["variacion"] is None  # no hubo ventas en el periodo anterior: no hay con qué comparar
    assert len(i["ventas_por_dia"]) == 7 and sum(d["ventas"] for d in i["ventas_por_dia"]) == 3
    assert {c["canal"] for c in i["por_canal"]} == {"DIGITAL", "PRESENCIAL"} and i["mas_vendidos"][0]["producto"] == "Camisa Oxford"
    assert len(i["ultimas_ventas"]) == 3 and i["ultimas_ventas"][0]["sucursal"] == "Centro"
    assert i["stock"]["disponibles"] > 0 and i["stock"]["vendidas"] > 0


def test_02_la_variacion_compara_con_el_periodo_anterior(inv, mundo, db, client):
    a, b, d = movimiento(client, inv, mundo)
    envejecer(db, d["id"], 10)  # la compra digital de Bs 300 pasa al periodo anterior de 7 días
    i = client.get("/api/reportes/indicadores", params={"dias": 7}, headers=inv.h_admin).json()
    assert (i["ventas_netas"]["valor"], i["ventas_netas"]["anterior"], i["ventas_netas"]["variacion"]) == (200.0, 300.0, -33.3)
    assert (i["ventas"]["valor"], i["ventas"]["anterior"], i["ventas"]["variacion"]) == (2.0, 1.0, 100.0)


def test_03_el_stock_bajo_sale_de_los_umbrales_de_la_sucursal(inv, mundo, db, client):
    movimiento(client, inv, mundo)
    assert client.get("/api/reportes/indicadores", headers=inv.h_admin).json()["stock_bajo_items"] == []
    db.execute(text("UPDATE existencias SET umbral_minimo = 50 WHERE variante_id = :v AND sucursal_id = :s"), {"v": inv.v_sm_rojo["id"], "s": inv.centro.id})
    db.commit()
    i = client.get("/api/reportes/indicadores", headers=inv.h_admin).json()
    assert i["stock"]["stock_bajo"] == 1
    assert [(s["sucursal"], s["producto"], s["sku"], s["umbral"]) for s in i["stock_bajo_items"]] == [("Centro", "Camisa Oxford", inv.v_sm_rojo["sku"], 50)]


def test_04_periodo_y_sucursal_validos(inv, mundo, client):
    movimiento(client, inv, mundo)
    r = client.get("/api/reportes/indicadores", params={"dias": 45}, headers=inv.h_admin)
    assert r.status_code == 422 and r.json()["detail"] == "El periodo debe ser de 7, 14, 30 o 90 días."
    norte = client.get("/api/reportes/indicadores", params={"sucursal": inv.norte.id}, headers=inv.h_admin).json()
    assert (norte["ventas"]["valor"], norte["reservas"]["valor"], norte["sucursal_id"]) == (0.0, 0.0, inv.norte.id)
    assert client.get("/api/reportes/indicadores", params={"sucursal": 99999}, headers=inv.h_admin).status_code == 404


def test_05_roles_plan_y_aislamiento(inv, mundo, tienda_b, db, client):
    movimiento(client, inv, mundo)
    for h in (inv.h_cajero, inv.h_enc_centro, inv.h_cliente):
        assert client.get("/api/reportes/indicadores", headers=h).status_code == 403
    assert client.get("/api/reportes/indicadores").status_code == 401
    otra = client.get("/api/reportes/indicadores", headers=tienda_b.h_admin).json()
    assert (otra["ventas_netas"]["valor"], otra["ventas"]["valor"], otra["productos_activos"], otra["ultimas_ventas"], otra["stock"]["disponibles"]) == (0.0, 0.0, 0, [], 0)
    sin_reportes(db, mundo)
    r = client.get("/api/reportes/indicadores", headers=inv.h_admin)
    assert r.status_code == 403 and r.json()["detail"] == "Su plan no incluye esta funcionalidad. Cambie al plan Profesional."

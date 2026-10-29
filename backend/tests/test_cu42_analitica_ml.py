"""CU-42 Analítica con Machine Learning — rotación (KMeans), pronóstico de demanda (regresión lineal), plan y aislamiento."""
from app.modules.ia.cu42_analitica_ml.service import clasificar_rotacion, proyectar, recomendar
from tests.reportes_util import con_ia, historial_semanal, movimiento
from tests.compras_util import stock_listo

MSG_PLAN = "Su plan no incluye esta funcionalidad. Cambie al plan Profesional."


def test_01_rotacion_con_kmeans_separa_alta_media_y_baja():
    datos = [("Jean", 60, 5), ("Polo", 55, 8), ("Camisa", 20, 30), ("Falda", 18, 25), ("Abrigo", 1, 40), ("Bufanda", 0, 50)]
    clases = clasificar_rotacion(datos)
    assert clases["Jean"] == clases["Polo"] == "ALTA" and clases["Camisa"] == clases["Falda"] == "MEDIA" and clases["Abrigo"] == clases["Bufanda"] == "BAJA"


def test_02_con_pocos_productos_se_usan_umbrales_fijos():
    assert clasificar_rotacion([("A", 60, 10), ("B", 10, 10)]) == {"A": "ALTA", "B": "MEDIA"}
    assert clasificar_rotacion([("A", 0, 10)]) == {"A": "BAJA"}


def test_03_la_regresion_detecta_la_tendencia():
    proy, tendencia, r2 = proyectar([2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13])
    assert tendencia == "SUBE" and proy == [14, 15, 16, 17] and r2 == 1.0
    assert proyectar([10] * 12)[1] == "ESTABLE"
    proy, tendencia, _ = proyectar([20, 18, 16, 14, 12, 10, 8, 6, 4, 2, 1, 0])
    assert tendencia == "BAJA" and all(v >= 0 for v in proy)  # la demanda proyectada nunca es negativa


def test_04_la_recomendacion_depende_del_stock():
    assert recomendar([10, 10, 10, 10], "ESTABLE", 20).startswith("Reponer")
    assert recomendar([1, 1, 0, 0], "BAJA", 50).startswith("Sobrestock")
    assert recomendar([5, 5, 5, 5], "ESTABLE", 40).startswith("Stock adecuado")


def test_05_con_pocas_ventas_no_se_pronostica(inv, mundo, db, client):
    con_ia(db, mundo)
    movimiento(client, inv, mundo)  # todas las ventas son de hoy: una sola semana
    r = client.get("/api/ia/analitica", headers=inv.h_admin)
    assert r.status_code == 200, r.text
    a = r.json()
    assert a["pronostico"] == [] and a["sin_historial_suficiente"] == 1 and a["mensaje"].startswith("Todavía no hay ventas suficientes")
    camisa = next(x for x in a["rotacion"] if x["producto"] == "Camisa Oxford")
    assert camisa["unidades_30d"] == 6 and camisa["clase"] in ("ALTA", "MEDIA", "BAJA") and camisa["tasa_diaria"] == 0.2
    assert "KMeans" in a["modelos"]["rotacion"] and "Regresión lineal" in a["modelos"]["pronostico"]


def test_06_con_historial_se_pronostica_la_demanda(inv, mundo, db, client):
    con_ia(db, mundo)
    stock_listo(inv, mundo, centro=10, norte=0)
    historial_semanal(db, inv, mundo, [2, 3, 4, 5, 6, 7, 8, 9])  # ocho semanas de ventas crecientes
    a = client.get("/api/ia/analitica", headers=inv.h_admin).json()
    p = a["pronostico"][0]
    assert (p["producto"], p["semanas_con_ventas"], p["tendencia"], len(p["proyeccion"]), p["historial"][-8:]) == ("Camisa Oxford", 8, "SUBE", 4, [2, 3, 4, 5, 6, 7, 8, 9])
    assert p["proyeccion"] == sorted(p["proyeccion"]) and p["proyeccion"][0] >= 10 and p["r2"] > 0.9
    assert p["recomendacion"].startswith("Reponer")  # la demanda proyectada supera el stock de 10 + 0 por variante
    historicas = [x for x in a["serie_total"] if not x["proyectada"]]
    assert len(historicas) == 12 and len([x for x in a["serie_total"] if x["proyectada"]]) == 4 and a["mensaje"] is None


def test_07_filtra_por_sucursal(inv, mundo, db, client):
    con_ia(db, mundo)
    stock_listo(inv, mundo)
    historial_semanal(db, inv, mundo, [2, 3, 4, 5])
    centro = client.get("/api/ia/analitica", params={"sucursal": inv.centro.id}, headers=inv.h_admin).json()
    norte = client.get("/api/ia/analitica", params={"sucursal": inv.norte.id}, headers=inv.h_admin).json()
    assert len(centro["pronostico"]) == 1 and norte["pronostico"] == []
    assert client.get("/api/ia/analitica", params={"sucursal": 99999}, headers=inv.h_admin).status_code == 404


def test_08_plan_roles_y_aislamiento(inv, mundo, tienda_b, db, client):
    r = client.get("/api/ia/analitica", headers=inv.h_admin)  # EMP-A tiene plan Básico
    assert r.status_code == 403 and r.json()["detail"] == MSG_PLAN
    con_ia(db, mundo)
    historial_semanal(db, inv, mundo, [2, 3, 4, 5, 6])
    for h in (inv.h_cajero, inv.h_enc_centro, inv.h_cliente):
        assert client.get("/api/ia/analitica", headers=h).status_code == 403
    b = client.get("/api/ia/analitica", headers=tienda_b.h_admin).json()  # EMP-B tiene IA pero ninguna venta de EMP-A
    assert (b["rotacion"], b["pronostico"], b["serie_total"][-1]["proyectada"]) == ([], [], False)

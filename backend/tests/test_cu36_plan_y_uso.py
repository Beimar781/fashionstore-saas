"""CU-36 Plan, límites y uso de la empresa — plan, vigencia, límite de sucursales, consumo y funcionalidades; también con la suscripción vencida."""
from datetime import timedelta

from sqlalchemy import text

from app.modules.reportes.base import hoy_local
from tests.reportes_util import con_ia, movimiento


def _plan(client, h):
    r = client.get("/api/mi-plan", headers=h)
    assert r.status_code == 200, r.text
    return r.json()


def test_01_plan_vigencia_y_funcionalidades(inv, mundo, client):
    p = _plan(client, inv.h_admin)
    assert (p["plan"]["nombre"], p["vigencia"]["estado"], p["vigencia"]["vigente"]) == ("Básico", "ACTIVA", True)
    assert p["vigencia"]["dias_restantes"] > 300
    f = {x["clave"]: x["incluida"] for x in p["funcionalidades"]}
    assert f == {"reportes_convencionales": True, "offline": True, "reportes_ia": False}


def test_02_limite_de_sucursales_y_aviso_al_alcanzarlo(inv, mundo, client):
    p = _plan(client, inv.h_admin)  # Centro y Norte activas, el plan Básico permite 2
    sucursales = next(x for x in p["limites"] if x["clave"] == "sucursales")
    assert (sucursales["usado"], sucursales["limite"], sucursales["porcentaje"], sucursales["alcanzado"]) == (2, 2, 100.0, True)
    assert "Alcanzó el límite de 2 sucursales activas de su plan." in p["alertas"]


def test_03_consumo_de_la_empresa(inv, mundo, db, client):
    con_ia(db, mundo)
    antes = {c["clave"]: c["valor"] for c in _plan(client, inv.h_admin)["consumo"]}
    assert set(antes) == {"usuarios", "productos", "ventas_mes", "consultas_ia"} and antes["productos"] == 1 and antes["ventas_mes"] == 0 and antes["consultas_ia"] == 0
    movimiento(client, inv, mundo)
    client.post("/api/ia/reportes", json={"prompt": "ventas de hoy"}, headers=inv.h_admin)
    despues = {c["clave"]: c["valor"] for c in _plan(client, inv.h_admin)["consumo"]}
    assert despues["ventas_mes"] == 3 and despues["consultas_ia"] == 1 and despues["usuarios"] >= 5


def test_04_aviso_de_vencimiento_cercano(inv, mundo, db, client):
    # la fecha de Bolivia (la que usa la app), no current_date de la base (UTC): entre las 20:00 y las 24:00 locales difieren en un día
    db.execute(text("UPDATE suscripciones SET fecha_vencimiento = :f WHERE empresa_id = :e"), {"e": mundo.a.id, "f": hoy_local() + timedelta(days=5)})
    db.commit()
    p = _plan(client, inv.h_admin)
    assert p["vigencia"]["dias_restantes"] == 5
    assert any(a.startswith("Su suscripción vence en") for a in p["alertas"])


def test_05_con_la_suscripcion_vencida_solo_se_ve_el_plan(inv, mundo, db, client):
    db.execute(text("UPDATE suscripciones SET estado = 'VENCIDA' WHERE empresa_id = :e"), {"e": mundo.a.id})
    db.commit()
    p = _plan(client, inv.h_admin)
    assert (p["plan"]["nombre"], p["vigencia"]["vigente"], p["vigencia"]["dias_restantes"], p["limites"], p["consumo"]) == ("Básico", False, None, [], [])
    assert p["alertas"] and "vencida" in p["alertas"][0]


def test_06_roles_y_aislamiento(inv, mundo, tienda_b, client):
    for h in (inv.h_cajero, inv.h_enc_centro, inv.h_cliente):
        assert client.get("/api/mi-plan", headers=h).status_code == 403
    assert client.get("/api/mi-plan").status_code == 401
    b = _plan(client, tienda_b.h_admin)
    assert b["plan"]["nombre"] == "Profesional" and next(f for f in b["funcionalidades"] if f["clave"] == "reportes_ia")["incluida"] is True
    assert next(x for x in b["limites"] if x["clave"] == "sucursales")["limite"] == 10
    assert {c["clave"]: c["valor"] for c in b["consumo"]}["productos"] == 0  # los productos de EMP-A no cuentan en EMP-B

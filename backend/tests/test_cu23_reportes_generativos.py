"""CU-23 Reportes generativos — interpretación por reglas (respaldo) y por IA (con un doble en memoria), validación, historial, plan y aislamiento."""
import json
from datetime import date

from app.core.ia import ClienteIA
from app.modules.ia.cu23_reportes_generativos import service
from app.modules.ia.cu23_reportes_generativos.interprete import interpretar_con_reglas
from tests.reportes_util import con_ia, movimiento

MSG_PLAN = "Su plan no incluye esta funcionalidad. Cambie al plan Profesional."


class ApiFalsa:
    """Imita la API de mensajes de Claude: devuelve el texto dado y guarda cómo se la llamó."""

    def __init__(self, texto, estado=200):
        self.texto, self.estado, self.llamadas = texto, estado, []

    def __call__(self, url, headers, json, timeout):
        self.llamadas.append((url, headers, json))
        return type("R", (), {"status_code": self.estado, "json": lambda s: {"content": [{"type": "text", "text": self.texto}]}})()


def _ia(monkeypatch, api):
    monkeypatch.setattr(service, "obtener_ia", lambda: ClienteIA("clave-de-prueba", "modelo-de-prueba", http=api))


def _generar(client, h, prompt):
    return client.post("/api/ia/reportes", json={"prompt": prompt}, headers=h)


def test_01_el_plan_basico_no_incluye_los_reportes_con_ia(inv, mundo, client):
    r = _generar(client, inv.h_admin, "ventas de hoy")
    assert r.status_code == 403 and r.json()["detail"] == MSG_PLAN
    assert client.get("/api/ia/reportes", headers=inv.h_admin).status_code == 403


def test_02_sin_clave_la_peticion_se_interpreta_con_reglas(inv, mundo, db, client):
    con_ia(db, mundo)
    movimiento(client, inv, mundo)
    r = _generar(client, inv.h_admin, "Dame las ventas de este mes")
    assert r.status_code == 201, r.text
    rep = r.json()
    assert rep["origen"] == "REGLAS" and rep["especificacion"]["ventas"] is True and rep["especificacion"]["etiqueta_periodo"] == "Mes en curso"
    assert "Ventas: Bs 500.00 netas en 3 venta(s), 6 prenda(s); ticket promedio Bs 200.00." in rep["texto"]
    assert "Incluye 1 devolución(es)/cambio(s)" in rep["texto"]
    assert rep["datos"]["ventas"]["ventas_netas"] == "500.00"


def test_03_ranking_de_productos_y_sucursal_por_nombre(inv, mundo, db, client):
    con_ia(db, mundo)
    movimiento(client, inv, mundo)
    rep = _generar(client, inv.h_admin, "cuál es el producto menos vendido de la sucursal centro este mes").json()
    assert (rep["especificacion"]["orden_ranking"], rep["especificacion"]["sucursal_id"], rep["especificacion"]["etiqueta_ambito"]) == ("peores", inv.centro.id, "Sucursal Centro")
    assert "Productos con menor venta:" in rep["texto"] and "1. Camisa Oxford — 5 u., Bs 500.00" in rep["texto"]


def test_04_reservas_pagos_e_inventario(inv, mundo, db, client):
    con_ia(db, mundo)
    movimiento(client, inv, mundo)
    rep = _generar(client, inv.h_admin, "reservas de este mes").json()
    assert "Reservas: 2 en total, 1 completadas (conversión 50.0%)." in rep["texto"]
    rep = _generar(client, inv.h_admin, "cómo van los pagos rechazados esta semana").json()
    assert "Pagos: 3 aprobados (Bs 600.00), 1 rechazados (Bs 100.00), 1 pendientes de confirmación (Bs 100.00)." in rep["texto"]
    rep = _generar(client, inv.h_admin, "estado del inventario").json()
    assert "Inventario:" in rep["texto"] and rep["datos"]["inventario"]["disponibles"] > 0


def test_05_una_peticion_sin_tema_da_un_resumen_general(inv, mundo, db, client):
    con_ia(db, mundo)
    movimiento(client, inv, mundo)
    rep = _generar(client, inv.h_admin, "dame un panorama").json()
    e = rep["especificacion"]
    assert (e["ventas"], e["reservas"], e["inventario"], e["ranking"]) == (True, True, True, True)


def test_06_la_peticion_vacia_o_demasiado_larga_se_rechaza(inv, mundo, db, client):
    con_ia(db, mundo)
    r = _generar(client, inv.h_admin, "   ")
    assert r.status_code == 422 and r.json()["detail"] == "Escriba o dicte lo que desea consultar."
    assert _generar(client, inv.h_admin, "ventas " * 100).status_code == 422


def test_07_con_clave_la_ia_propone_la_especificacion_y_se_valida(inv, mundo, db, client, monkeypatch):
    con_ia(db, mundo)
    movimiento(client, inv, mundo)
    api = ApiFalsa(json.dumps({"ventas": True, "ranking": True, "orden_ranking": "mejores", "desde": date.today().isoformat(), "hasta": date.today().isoformat(),
                               "sucursal_id": inv.centro.id, "etiqueta_periodo": "Hoy", "etiqueta_ambito": "Sucursal Centro"}))
    _ia(monkeypatch, api)
    rep = _generar(client, inv.h_admin, "lo que se vendió hoy y lo mejor").json()
    assert rep["origen"] == "IA" and rep["especificacion"]["sucursal_id"] == inv.centro.id and "Ventas: Bs 500.00" in rep["texto"]
    url, headers, cuerpo = api.llamadas[0]
    assert url.startswith("https://api.anthropic.com/") and headers["x-api-key"] == "clave-de-prueba" and cuerpo["model"] == "modelo-de-prueba"
    assert "lo que se vendió hoy" in cuerpo["messages"][0]["content"] and str(inv.centro.id) in cuerpo["messages"][0]["content"]


def test_08_si_la_ia_falla_o_propone_algo_invalido_se_usan_las_reglas(inv, mundo, db, client, monkeypatch):
    con_ia(db, mundo)
    movimiento(client, inv, mundo)
    for texto, estado in (("no es json", 200), ("{}", 200), (json.dumps({"ventas": True, "sucursal_id": 99999}), 200), (json.dumps({"ventas": True, "desde": "2026-12-31", "hasta": "2026-01-01"}), 200), ("{}", 500)):
        _ia(monkeypatch, ApiFalsa(texto, estado))
        rep = _generar(client, inv.h_admin, "ventas de hoy").json()
        assert rep["origen"] == "REGLAS" and rep["especificacion"]["ventas"] is True, (texto, estado)


def test_09_la_ia_sin_clave_no_llama_a_la_api():
    api = ApiFalsa("{}")
    assert ClienteIA("", "m", http=api).json_estructurado("s", "u") is None and api.llamadas == []


def test_10_las_reglas_entienden_periodos_y_listados():
    hoy = date(2026, 10, 29)
    sucursales = [(1, "Sucursal Centro"), (2, "Sucursal Norte")]
    assert interpretar_con_reglas("ventas de ayer", hoy, sucursales).etiqueta_periodo == "Ayer"
    e = interpretar_con_reglas("listado de ventas del 2026-10-01 a 2026-10-15 en la sucursal norte", hoy, sucursales)
    assert (e.detalle_ventas, e.limite_detalle, str(e.desde), str(e.hasta), e.sucursal_id) == (True, 50, "2026-10-01", "2026-10-15", 2)
    e = interpretar_con_reglas("top 3 productos mes pasado", hoy, sucursales)
    assert (e.limite_ranking, str(e.desde), str(e.hasta)) == (3, "2026-09-01", "2026-09-30")


def test_11_historial_y_aislamiento(inv, mundo, tienda_b, db, client):
    con_ia(db, mundo)
    movimiento(client, inv, mundo)
    rep = _generar(client, inv.h_admin, "ventas de hoy").json()
    assert [r["id"] for r in client.get("/api/ia/reportes", headers=inv.h_admin).json()] == [rep["id"]]
    assert client.get(f"/api/ia/reportes/{rep['id']}", headers=inv.h_admin).json()["texto"] == rep["texto"]
    assert client.get("/api/ia/reportes", headers=tienda_b.h_admin).json() == []  # EMP-B tiene IA, pero no ve lo de EMP-A
    r = client.get(f"/api/ia/reportes/{rep['id']}", headers=tienda_b.h_admin)
    assert r.status_code == 404 and r.json()["detail"] == "Reporte no encontrado."
    b = _generar(client, tienda_b.h_admin, "ventas de hoy").json()
    assert "Ventas: Bs 0.00" in b["texto"]


def test_12_solo_el_administrador(inv, mundo, db, client):
    con_ia(db, mundo)
    for h in (inv.h_cajero, inv.h_enc_centro, inv.h_cliente):
        assert _generar(client, h, "ventas").status_code == 403
        assert client.get("/api/ia/reportes", headers=h).status_code == 403
    assert client.post("/api/ia/reportes", json={"prompt": "ventas"}).status_code == 401

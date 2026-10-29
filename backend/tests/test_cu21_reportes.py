"""CU-21 Reportes de ventas y reservas — ventas netas de devoluciones, reservas, vista de pagos, exportación, plan y aislamiento."""
from datetime import timedelta

from app.modules.reportes.publico import hoy_local
from tests.reportes_util import movimiento, sin_reportes


def test_01_ventas_digitales_y_presenciales_netas_de_devoluciones(inv, mundo, client):
    movimiento(client, inv, mundo)
    r = client.get("/api/reportes/ventas", headers=inv.h_admin)
    assert r.status_code == 200, r.text
    v = r.json()
    assert v["totales"] == {
        "ventas": 3, "unidades": 6, "total_bruto": "600.00", "devoluciones": 1, "devuelto": "100.00", "entregado_en_cambios": "0.00",
        "ventas_netas": "500.00", "ticket_promedio": "200.00",
    }
    canales = {c["canal"]: c for c in v["por_canal"]}
    assert (canales["PRESENCIAL"]["ventas"], canales["PRESENCIAL"]["total"], canales["DIGITAL"]["ventas"], canales["DIGITAL"]["total"]) == (2, "300.00", 1, "300.00")
    metodos = {m["metodo"]: m for m in v["por_metodo"]}
    assert (metodos["EFECTIVO"]["total"], metodos["TARJETA"]["cobros"], metodos["TARJETA"]["total"]) == ("200.00", 2, "400.00")
    assert [(s["sucursal"], s["ventas"], s["total"]) for s in v["por_sucursal"]] == [("Centro", 3, "600.00")]
    assert sum(d["ventas"] for d in v["por_dia"]) == 3 and v["por_dia"][-1]["fecha"] == hoy_local().isoformat() and len(v["por_dia"]) == 30


def test_02_los_productos_se_miden_netos_de_devoluciones(inv, mundo, client):
    movimiento(client, inv, mundo)
    v = client.get("/api/reportes/ventas", headers=inv.h_admin).json()
    mas = {p["producto"]: p for p in v["mas_vendidos"]}
    assert (mas["Camisa Oxford"]["unidades"], mas["Camisa Oxford"]["ingresos"]) == (6 - 1, "500.00")  # 6 vendidas menos 1 devuelta
    assert v["menos_vendidos"][0]["producto"] == "Camisa Oxford"


def test_03_filtro_por_canal_y_sucursal(inv, mundo, client):
    movimiento(client, inv, mundo)
    digital = client.get("/api/reportes/ventas", params={"canal": "DIGITAL"}, headers=inv.h_admin).json()
    assert (digital["totales"]["total_bruto"], digital["totales"]["devuelto"], digital["totales"]["ventas_netas"]) == ("300.00", "0.00", "300.00")  # la devolución fue de una venta de caja
    presencial = client.get("/api/reportes/ventas", params={"canal": "PRESENCIAL"}, headers=inv.h_admin).json()
    assert (presencial["totales"]["total_bruto"], presencial["totales"]["ventas_netas"]) == ("300.00", "200.00")
    norte = client.get("/api/reportes/ventas", params={"sucursal": inv.norte.id}, headers=inv.h_admin).json()
    assert (norte["totales"]["ventas"], norte["totales"]["ventas_netas"], norte["por_sucursal"]) == (0, "0.00", [])
    assert client.get("/api/reportes/ventas", params={"canal": "OTRO"}, headers=inv.h_admin).status_code == 422


def test_04_el_periodo_se_valida_y_acota_los_datos(inv, mundo, client):
    movimiento(client, inv, mundo)
    ayer = (hoy_local() - timedelta(days=1)).isoformat()
    r = client.get("/api/reportes/ventas", params={"desde": ayer, "hasta": ayer}, headers=inv.h_admin).json()
    assert r["totales"]["ventas"] == 0 and len(r["por_dia"]) == 1  # todo ocurrió hoy
    r = client.get("/api/reportes/ventas", params={"desde": hoy_local().isoformat(), "hasta": ayer}, headers=inv.h_admin)
    assert r.status_code == 422 and r.json()["detail"] == "La fecha inicial no puede ser posterior a la final."
    r = client.get("/api/reportes/ventas", params={"desde": (hoy_local() - timedelta(days=400)).isoformat()}, headers=inv.h_admin)
    assert r.status_code == 422 and r.json()["detail"] == "El periodo no puede superar 366 días."
    r = client.get("/api/reportes/ventas", params={"sucursal": 99999}, headers=inv.h_admin)
    assert r.status_code == 404 and r.json()["detail"] == "Sucursal no encontrada."


def test_05_reservas_con_su_conversion(inv, mundo, client):
    movimiento(client, inv, mundo)
    r = client.get("/api/reportes/reservas", headers=inv.h_admin)
    assert r.status_code == 200, r.text
    rep = r.json()
    estados = {e["estado"]: e["cantidad"] for e in rep["por_estado"]}
    assert (rep["total"], rep["completadas"], rep["conversion"], estados["COMPLETADA"], estados["PENDIENTE"]) == (2, 1, 50.0, 1, 1)
    assert [(s["sucursal"], s["reservas"], s["completadas"]) for s in rep["por_sucursal"]] == [("Centro", 2, 1)]
    assert rep["por_dia"][0]["reservas"] == 2


def test_06_vista_de_pagos_aprobados_rechazados_y_pendientes(inv, mundo, client):
    movimiento(client, inv, mundo)
    r = client.get("/api/reportes/pagos", headers=inv.h_admin)
    assert r.status_code == 200, r.text
    p = r.json()
    assert (p["aprobados"], p["rechazados"], p["pendientes_confirmacion"]) == (
        {"cantidad": 3, "monto": "600.00"}, {"cantidad": 1, "monto": "100.00"}, {"cantidad": 1, "monto": "100.00"})
    problemas = {x["estado"]: x for x in p["con_problemas"]}
    assert problemas["RECHAZADO"]["metodo"] == "TARJETA" and problemas["RECHAZADO"]["sucursal"] == "Centro" and problemas["RECHAZADO"]["motivo"]
    assert problemas["PENDIENTE_CONFIRMACION"]["tarjeta"] == "" or problemas["PENDIENTE_CONFIRMACION"]["monto"] == "100.00"
    metodos = {(m["metodo"], m["estado"]): m["cantidad"] for m in p["por_metodo"]}
    assert metodos[("EFECTIVO", "APROBADO")] == 1 and metodos[("TARJETA", "APROBADO")] == 2


def test_07_exportar_csv(inv, mundo, client):
    movimiento(client, inv, mundo)
    r = client.get("/api/reportes/exportar/ventas", headers=inv.h_admin)
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv") and "attachment" in r.headers["content-disposition"]
    lineas = r.text.lstrip("﻿").strip().splitlines()
    assert lineas[0] == "comprobante,pedido,fecha,canal,sucursal,total" and len(lineas) == 4
    assert len(client.get("/api/reportes/exportar/reservas", headers=inv.h_admin).text.strip().splitlines()) == 3
    assert client.get("/api/reportes/exportar/pagos", headers=inv.h_admin).status_code == 200
    r = client.get("/api/reportes/exportar/clientes", headers=inv.h_admin)
    assert r.status_code == 422 and r.json()["detail"] == "Tipo de exportación no soportado. Use ventas, reservas o pagos."


def test_08_solo_el_administrador_y_con_el_plan_adecuado(inv, mundo, db, client):
    for ruta in ("ventas", "reservas", "pagos", "exportar/ventas"):
        for h in (inv.h_cajero, inv.h_enc_centro, inv.h_cliente):
            assert client.get(f"/api/reportes/{ruta}", headers=h).status_code == 403
        assert client.get(f"/api/reportes/{ruta}").status_code == 401
    sin_reportes(db, mundo)
    r = client.get("/api/reportes/ventas", headers=inv.h_admin)
    assert r.status_code == 403 and r.json()["detail"] == "Su plan no incluye esta funcionalidad. Cambie al plan Profesional."


def test_09_aislamiento_entre_empresas(inv, mundo, tienda_b, client):
    movimiento(client, inv, mundo)
    v = client.get("/api/reportes/ventas", headers=tienda_b.h_admin).json()
    assert (v["totales"]["ventas"], v["totales"]["total_bruto"], v["por_sucursal"], v["mas_vendidos"]) == (0, "0.00", [], [])
    assert client.get("/api/reportes/pagos", headers=tienda_b.h_admin).json()["rechazados"]["cantidad"] == 0
    assert client.get("/api/reportes/reservas", headers=tienda_b.h_admin).json()["total"] == 0
    r = client.get("/api/reportes/ventas", params={"sucursal": inv.centro.id}, headers=tienda_b.h_admin)  # una sucursal de otra empresa no existe
    assert r.status_code == 404

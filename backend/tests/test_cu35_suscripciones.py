"""CU-35 Gestionar suscripciones de empresas — caja negra."""
from datetime import date, timedelta

from fastapi import Depends

from app.main import app
from app.modules.plataforma.models import Suscripcion
from app.modules.plataforma.publico import exigir_funcionalidad


def _asignar(plan_id, inicio=None, venc=None, meses=12, pago="QR"):
    body = {"plan_id": plan_id, "fecha_inicio": str(inicio or date.today()), "forma_pago": pago}
    if venc:
        body["fecha_vencimiento"] = str(venc)
    else:
        body["duracion_meses"] = meses
    return body


def test_01_asignar_plan_cierra_la_anterior(datos, mundo, client, db):
    h = datos.superadmin()
    r = client.post(f"/api/plataforma/empresas/{mundo.a.id}/suscripciones", json=_asignar(mundo.pro.id), headers=h)
    assert r.status_code == 201 and r.json()["estado"] == "ACTIVA" and r.json()["plan"]["nombre"] == "Profesional"
    assert r.json()["forma_pago"] == "QR"
    estados = [s.estado for s in db.query(Suscripcion).filter_by(empresa_id=mundo.a.id).order_by(Suscripcion.id)]
    assert estados == ["VENCIDA", "ACTIVA"]  # la anterior se cierra y queda en el historial
    det = client.get(f"/api/plataforma/empresas/{mundo.a.id}/suscripcion", headers=h).json()
    assert len(det["historial"]) == 2 and det["uso"]["limite"] == 10


def test_02_cambio_a_plan_con_limite_menor(datos, mundo, client):
    for i in range(4):
        datos.sucursal(mundo.b, f"B{i}")
    h = datos.superadmin()
    r = client.post(f"/api/plataforma/empresas/{mundo.b.id}/suscripciones", json=_asignar(mundo.basico.id), headers=h)
    assert r.status_code == 409
    assert r.json()["detail"] == "La empresa tiene 4 sucursales activas; el plan elegido permite 2. Desactive sucursales antes de cambiar."


def test_03_fechas_invalidas(datos, mundo, client):
    h = datos.superadmin()
    hoy = date.today()
    r = client.post(f"/api/plataforma/empresas/{mundo.a.id}/suscripciones", headers=h,
                    json=_asignar(mundo.pro.id, inicio=hoy, venc=hoy))
    assert r.status_code == 422 and r.json()["detail"] == "La fecha de vencimiento debe ser posterior a la de inicio."


def test_04_vencimiento_automatico_y_restriccion(datos, client, db):
    plan = datos.plan()
    e = datos.empresa("EMP-V", plan, venc=date.today() - timedelta(days=1), inicio=date.today() - timedelta(days=30))
    h = datos.superadmin()
    det = client.get(f"/api/plataforma/empresas/{e.id}/suscripcion", headers=h).json()
    assert det["vigente"]["estado"] == "VENCIDA"
    assert client.get("/api/plataforma/empresas", headers=h).json()[0]["suscripcion_estado"] == "VENCIDA"


def test_05_renovar_suscripcion_vencida(datos, client):
    plan = datos.plan()
    e = datos.empresa("EMP-V", plan, venc=date.today() - timedelta(days=1), inicio=date.today() - timedelta(days=30))
    admin = datos.usuario(e)
    h = datos.superadmin()
    assert client.get(f"/api/plataforma/empresas/{e.id}/suscripcion", headers=h).json()["vigente"]["estado"] == "VENCIDA"
    r = client.post(f"/api/plataforma/empresas/{e.id}/suscripciones", json=_asignar(plan.id, meses=6), headers=h)
    assert r.status_code == 201 and r.json()["estado"] == "ACTIVA"
    ha = datos.login(admin, e)                       # recupera sus operaciones
    assert client.get("/api/usuarios", headers=ha).status_code == 200


def test_06_funcionalidad_ia_segun_plan(datos, mundo, client):
    app.add_api_route("/api/_prueba/reportes-ia", lambda ctx=Depends(exigir_funcionalidad("reportes_ia")): {"ok": True}, methods=["GET"])
    ha, hb = datos.login(mundo.admin_a, mundo.a), datos.login(mundo.admin_b, mundo.b)
    assert client.get("/api/_prueba/reportes-ia", headers=ha).status_code == 403   # Básico: bloqueado
    assert client.get("/api/_prueba/reportes-ia", headers=hb).status_code == 200   # Profesional: permitido


def test_suspender_y_asignar_a_empresa_suspendida(datos, mundo, client):
    h = datos.superadmin()
    r = client.post(f"/api/plataforma/empresas/{mundo.a.id}/suscripcion/suspender", json={"estado": "SUSPENDIDA"}, headers=h)
    assert r.json()["estado"] == "SUSPENDIDA"
    client.post(f"/api/plataforma/empresas/{mundo.a.id}/suspender", headers=h)
    r2 = client.post(f"/api/plataforma/empresas/{mundo.a.id}/suscripciones", json=_asignar(mundo.pro.id), headers=h)
    assert r2.status_code == 409  # empresa suspendida: no se asigna plan hasta reactivarla

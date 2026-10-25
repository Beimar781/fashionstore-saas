"""CU-33 Gestionar empresas (tenants) — caja negra."""
from datetime import date

from app.modules.acceso.models import Usuario
from app.modules.plataforma.models import Empresa, Suscripcion
from app.modules.plataforma.cu35_suscripciones.repository import SuscripcionRepository


def _empresa(plan_id, codigo="EMP-N", nit="900100200"):
    return {
        "codigo": codigo, "razon_social": "Nueva SRL", "nit": nit, "email_contacto": "info@nueva.com", "telefono": "7123",
        "administrador": {"nombre": "Ada", "apellidos": "Lovelace", "email": "ada@nueva.com", "password": "Segura123"},
        "suscripcion": {"plan_id": plan_id, "fecha_inicio": str(date.today()), "duracion_meses": 12, "forma_pago": "qr"},
    }


def test_01_registrar_empresa_valida(datos, client, db):
    plan = datos.plan()
    h = datos.superadmin()
    r = client.post("/api/plataforma/empresas", json=_empresa(plan.id), headers=h)
    assert r.status_code == 201
    j = r.json()
    assert j["codigo"] == "EMP-N" and j["plan"] == "Básico" and j["suscripcion_estado"] == "ACTIVA"
    assert db.query(Usuario).filter_by(empresa_id=j["id"]).count() == 1
    assert db.query(Suscripcion).filter_by(empresa_id=j["id"], estado="ACTIVA").count() == 1


def test_02_codigo_o_nit_duplicado(datos, client):
    plan = datos.plan()
    h = datos.superadmin()
    client.post("/api/plataforma/empresas", json=_empresa(plan.id), headers=h)
    for dup in (_empresa(plan.id, nit="otro-nit"), _empresa(plan.id, codigo="OTRO")):
        r = client.post("/api/plataforma/empresas", json=dup, headers=h)
        assert r.status_code == 409 and r.json()["detail"] == "Ya existe una empresa con ese código/NIT."


def test_03_transaccion_atomica(datos, client, db, monkeypatch):
    plan = datos.plan()
    h = datos.superadmin()

    def falla(self, sus):
        raise RuntimeError("falla simulada al crear la suscripción")

    monkeypatch.setattr(SuscripcionRepository, "agregar", falla)
    r = client.post("/api/plataforma/empresas", json=_empresa(plan.id), headers=h)
    assert r.status_code == 500
    db.expire_all()
    assert db.query(Empresa).filter_by(codigo="EMP-N").count() == 0     # rollback total
    assert db.query(Usuario).filter_by(email="ada@nueva.com").count() == 0


def test_04_suspender_empresa(datos, mundo, client):
    h = datos.superadmin()
    assert client.post(f"/api/plataforma/empresas/{mundo.a.id}/suspender", headers=h).json()["estado"] == "SUSPENDIDA"
    r = client.post("/api/auth/login", json={"codigo_empresa": "EMP-A", "email": mundo.admin_a.email, "password": "Clave1234"})
    assert r.status_code == 403
    assert client.get("/api/plataforma/empresas", headers=h).json()[0]["codigo"]            # datos conservados
    assert client.post(f"/api/plataforma/empresas/{mundo.a.id}/reactivar", headers=h).json()["estado"] == "ACTIVA"


def test_05_no_superadmin_recibe_403(datos, mundo, client):
    h = datos.login(mundo.admin_a, mundo.a)
    assert client.get("/api/plataforma/empresas", headers=h).status_code == 403
    assert client.post("/api/plataforma/empresas", json={}, headers=h).status_code == 403


def test_06_eliminar_no_permitido(datos, mundo, client, db):
    h = datos.superadmin()
    r = client.delete(f"/api/plataforma/empresas/{mundo.a.id}", headers=h)
    assert r.status_code == 409 and "baja lógica" in r.json()["detail"]
    assert db.get(Empresa, mundo.a.id) is not None


def test_admin_obligatorio(datos, client):
    plan = datos.plan()
    h = datos.superadmin()
    body = _empresa(plan.id); body.pop("administrador")
    r = client.post("/api/plataforma/empresas", json=body, headers=h)
    assert r.status_code == 422 and r.json()["detail"] == "Debe registrar un administrador para la empresa."


def test_listado_con_plan_y_vencimiento(datos, mundo, client):
    h = datos.superadmin()
    filas = {e["codigo"]: e for e in client.get("/api/plataforma/empresas", headers=h).json()}
    assert filas["EMP-A"]["plan"] == "Básico" and filas["EMP-B"]["plan"] == "Profesional"
    assert filas["EMP-A"]["fecha_vencimiento"] and filas["EMP-A"]["suscripcion_estado"] == "ACTIVA"

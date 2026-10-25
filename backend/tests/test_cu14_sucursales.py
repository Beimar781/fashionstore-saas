"""CU-14 Gestionar ciudades y sucursales — caja negra."""
from datetime import date, timedelta

from app.modules.plataforma.models import Plan


def _suc(nombre, ciudad_nombre="Santa Cruz"):
    return {"nombre": nombre, "ciudad_nombre": ciudad_nombre, "direccion": "Av. 1", "telefono": "7000", "horario": "9-18"}


def test_01_crear_con_cupo(datos, mundo, client):
    datos.sucursal(mundo.a, "S1")
    h = datos.login(mundo.admin_a, mundo.a)
    assert client.post("/api/sucursales", json=_suc("S2"), headers=h).status_code == 201
    uso = client.get("/api/sucursales", headers=h).json()["uso_plan"]
    assert (uso["activas"], uso["limite"]) == (2, 2)  # "uso del plan 2 de 2"


def test_02_sin_cupo(datos, mundo, client):
    datos.sucursal(mundo.a, "S1"); datos.sucursal(mundo.a, "S2")
    h = datos.login(mundo.admin_a, mundo.a)
    r = client.post("/api/sucursales", json=_suc("S3"), headers=h)
    assert r.status_code == 409
    assert r.json()["detail"] == "Su plan permite hasta 2 sucursales activas. Desactive una sucursal o cambie de plan."


def test_03_reactivar_sin_cupo(datos, mundo, client):
    datos.sucursal(mundo.a, "S1"); datos.sucursal(mundo.a, "S2"); s3 = datos.sucursal(mundo.a, "S3", activa=False)
    h = datos.login(mundo.admin_a, mundo.a)
    r = client.post(f"/api/sucursales/{s3.id}/activar", headers=h)
    assert r.status_code == 409 and "Su plan permite hasta 2 sucursales activas" in r.json()["detail"]


def test_04_nombre_duplicado(datos, mundo, client):
    datos.sucursal(mundo.a, "S1")
    h = datos.login(mundo.admin_a, mundo.a)
    r = client.post("/api/sucursales", json=_suc("s1"), headers=h)
    assert r.status_code == 409 and r.json()["detail"] == "Ya existe una sucursal con ese nombre."


def test_05_mismo_nombre_en_otra_empresa(datos, mundo, client):
    datos.sucursal(mundo.b, "Central")
    h = datos.login(mundo.admin_a, mundo.a)
    assert client.post("/api/sucursales", json=_suc("Central"), headers=h).status_code == 201


def test_06_suscripcion_no_vigente_bloquea(datos, client):
    plan = datos.plan()
    e = datos.empresa("EMP-V", plan, venc=date.today() - timedelta(days=1), inicio=date.today() - timedelta(days=30))
    admin = datos.usuario(e)
    r0 = client.post("/api/auth/login", json={"codigo_empresa": "EMP-V", "email": admin.email, "password": "Clave1234"})
    h = {"Authorization": f"Bearer {r0.json()['access_token']}"}
    r = client.post("/api/sucursales", json=_suc("Nueva"), headers=h)
    assert r.status_code == 403 and r.json()["detail"] == "La suscripción de su empresa no está vigente."


def test_07_limite_configurable_sin_cambiar_codigo(datos, mundo, client, db):
    datos.sucursal(mundo.a, "S1"); datos.sucursal(mundo.a, "S2")
    h = datos.login(mundo.admin_a, mundo.a)
    assert client.post("/api/sucursales", json=_suc("S3"), headers=h).status_code == 409
    db.query(Plan).filter_by(id=mundo.basico.id).update({"max_sucursales": 3}); db.commit()
    assert client.post("/api/sucursales", json=_suc("S3"), headers=h).status_code == 201


def test_ciudades(datos, mundo, client):
    h = datos.login(mundo.admin_a, mundo.a)
    assert client.post("/api/ciudades", json={"nombre": "Cochabamba"}, headers=h).status_code == 201
    assert client.post("/api/ciudades", json={"nombre": "cochabamba"}, headers=h).status_code == 409
    nombres = [c["nombre"] for c in client.get("/api/ciudades", headers=h).json()]
    assert "Cochabamba" in nombres


def test_desactivar_libera_cupo(datos, mundo, client):
    s1 = datos.sucursal(mundo.a, "S1"); datos.sucursal(mundo.a, "S2")
    h = datos.login(mundo.admin_a, mundo.a)
    assert client.post(f"/api/sucursales/{s1.id}/desactivar", headers=h).json()["activa"] is False
    assert client.post("/api/sucursales", json=_suc("S3"), headers=h).status_code == 201

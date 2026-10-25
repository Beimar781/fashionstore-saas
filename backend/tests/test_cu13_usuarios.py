"""CU-13 Gestionar usuarios y roles — caja negra."""
from app.core.constantes import ADMIN, CAJERO, ENCARGADO
from app.modules.acceso.models import Usuario


def _nuevo(email="nuevo@a.com", rol=CAJERO, sucursal_id=None, password="Segura123"):
    return {"nombre": "Nuevo", "apellidos": "Usuario", "email": email, "password": password, "rol": rol, "sucursal_id": sucursal_id}


def test_01_registrar_cajero_con_hash(datos, mundo, client, db):
    h = datos.login(mundo.admin_a, mundo.a)
    suc = datos.sucursal(mundo.a, "Central")
    r = client.post("/api/usuarios", json=_nuevo(sucursal_id=suc.id), headers=h)
    assert r.status_code == 201
    u = db.get(Usuario, r.json()["id"])
    assert u.empresa_id == mundo.a.id and u.password_hash != "Segura123" and u.password_hash.startswith("$argon2")


def test_02_correo_duplicado_en_la_empresa(datos, mundo, client):
    h = datos.login(mundo.admin_a, mundo.a)
    suc = datos.sucursal(mundo.a, "Central")
    client.post("/api/usuarios", json=_nuevo(sucursal_id=suc.id), headers=h)
    r = client.post("/api/usuarios", json=_nuevo(sucursal_id=suc.id), headers=h)
    assert r.status_code == 409 and r.json()["detail"] == "Este correo ya está en uso."


def test_03_sucursal_de_otra_empresa(datos, mundo, client):
    h = datos.login(mundo.admin_a, mundo.a)
    suc_b = datos.sucursal(mundo.b, "Sucursal B")
    r = client.post("/api/usuarios", json=_nuevo(sucursal_id=suc_b.id), headers=h)
    assert r.status_code == 404 and r.json()["detail"] == "El recurso no pertenece a su empresa."


def test_04_no_puede_asignar_superadministrador(datos, mundo, client):
    h = datos.login(mundo.admin_a, mundo.a)
    r = client.post("/api/usuarios", json=_nuevo(rol="SuperAdministrador"), headers=h)
    assert r.status_code == 403 and r.json()["detail"] == "No tiene permisos para asignar este rol."


def test_05_unico_administrador_no_se_desactiva(datos, mundo, client):
    h = datos.login(mundo.admin_a, mundo.a)
    r = client.post(f"/api/usuarios/{mundo.admin_a.id}/desactivar", headers=h)
    assert r.status_code == 409 and "al menos un administrador activo" in r.json()["detail"]
    r2 = client.put(f"/api/usuarios/{mundo.admin_a.id}", json={"rol": CAJERO, "sucursal_id": None}, headers=h)
    assert r2.status_code in (409, 422)  # tampoco se le quita el rol (RN03)


def test_05b_con_dos_administradores_si_se_puede(datos, mundo, client):
    otro = datos.usuario(mundo.a, ADMIN, email="otro-admin@a.com")
    h = datos.login(mundo.admin_a, mundo.a)
    assert client.post(f"/api/usuarios/{otro.id}/desactivar", headers=h).json()["activo"] is False


def test_06_listar_solo_la_empresa_del_token(datos, mundo, client):
    datos.usuario(mundo.b, CAJERO, email="cajero@b.com", sucursal=datos.sucursal(mundo.b, "Suc B"))
    h = datos.login(mundo.admin_a, mundo.a)
    emails = [u["email"] for u in client.get("/api/usuarios", headers=h).json()]
    assert mundo.admin_a.email in emails and "cajero@b.com" not in emails and mundo.admin_b.email not in emails


def test_07_contrasena_debil(datos, mundo, client):
    h = datos.login(mundo.admin_a, mundo.a)
    suc = datos.sucursal(mundo.a, "Central")
    r = client.post("/api/usuarios", json=_nuevo(sucursal_id=suc.id, password="12345"), headers=h)
    assert r.status_code == 422 and r.json()["detail"] == "La contraseña debe tener al menos 8 caracteres."


def test_cajero_sin_sucursal(datos, mundo, client):
    h = datos.login(mundo.admin_a, mundo.a)
    r = client.post("/api/usuarios", json=_nuevo(), headers=h)
    assert r.status_code == 422 and r.json()["detail"] == "Debe asignar una sucursal."


def test_solo_administrador_accede(datos, mundo, client):
    suc = datos.sucursal(mundo.a, "Central")
    cajero = datos.usuario(mundo.a, CAJERO, sucursal=suc)
    h = datos.login(cajero, mundo.a)
    assert client.get("/api/usuarios", headers=h).status_code == 403

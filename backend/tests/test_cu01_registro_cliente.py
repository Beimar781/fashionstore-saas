"""CU-01 Registrar cuenta de cliente — caja negra."""
from datetime import date, timedelta

CUENTA = {"codigo_empresa": "EMP-A", "nombre": "Lucía", "apellidos": "Pérez", "email": "Lucia@Correo.com", "password": "Clave1234"}


def test_01_registro_correcto_inicia_sesion_como_cliente(mundo, client):
    r = client.post("/api/auth/registro", json=CUENTA)
    assert r.status_code == 201
    datos = r.json()
    assert datos["usuario"]["rol"] == "Cliente" and datos["usuario"]["email"] == "lucia@correo.com"
    assert datos["empresa"]["codigo"] == "EMP-A" and datos["panel"] == "catalogo" and datos["access_token"]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {datos['access_token']}"})
    assert me.status_code == 200 and me.json()["usuario"]["rol"] == "Cliente"


def test_02_despues_puede_iniciar_sesion_y_ver_el_catalogo(mundo, client):
    client.post("/api/auth/registro", json=CUENTA)
    r = client.post("/api/auth/login", json={"codigo_empresa": "EMP-A", "email": "lucia@correo.com", "password": "Clave1234"})
    assert r.status_code == 200
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    assert client.get("/api/catalogo/productos", headers=h).status_code == 200


def test_03_correo_repetido_en_la_empresa(mundo, client):
    client.post("/api/auth/registro", json=CUENTA)
    r = client.post("/api/auth/registro", json={**CUENTA, "email": "lucia@CORREO.com"})
    assert r.status_code == 409 and r.json()["detail"] == "Este correo ya está en uso."


def test_04_el_mismo_correo_puede_existir_en_otra_empresa(mundo, client):
    assert client.post("/api/auth/registro", json=CUENTA).status_code == 201
    r = client.post("/api/auth/registro", json={**CUENTA, "codigo_empresa": "EMP-B"})
    assert r.status_code == 201 and r.json()["empresa"]["codigo"] == "EMP-B"


def test_05_empresa_inexistente_suspendida_o_sin_suscripcion(datos, mundo, client):
    aviso_empresa = "Empresa inactiva. Contacte al administrador de la plataforma."
    r = client.post("/api/auth/registro", json={**CUENTA, "codigo_empresa": "NO-EXISTE"})
    assert r.status_code == 403 and r.json()["detail"] == aviso_empresa
    datos.empresa("EMP-S", mundo.basico, estado="SUSPENDIDA")
    r = client.post("/api/auth/registro", json={**CUENTA, "codigo_empresa": "EMP-S"})
    assert r.status_code == 403 and r.json()["detail"] == aviso_empresa
    hoy = date.today()
    datos.empresa("EMP-V", mundo.basico, inicio=hoy - timedelta(days=40), venc=hoy - timedelta(days=1))
    r = client.post("/api/auth/registro", json={**CUENTA, "codigo_empresa": "EMP-V"})
    assert r.status_code == 403 and r.json()["detail"] == "La suscripción de su empresa no está vigente."


def test_06_datos_invalidos(mundo, client):
    r = client.post("/api/auth/registro", json={**CUENTA, "password": "corta"})
    assert r.status_code == 422 and r.json()["detail"] == "La contraseña debe tener al menos 8 caracteres."
    assert client.post("/api/auth/registro", json={**CUENTA, "email": "no-es-correo"}).status_code == 422
    assert client.post("/api/auth/registro", json={**CUENTA, "nombre": ""}).status_code == 422


def test_07_no_se_puede_pedir_otro_rol_ni_otra_empresa_por_el_cuerpo(mundo, client, db):
    r = client.post("/api/auth/registro", json={**CUENTA, "rol": "Administrador", "empresa_id": mundo.b.id, "sucursal_id": 1})
    assert r.status_code == 201
    assert r.json()["usuario"]["rol"] == "Cliente" and r.json()["empresa"]["id"] == mundo.a.id  # la empresa sale del código
    assert r.json()["usuario"]["sucursal_id"] is None

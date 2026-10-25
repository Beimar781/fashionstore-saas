"""CU-02 Iniciar sesión — pruebas de caja negra (5.2.1)."""
from datetime import date, timedelta

from app.core.constantes import ADMIN, CAJERO
from tests.conftest import CLAVE


def _login(client, codigo, email, password=CLAVE):
    return client.post("/api/auth/login", json={"codigo_empresa": codigo, "email": email, "password": password})


def test_01_admin_valido(datos, mundo, client):
    r = _login(client, "EMP-A", mundo.admin_a.email)
    assert r.status_code == 200
    j = r.json()
    assert j["access_token"] and j["refresh_token"]
    assert j["empresa"]["codigo"] == "EMP-A" and j["usuario"]["rol"] == ADMIN
    assert j["panel"] == "empresa" and j["restringido"] is False


def test_02_superadmin_sin_codigo(datos, client):
    datos.usuario(None, "SuperAdministrador", email="super@plataforma.com")
    r = _login(client, None, "super@plataforma.com")
    assert r.status_code == 200 and r.json()["panel"] == "plataforma" and r.json()["empresa"] is None


def test_03_contrasena_incorrecta_mensaje_unico(datos, mundo, client):
    r = _login(client, "EMP-A", mundo.admin_a.email, "incorrecta")
    assert r.status_code == 401
    assert r.json()["detail"] == "Código de empresa, correo o contraseña inválidos."
    r2 = _login(client, "EMP-A", "noexiste@x.com")
    assert r2.json()["detail"] == r.json()["detail"]  # no revela cuál dato falla


def test_04_empresa_suspendida(datos, client):
    plan = datos.plan()
    e = datos.empresa("EMP-S", plan, estado="SUSPENDIDA")
    u = datos.usuario(e, ADMIN)
    r = _login(client, "EMP-S", u.email)
    assert r.status_code == 403 and r.json()["detail"].startswith("Empresa inactiva.")
    assert _login(client, "NO-EXISTE", "a@b.com").status_code == 403


def test_05_suscripcion_vencida_admin_modo_restringido(datos, client):
    plan = datos.plan()
    e = datos.empresa("EMP-V", plan, venc=date.today() - timedelta(days=1),
                      inicio=date.today() - timedelta(days=40))
    u = datos.usuario(e, ADMIN)
    r = _login(client, "EMP-V", u.email)
    assert r.status_code == 200 and r.json()["restringido"] is True
    assert r.json()["suscripcion"]["estado"] == "VENCIDA"
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    assert client.get("/api/auth/me", headers=h).status_code == 200      # consulta de plan: permitida
    assert client.get("/api/usuarios", headers=h).status_code == 403     # operaciones: bloqueadas


def test_06_suscripcion_vencida_cajero_rechazado(datos, client):
    plan = datos.plan()
    e = datos.empresa("EMP-V", plan, venc=date.today() - timedelta(days=1), inicio=date.today() - timedelta(days=40))
    s = datos.sucursal(e, "Central")
    u = datos.usuario(e, CAJERO, sucursal=s)
    r = _login(client, "EMP-V", u.email)
    assert r.status_code == 403 and r.json()["detail"] == "La suscripción de su empresa no está vigente."


def test_07_mismo_correo_en_dos_empresas(datos, mundo, client):
    ua = datos.usuario(mundo.a, ADMIN, email="mismo@correo.com")
    ub = datos.usuario(mundo.b, ADMIN, email="mismo@correo.com")
    ra, rb = _login(client, "EMP-A", "mismo@correo.com"), _login(client, "EMP-B", "mismo@correo.com")
    assert ra.json()["empresa"]["codigo"] == "EMP-A" and rb.json()["empresa"]["codigo"] == "EMP-B"
    assert ra.json()["usuario"]["id"] == ua.id and rb.json()["usuario"]["id"] == ub.id


def test_cuenta_inactiva(datos, mundo, client):
    u = datos.usuario(mundo.a, ADMIN, email="baja@a.com", activo=False)
    r = _login(client, "EMP-A", u.email)
    assert r.status_code == 403 and r.json()["detail"] == "Cuenta inactiva. Contacte a su administrador."


def test_refresh_y_me(datos, mundo, client):
    j = _login(client, "EMP-A", mundo.admin_a.email).json()
    r = client.post("/api/auth/refresh", json={"refresh_token": j["refresh_token"]})
    assert r.status_code == 200 and r.json()["access_token"]
    assert client.post("/api/auth/refresh", json={"refresh_token": j["access_token"]}).status_code == 401
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {j['access_token']}"})
    assert me.json()["suscripcion"]["plan"]["nombre"] == "Básico"


def test_sin_token_401(client):
    assert client.get("/api/usuarios").status_code == 401


# --- Recuperación de contraseña (extensión de CU-02) ---
def _capturar_enlaces(monkeypatch):
    enviados = []
    monkeypatch.setattr("app.modules.acceso.cu02_login.service.enviar_correo",
                        lambda destino, asunto, html, texto_consola="": enviados.append((destino, texto_consola)))
    return enviados


def _token(enviados):
    return enviados[-1][1].split("token=")[1]


def test_07_recuperar_password_flujo_completo(datos, mundo, client, monkeypatch):
    enviados = _capturar_enlaces(monkeypatch)
    r = client.post("/api/auth/olvide-password", json={"codigo_empresa": "EMP-A", "email": mundo.admin_a.email})
    assert r.status_code == 200 and len(enviados) == 1 and enviados[0][0] == mundo.admin_a.email
    token = _token(enviados)
    r = client.post("/api/auth/restablecer-password", json={"token": token, "password": "NuevaClave2026*"})
    assert r.status_code == 200
    assert _login(client, "EMP-A", mundo.admin_a.email, CLAVE).status_code == 401           # la anterior ya no sirve
    assert _login(client, "EMP-A", mundo.admin_a.email, "NuevaClave2026*").status_code == 200
    # el enlace es de un solo uso
    assert client.post("/api/auth/restablecer-password", json={"token": token, "password": "OtraClave2026*"}).status_code == 422


def test_08_recuperar_no_revela_si_existe(datos, mundo, client, monkeypatch):
    enviados = _capturar_enlaces(monkeypatch)
    ok = client.post("/api/auth/olvide-password", json={"codigo_empresa": "EMP-A", "email": mundo.admin_a.email})
    no_existe = client.post("/api/auth/olvide-password", json={"codigo_empresa": "EMP-A", "email": "nadie@x.com"})
    sin_empresa = client.post("/api/auth/olvide-password", json={"codigo_empresa": "NO-EXISTE", "email": "a@b.com"})
    assert ok.json() == no_existe.json() == sin_empresa.json()
    assert len(enviados) == 1


def test_09_enlace_nuevo_invalida_el_anterior_y_token_falso(datos, mundo, client, monkeypatch):
    enviados = _capturar_enlaces(monkeypatch)
    for _ in range(2):
        client.post("/api/auth/olvide-password", json={"codigo_empresa": "EMP-A", "email": mundo.admin_a.email})
    viejo, nuevo = enviados[0][1].split("token=")[1], _token(enviados)
    assert client.post("/api/auth/restablecer-password", json={"token": viejo, "password": "NuevaClave2026*"}).status_code == 422
    assert client.post("/api/auth/restablecer-password", json={"token": "falso" * 10, "password": "NuevaClave2026*"}).status_code == 422
    assert client.post("/api/auth/restablecer-password", json={"token": nuevo, "password": "corta"}).status_code == 422
    assert client.post("/api/auth/restablecer-password", json={"token": nuevo, "password": "NuevaClave2026*"}).status_code == 200


def test_10_superadmin_recupera_sin_codigo(datos, client, monkeypatch):
    enviados = _capturar_enlaces(monkeypatch)
    datos.usuario(None, "SuperAdministrador", email="super@plataforma.com")
    client.post("/api/auth/olvide-password", json={"email": "super@plataforma.com"})
    assert len(enviados) == 1

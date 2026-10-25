"""Pruebas de integración y de aislamiento multitenant (5.3.1)."""
from datetime import date, timedelta

from app.core.constantes import CAJERO
from app.core.security import crear_token
from app.modules.sucursales.models import Sucursal


def test_01_listados_sin_registros_de_otra_empresa(datos, mundo, client):
    datos.sucursal(mundo.b, "Solo de B")
    datos.usuario(mundo.b, CAJERO, email="cajero@b.com", sucursal=datos.sucursal(mundo.b, "Otra B"))
    h = datos.login(mundo.admin_a, mundo.a)
    assert "Solo de B" not in str(client.get("/api/sucursales", headers=h).json())
    assert "cajero@b.com" not in str(client.get("/api/usuarios", headers=h).json())
    assert mundo.b.id not in [c["id"] for c in client.get("/api/ciudades", headers=h).json()]


def test_02_usuario_de_otra_empresa_es_404(datos, mundo, client):
    otro = datos.usuario(mundo.b, CAJERO, email="x@b.com", sucursal=datos.sucursal(mundo.b, "B1"))
    h = datos.login(mundo.admin_a, mundo.a)
    assert client.put(f"/api/usuarios/{otro.id}", json={"nombre": "Hack"}, headers=h).status_code == 404
    assert client.post(f"/api/usuarios/{otro.id}/desactivar", headers=h).status_code == 404


def test_03_editar_sucursal_de_otra_empresa_404_sin_cambios(datos, mundo, client, db):
    sb = datos.sucursal(mundo.b, "Original")
    h = datos.login(mundo.admin_a, mundo.a)
    for ruta, cuerpo in ((f"/api/sucursales/{sb.id}", {"nombre": "Hackeada"}),):
        assert client.put(ruta, json=cuerpo, headers=h).status_code == 404
    assert client.post(f"/api/sucursales/{sb.id}/desactivar", headers=h).status_code == 404
    db.expire_all()
    sb = db.get(Sucursal, sb.id)
    assert sb.nombre == "Original" and sb.activa is True


def test_04_token_con_empresa_id_alterado_es_401(datos, mundo, client):
    h = datos.login(mundo.admin_a, mundo.a)
    token = h["Authorization"].split()[1]
    cabecera, cuerpo, firma = token.split(".")
    import base64, json
    datos_tok = json.loads(base64.urlsafe_b64decode(cuerpo + "=" * (-len(cuerpo) % 4)))
    datos_tok["empresa_id"] = mundo.b.id
    nuevo = base64.urlsafe_b64encode(json.dumps(datos_tok).encode()).rstrip(b"=").decode()
    falso = {"Authorization": f"Bearer {cabecera}.{nuevo}.{firma}"}
    assert client.get("/api/usuarios", headers=falso).status_code == 401


def test_flujo_alta_empresa_y_limite_del_plan(datos, client):
    """Flujo 1 del 5.3.1: SuperAdmin registra empresa Básico → admin entra → 2 sucursales → la 3.ª se rechaza."""
    basico = datos.plan("Básico", 2)
    hs = datos.superadmin()
    r = client.post("/api/plataforma/empresas", headers=hs, json={
        "codigo": "NUEVA", "razon_social": "Nueva SRL", "nit": "1000", "email_contacto": "a@b.com",
        "administrador": {"nombre": "Ana", "apellidos": "X", "email": "ana@nueva.com", "password": "Segura123"},
        "suscripcion": {"plan_id": basico.id, "fecha_inicio": str(date.today()), "duracion_meses": 12}})
    assert r.status_code == 201
    login = client.post("/api/auth/login", json={"codigo_empresa": "NUEVA", "email": "ana@nueva.com", "password": "Segura123"})
    assert login.status_code == 200 and login.json()["panel"] == "empresa"
    h = {"Authorization": f"Bearer {login.json()['access_token']}"}
    for n in ("S1", "S2"):
        assert client.post("/api/sucursales", headers=h, json={"nombre": n, "ciudad_nombre": "Oruro"}).status_code == 201
    assert client.get("/api/sucursales", headers=h).json()["uso_plan"] == {"plan": "Básico", "activas": 2, "limite": 2, "disponibles": 0}
    assert client.post("/api/sucursales", headers=h, json={"nombre": "S3", "ciudad_nombre": "Oruro"}).status_code == 409


def test_flujo_vencimiento_y_cambio_de_plan(datos, mundo, client, db):
    """Flujo 2 del 5.3.1: vence la suscripción → cajero bloqueado, admin restringido, cambio de plan con reglas."""
    from app.modules.plataforma.models import Suscripcion
    suc = [datos.sucursal(mundo.b, f"B{i}") for i in range(5)]
    cajero = datos.usuario(mundo.b, CAJERO, sucursal=suc[0])
    db.query(Suscripcion).filter_by(empresa_id=mundo.b.id).update({"fecha_vencimiento": date.today() - timedelta(days=1), "fecha_inicio": date.today() - timedelta(days=60)})
    db.commit()
    hs = datos.superadmin()
    assert client.get(f"/api/plataforma/empresas/{mundo.b.id}/suscripcion", headers=hs).json()["vigente"]["estado"] == "VENCIDA"
    rc = client.post("/api/auth/login", json={"codigo_empresa": "EMP-B", "email": cajero.email, "password": "Clave1234"})
    assert rc.status_code == 403
    ra = client.post("/api/auth/login", json={"codigo_empresa": "EMP-B", "email": mundo.admin_b.email, "password": "Clave1234"})
    assert ra.status_code == 200 and ra.json()["restringido"] is True
    pedido = {"plan_id": mundo.basico.id, "fecha_inicio": str(date.today()), "duracion_meses": 12}
    assert client.post(f"/api/plataforma/empresas/{mundo.b.id}/suscripciones", json=pedido, headers=hs).status_code == 409
    for s in suc[:3]:
        db.query(Sucursal).filter_by(id=s.id).update({"activa": False})
    db.commit()
    assert client.post(f"/api/plataforma/empresas/{mundo.b.id}/suscripciones", json=pedido, headers=hs).status_code == 201


def test_flujo_dos_administradores_mismo_flujo(datos, mundo, client):
    """Flujo 3 del 5.3.1: ambos administradores dan de alta una sucursal; cada operación afecta solo a su empresa."""
    ha, hb = datos.login(mundo.admin_a, mundo.a), datos.login(mundo.admin_b, mundo.b)
    nueva = {"nombre": "Sucursal Nueva", "ciudad_nombre": "Tarija"}
    assert client.post("/api/sucursales", json=nueva, headers=ha).status_code == 201
    assert client.post("/api/sucursales", json=nueva, headers=hb).status_code == 201
    assert len(client.get("/api/sucursales", headers=ha).json()["sucursales"]) == 1
    assert len(client.get("/api/sucursales", headers=hb).json()["sucursales"]) == 1

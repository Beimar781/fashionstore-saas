"""CU-34 Gestionar planes de suscripción — caja negra."""


def _plan(nombre="Empresarial", limite=10, ia=True):
    return {"nombre": nombre, "descripcion": "Plan", "precio": "500", "periodicidad": "mensual", "max_sucursales": limite, "reportes_ia": ia}


def test_01_crear_plan_valido(datos, client):
    h = datos.superadmin()
    r = client.post("/api/plataforma/planes", json=_plan(), headers=h)
    assert r.status_code == 201 and r.json()["plan"]["max_sucursales"] == 10 and r.json()["plan"]["reportes_ia"] is True
    assert "Empresarial" in [p["nombre"] for p in client.get("/api/plataforma/planes", headers=h).json()]


def test_02_nombre_duplicado(datos, client):
    h = datos.superadmin()
    client.post("/api/plataforma/planes", json=_plan(), headers=h)
    r = client.post("/api/plataforma/planes", json=_plan("empresarial"), headers=h)
    assert r.status_code == 409 and r.json()["detail"] == "Ya existe un plan con ese nombre."


def test_03_limite_no_positivo(datos, client):
    h = datos.superadmin()
    r = client.post("/api/plataforma/planes", json=_plan(limite=0), headers=h)
    assert r.status_code == 422 and r.json()["detail"] == "El límite de sucursales debe ser mayor a cero."


def test_04_reducir_limite_bajo_el_uso_advierte(datos, mundo, client):
    datos.sucursal(mundo.b, "B1"); datos.sucursal(mundo.b, "B2")
    h = datos.superadmin()
    r = client.put(f"/api/plataforma/planes/{mundo.pro.id}", json={"max_sucursales": 1}, headers=h)
    assert r.status_code == 200
    adv = r.json()["advertencias"]
    assert adv and adv[0]["codigo"] == "EMP-B" and adv[0]["sucursales_activas"] == 2 and adv[0]["limite"] == 1
    # no se desactivan sucursales automáticamente
    h_b = datos.login(mundo.admin_b, mundo.b)
    assert client.get("/api/sucursales", headers=h_b).json()["uso_plan"]["activas"] == 2


def test_05_inactivar_plan_en_uso(datos, mundo, client):
    h = datos.superadmin()
    r = client.post(f"/api/plataforma/planes/{mundo.basico.id}/inactivar", headers=h)
    assert r.status_code == 200 and r.json()["activo"] is False and r.json()["empresas_suscritas"] == 1
    # la suscripción vigente se mantiene
    assert client.get(f"/api/plataforma/empresas/{mundo.a.id}/suscripcion", headers=h).json()["vigente"]["estado"] == "ACTIVA"
    # pero ya no se puede contratar
    r2 = client.post(f"/api/plataforma/empresas/{mundo.b.id}/suscripciones", headers=h,
                     json={"plan_id": mundo.basico.id, "fecha_inicio": "2026-01-01", "duracion_meses": 1})
    assert r2.status_code == 409


def test_listado_con_empresas_suscritas(datos, mundo, client):
    h = datos.superadmin()
    por_nombre = {p["nombre"]: p for p in client.get("/api/plataforma/planes", headers=h).json()}
    assert por_nombre["Básico"]["empresas_suscritas"] == 1 and por_nombre["Profesional"]["empresas_suscritas"] == 1

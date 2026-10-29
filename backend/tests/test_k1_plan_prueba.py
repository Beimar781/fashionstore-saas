"""Fase K, ajuste 1 · Tercer plan «Prueba gratuita»: un mes, una sola vez por empresa, sin IA; al vencer, modo restringido (RN05) y se puede contratar otro plan."""
from datetime import date, timedelta

from app.core.constantes import MSG_SUSCRIPCION_NO_VIGENTE
from app.modules.plataforma.cu35_suscripciones.service import sumar_meses
from app.modules.plataforma.models import Suscripcion

MSG_PLAN = "Su plan no incluye esta funcionalidad. Cambie al plan Profesional."


def _prueba(datos):
    return datos.plan("Prueba gratuita", 1, ia=False, precio=0, es_prueba=True)


def _asignar(client, h, empresa, plan, inicio=None, **extra):
    cuerpo = {"plan_id": plan.id, "fecha_inicio": str(inicio or date.today()), **extra}
    return client.post(f"/api/plataforma/empresas/{empresa.id}/suscripciones", json=cuerpo, headers=h)


def test_01_el_listado_de_planes_muestra_los_tres(datos, mundo, client):
    _prueba(datos)
    r = client.get("/api/plataforma/planes", headers=datos.superadmin())
    assert r.status_code == 200
    planes = {p["nombre"]: p for p in r.json()}
    assert set(planes) == {"Básico", "Profesional", "Prueba gratuita"}
    assert (planes["Prueba gratuita"]["es_prueba"], planes["Prueba gratuita"]["precio"], planes["Prueba gratuita"]["max_sucursales"], planes["Prueba gratuita"]["reportes_ia"]) == (True, "0.00", 1, False)
    assert planes["Prueba gratuita"]["offline"] and planes["Prueba gratuita"]["reportes_convencionales"]
    assert not planes["Básico"]["es_prueba"] and not planes["Profesional"]["es_prueba"]


def test_02_al_asignarla_la_vigencia_es_de_un_mes_sin_indicarla(datos, mundo, client):
    plan, h = _prueba(datos), datos.superadmin()
    inicio = date(2026, 1, 31)
    r = _asignar(client, h, mundo.a, plan, inicio=inicio)  # sin fecha de vencimiento ni duración
    assert r.status_code == 201, r.text
    assert (r.json()["fecha_vencimiento"], r.json()["plan"]["nombre"], r.json()["monto"]) == ("2026-02-28", "Prueba gratuita", "0.00") and sumar_meses(inicio, 1) == date(2026, 2, 28)
    otra = _asignar(client, h, mundo.b, plan, duracion_meses=12, fecha_vencimiento=str(date.today() + timedelta(days=400)))  # lo que indique el SuperAdmin no cambia la prueba
    assert otra.json()["fecha_vencimiento"] == str(sumar_meses(date.today(), 1))


def test_03_cada_empresa_la_usa_una_sola_vez(datos, mundo, client):
    plan, h = _prueba(datos), datos.superadmin()
    assert _asignar(client, h, mundo.a, plan).status_code == 201
    r = _asignar(client, h, mundo.a, plan)  # renovar la prueba mientras está vigente
    assert r.status_code == 409 and r.json()["detail"] == "La empresa ya usó su mes de prueba."
    assert _asignar(client, h, mundo.a, mundo.basico, duracion_meses=12).status_code == 201  # pasa a Básico
    r = _asignar(client, h, mundo.a, plan)  # y ya no puede volver a la prueba
    assert r.status_code == 409 and r.json()["detail"] == "La empresa ya usó su mes de prueba."
    assert _asignar(client, h, mundo.b, plan).status_code == 201  # pero otra empresa sí tiene la suya


def test_04_la_prueba_vencida_deja_a_la_empresa_en_modo_restringido(datos, mundo, client, db):
    plan, h = _prueba(datos), datos.superadmin()
    r = _asignar(client, h, mundo.a, plan, inicio=date.today() - timedelta(days=60))  # empezó hace dos meses: ya venció
    assert r.status_code == 201
    assert db.query(Suscripcion).filter_by(empresa_id=mundo.a.id).order_by(Suscripcion.id.desc()).first().estado == "VENCIDA"
    login = client.post("/api/auth/login", json={"codigo_empresa": mundo.a.codigo, "email": mundo.admin_a.email, "password": "Clave1234"})
    assert login.status_code == 200 and login.json()["restringido"] is True  # RN05
    h_admin = {"Authorization": f"Bearer {login.json()['access_token']}"}
    bloqueada = client.get("/api/sucursales", headers=h_admin)
    assert bloqueada.status_code == 403 and bloqueada.json()["detail"] == MSG_SUSCRIPCION_NO_VIGENTE
    plan_visible = client.get("/api/mi-plan", headers=h_admin).json()
    assert (plan_visible["plan"]["nombre"], plan_visible["vigencia"]["vigente"], plan_visible["limites"]) == ("Prueba gratuita", False, [])  # solo puede consultar su plan
    assert _asignar(client, h, mundo.a, mundo.basico, duracion_meses=12).status_code == 201  # contrata Básico con CU-35
    assert client.get("/api/sucursales", headers=h_admin).status_code == 200


def test_05_de_la_prueba_se_pasa_a_basico_o_a_profesional(datos, mundo, client, db):
    plan, h = _prueba(datos), datos.superadmin()
    _asignar(client, h, mundo.a, plan)
    _asignar(client, h, mundo.b, plan)
    assert _asignar(client, h, mundo.a, mundo.basico, duracion_meses=12).json()["plan"]["nombre"] == "Básico"
    assert _asignar(client, h, mundo.b, mundo.pro, duracion_meses=12).json()["plan"]["nombre"] == "Profesional"
    for empresa, esperado in ((mundo.a, ["VENCIDA", "VENCIDA", "ACTIVA"]), (mundo.b, ["VENCIDA", "VENCIDA", "ACTIVA"])):
        assert [s.estado for s in db.query(Suscripcion).filter_by(empresa_id=empresa.id).order_by(Suscripcion.id)] == esperado  # la prueba y el plan anterior quedan en el historial


def test_06_el_limite_de_una_sucursal_se_respeta_al_asignarla(datos, mundo, client):
    plan, h = _prueba(datos), datos.superadmin()
    datos.sucursal(mundo.a, "Centro")
    datos.sucursal(mundo.a, "Norte")
    r = _asignar(client, h, mundo.a, plan)  # RN08: tiene 2 sucursales activas y la prueba permite 1
    assert r.status_code == 409 and r.json()["detail"] == "La empresa tiene 2 sucursales activas; el plan elegido permite 1. Desactive sucursales antes de cambiar."
    assert client.get(f"/api/plataforma/empresas/{mundo.a.id}/suscripcion", headers=h).json()["vigente"]["plan"]["nombre"] == "Básico"  # no se cambió nada


def test_07_con_la_prueba_se_bloquea_la_ia_pero_no_los_reportes_ni_el_offline(datos, mundo, client):
    plan, h = _prueba(datos), datos.superadmin()
    assert _asignar(client, h, mundo.b, plan).status_code == 201  # EMP-B venía con el plan Profesional (con IA)
    h_b = datos.login(mundo.admin_b, mundo.b)
    r = client.post("/api/ia/reportes", json={"prompt": "ventas de hoy"}, headers=h_b)
    assert r.status_code == 403 and r.json()["detail"] == MSG_PLAN  # CU-23
    assert client.get("/api/ia/analitica", headers=h_b).status_code == 403  # CU-42
    assert client.get("/api/reportes/ventas", headers=h_b).status_code == 200  # CU-21: reportes convencionales
    assert client.get("/api/reportes/indicadores", headers=h_b).status_code == 200  # CU-22
    mi = client.get("/api/mi-plan", headers=h_b).json()  # CU-36
    assert mi["plan"]["nombre"] == "Prueba gratuita" and mi["vigencia"]["vigente"] is True
    assert next(x for x in mi["limites"] if x["clave"] == "sucursales")["limite"] == 1
    assert {f["clave"]: f["incluida"] for f in mi["funcionalidades"]} == {"reportes_convencionales": True, "offline": True, "reportes_ia": False}


def test_08_el_superadministrador_la_asigna_al_crear_la_empresa(datos, client, db):
    plan, h = _prueba(datos), datos.superadmin()
    cuerpo = lambda codigo, nit: {  # noqa: E731
        "codigo": codigo, "razon_social": "Nueva SRL", "nit": nit, "email_contacto": f"info@{codigo.lower()}.com", "telefono": "7123",
        "administrador": {"nombre": "Ada", "apellidos": "Lovelace", "email": f"ada@{codigo.lower()}.com", "password": "Segura123"},
        "suscripcion": {"plan_id": plan.id, "fecha_inicio": str(date.today()), "duracion_meses": 12},  # aunque se pidan 12 meses, la prueba dura 1
    }
    r = client.post("/api/plataforma/empresas", json=cuerpo("EMP-N1", "900100201"), headers=h)
    assert r.status_code == 201, r.text
    assert (r.json()["plan"], r.json()["suscripcion_estado"], r.json()["fecha_vencimiento"]) == ("Prueba gratuita", "ACTIVA", str(sumar_meses(date.today(), 1)))
    assert client.post("/api/plataforma/empresas", json=cuerpo("EMP-N2", "900100202"), headers=h).status_code == 201  # cada empresa nueva tiene la suya


def test_09_los_planes_se_pueden_crear_y_corregir_como_de_prueba(datos, client):
    h = datos.superadmin()
    r = client.post("/api/plataforma/planes", json={"nombre": "Prueba extendida", "precio": "0", "max_sucursales": 1, "es_prueba": True}, headers=h)
    assert r.status_code == 201 and r.json()["plan"]["es_prueba"] is True
    plan_id = r.json()["plan"]["id"]
    assert client.put(f"/api/plataforma/planes/{plan_id}", json={"es_prueba": False}, headers=h).json()["plan"]["es_prueba"] is False
    assert client.get("/api/plataforma/planes", headers=datos.superadmin()).status_code == 200

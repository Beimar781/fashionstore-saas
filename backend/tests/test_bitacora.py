"""Bitácora del sistema (función transversal, Fase J): qué se registra, qué se oculta, quién la ve y que no se puede alterar."""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.main import app
from app.modules.plataforma.bitacora import etiquetas
from app.modules.plataforma.bitacora.middleware import _registrar
from app.modules.plataforma.publico import registrar_en_bitacora
from tests.catalogo_util import entrar
from tests.compras_util import comprar, stock_listo

CLAVE_MALA = "ContrasenaIncorrecta99"


def _lista(client, h, ruta="/api/bitacora", **params):
    r = client.get(ruta, params=params, headers=h)
    assert r.status_code == 200, r.text
    return r.json()


def _filas(db):
    return db.execute(text("SELECT * FROM bitacora ORDER BY id")).mappings().all()


def _color(client, h, nombre="Verde claro", **extra):
    return client.post("/api/colores", json={"nombre": nombre, "codigo_hex": "#88CC88"}, headers={**h, **extra})


def test_01_inicio_y_cierre_de_sesion_quedan_registrados(inv, mundo, client, db):
    h = entrar(client, mundo.a, "administrador@emp-a.com", "Clave1234")
    assert client.post("/api/auth/logout", headers=h).status_code == 200
    items = _lista(client, inv.h_admin)["items"]
    por_accion = {i["accion"]: i for i in items if i["usuario"] == "Administrador Prueba"}
    assert por_accion["LOGIN"]["accion_texto"] == "Inicio de sesión" and por_accion["LOGIN"]["tono"] == "verde"
    assert por_accion["LOGOUT"]["accion_texto"] == "Cierre de sesión" and por_accion["LOGOUT"]["tono"] == "gris"
    assert (por_accion["LOGIN"]["rol"], por_accion["LOGIN"]["entidad"], por_accion["LOGIN"]["ip"]) == ("Administrador", "sesión", "testclient")
    assert por_accion["LOGIN"]["empresa"] is None  # el nombre de la empresa (columna Empresa) solo lo ve el SuperAdministrador
    assert {f["empresa_id"] for f in _filas(db) if f["accion"] in ("LOGIN", "LOGOUT")} == {mundo.a.id}


def test_02_un_alta_deja_su_fila_con_un_detalle_legible(inv, mundo, client, db):
    assert _color(client, inv.h_admin, "Verde claro").status_code == 201
    r = client.post("/api/ciudades", json={"nombre": "Cochabamba", "departamento": "Cochabamba"}, headers=inv.h_admin)
    assert r.status_code == 201
    items = {i["detalle"]: i for i in _lista(client, inv.h_admin, tamano=100)["items"] if i["accion"] == "CREAR"}
    assert items["Registró el color Verde claro"]["entidad"] == "color" and items["Registró el color Verde claro"]["tono"] == "azul"
    ciudad = items["Registró la ciudad Cochabamba"]
    assert (ciudad["entidad"], ciudad["entidad_id"], ciudad["usuario"], ciudad["rol"]) == ("ciudad", r.json()["id"], "Administrador Prueba", "Administrador")


def test_03_modificar_y_eliminar_tienen_su_accion_y_su_color(inv, mundo, client):
    color = _color(client, inv.h_admin, "Rosa").json()
    assert client.put(f"/api/colores/{color['id']}", json={"nombre": "Rosa palo", "codigo_hex": "#EEBBCC"}, headers=inv.h_admin).status_code == 200
    assert client.delete(f"/api/colores/{color['id']}", headers=inv.h_admin).status_code in (200, 204)
    items = {i["accion"]: i for i in _lista(client, inv.h_admin, entidad="color")["items"]}
    assert items["MODIFICAR"]["detalle"] == "Modificó el color Rosa palo" and items["MODIFICAR"]["tono"] == "ambar"
    assert items["ELIMINAR"]["detalle"] == f"Eliminó el color #{color['id']}" and items["ELIMINAR"]["tono"] == "rojo"


def test_04_el_intento_fallido_se_registra_sin_la_contrasena(inv, mundo, client, db):
    r = client.post("/api/auth/login", json={"codigo_empresa": mundo.a.codigo, "email": "administrador@emp-a.com", "password": CLAVE_MALA})
    assert r.status_code == 401
    fallido = next(i for i in _lista(client, inv.h_admin)["items"] if i["accion"] == "LOGIN_FALLIDO")
    assert fallido["detalle"] == "Intento fallido de inicio de sesión con el correo administrador@emp-a.com en la empresa EMP-A"
    assert (fallido["usuario"], fallido["tono"], fallido["accion_texto"]) == ("administrador@emp-a.com", "rojo", "Inicio de sesión fallido")
    assert CLAVE_MALA not in str([tuple(f.values()) for f in _filas(db)])  # la contraseña no se guarda en ningún lado
    client.post("/api/auth/login", json={"codigo_empresa": "NO-EXISTE", "email": "x@y.com", "password": CLAVE_MALA})
    sin_empresa = [f for f in _filas(db) if f["accion"] == "LOGIN_FALLIDO" and f["empresa_id"] is None]
    assert len(sin_empresa) == 1 and CLAVE_MALA not in str(sin_empresa[0].values())


def test_05_las_consultas_y_los_errores_no_se_registran(inv, mundo, client, db):
    antes = len(_filas(db))
    client.get("/api/colores", headers=inv.h_admin)
    client.get("/api/bitacora", headers=inv.h_admin)
    client.get("/api/catalogo/productos", headers=inv.h_cliente)
    assert client.post("/api/ciudades", json={"nombre": "", "departamento": ""}, headers=inv.h_admin).status_code == 422  # no terminó bien
    assert client.post("/api/colores", json={"nombre": "Rojo", "codigo_hex": "#CC0000"}, headers=inv.h_admin).status_code == 409  # ya existe
    client.post("/api/ciudades", json={"nombre": "Oruro", "departamento": "Oruro"})  # sin sesión
    assert len(_filas(db)) == antes


def test_06_nunca_se_guardan_datos_de_tarjeta_ni_tokens(inv, mundo, client, db):
    stock_listo(inv, mundo)
    comprar(client, inv.h_cliente, inv, inv.v_sm_rojo, 1)  # paga con la tarjeta 4242 4242 4242 4242, CVC 123
    todo = str([tuple(f.values()) for f in _filas(db)])
    assert "4242" not in todo and "Bearer" not in todo and "eyJ" not in todo and "Clave1234" not in todo
    pagos = [f for f in _filas(db) if f["accion"] == "PAGAR"]
    assert any(f["detalle"].startswith("Pagó el pedido PED-") and f["detalle"].endswith("con tarjeta") for f in pagos)
    assert any(f["accion"] == "CREAR" and f["entidad"] == "pedido" for f in _filas(db))


def test_07_la_ip_real_viene_de_x_forwarded_for(inv, mundo, client, db):
    assert _color(client, inv.h_admin, "Naranja", **{"X-Forwarded-For": "203.0.113.7, 10.0.0.1"}).status_code == 201
    assert next(f for f in _filas(db) if f["detalle"] == "Registró el color Naranja")["ip"] == "203.0.113.7"
    assert _lista(client, inv.h_admin, q="203.0.113")["total"] == 1  # y se puede buscar por IP


def test_08_el_administrador_solo_ve_la_bitacora_de_su_empresa(inv, mundo, tienda_b, client):
    _color(client, inv.h_admin, "Solo de A")
    _color(client, tienda_b.h_admin, "Solo de B")
    de_a = _lista(client, inv.h_admin, tamano=100)["items"]
    de_b = _lista(client, tienda_b.h_admin, tamano=100)["items"]
    assert any("Solo de A" in i["detalle"] for i in de_a) and not any("Solo de B" in i["detalle"] for i in de_a)
    assert any("Solo de B" in i["detalle"] for i in de_b) and not any("Solo de A" in i["detalle"] for i in de_b)
    # el empresa_id sale del token: pedir otra empresa por la URL no cambia nada
    assert _lista(client, inv.h_admin, empresa="1000", tamano=100)["total"] == len(de_a)


def test_09_el_superadministrador_ve_todas_las_empresas_y_las_de_plataforma(inv, mundo, tienda_b, datos, client):
    _color(client, inv.h_admin, "Solo de A")
    _color(client, tienda_b.h_admin, "Solo de B")
    h_super = datos.superadmin()
    plan = client.post("/api/plataforma/planes", json={"nombre": "Plan de prueba", "precio": "10", "max_sucursales": 1}, headers=h_super)
    assert plan.status_code == 201, plan.text
    assert client.post(f"/api/plataforma/empresas/{mundo.b.id}/suspender", headers=h_super).status_code == 200
    todo = _lista(client, h_super, "/api/plataforma/bitacora", tamano=100)["items"]
    assert {mundo.a.razon_social, mundo.b.razon_social, "Plataforma"} <= {i["empresa"] for i in todo}  # la columna Empresa
    detalles = {i["detalle"]: i for i in todo}
    assert detalles["Registró el color Solo de A"]["empresa_id"] == mundo.a.id and detalles["Registró el color Solo de B"]["empresa_id"] == mundo.b.id
    assert detalles["Creó el plan Plan de prueba"]["empresa_id"] is None and detalles["Creó el plan Plan de prueba"]["empresa"] == "Plataforma"
    suspension = next(i for i in todo if i["accion"] == "SUSPENDER" and i["entidad"] == "empresa")
    assert suspension["empresa_id"] == mundo.b.id and suspension["rol"] == "SuperAdministrador"  # su operación sobre una empresa va con el empresa_id de esa empresa
    solo_a = _lista(client, h_super, "/api/plataforma/bitacora", empresa=str(mundo.a.id), tamano=100)["items"]
    assert solo_a and {i["empresa_id"] for i in solo_a} == {mundo.a.id}
    plataforma = _lista(client, h_super, "/api/plataforma/bitacora", empresa="plataforma", tamano=100)["items"]
    assert plataforma and {i["empresa_id"] for i in plataforma} == {None}
    opciones = client.get("/api/plataforma/bitacora/opciones", headers=h_super).json()
    assert {e["id"] for e in opciones["empresas"]} >= {mundo.a.id, mundo.b.id}


def test_10_solo_administrador_y_superadministrador_tienen_acceso(inv, mundo, tienda_b, datos, client):
    h_super = datos.superadmin()
    for h in (inv.h_enc_centro, inv.h_cajero, inv.h_cliente):
        assert client.get("/api/bitacora", headers=h).status_code == 403
        assert client.get("/api/bitacora/opciones", headers=h).status_code == 403
        assert client.get("/api/plataforma/bitacora", headers=h).status_code == 403
    assert client.get("/api/plataforma/bitacora", headers=inv.h_admin).status_code == 403  # la general es de la plataforma
    assert client.get("/api/bitacora", headers=h_super).status_code == 403  # y la de una empresa, de su Administrador
    assert client.get("/api/bitacora").status_code == 401 and client.get("/api/plataforma/bitacora").status_code == 401


def test_11_no_hay_forma_de_editar_ni_de_borrar(inv, mundo, client, db):
    _color(client, inv.h_admin, "Para siempre")
    for ruta in ("/api/bitacora", "/api/bitacora/1", "/api/plataforma/bitacora", "/api/plataforma/bitacora/1"):
        for metodo in (client.post, client.put, client.patch, client.delete):
            assert metodo(ruta, headers=inv.h_admin).status_code in (404, 405)
    metodos = {m.upper() for ruta, ops in app.openapi()["paths"].items() if "bitacora" in ruta for m in ops}
    assert metodos == {"GET"}  # solo lectura
    for sql in ("UPDATE bitacora SET detalle = 'alterado'", "DELETE FROM bitacora"):  # ni siquiera directo en la base
        with pytest.raises(DBAPIError, match="no se puede modificar ni borrar"):
            db.execute(text(sql))
        db.rollback()
    assert any(f["detalle"] == "Registró el color Para siempre" for f in _filas(db))


def test_12_filtros_busqueda_y_paginacion(inv, mundo, client, db):
    ahora = datetime.now(timezone.utc)
    for dias, usuario, accion, entidad, detalle, ip in (
        (10, "Luis Rojas", "CREAR", "reserva", "Registró la reserva RSV-AAAA", "190.129.10.5"),
        (5, "Ana Suárez", "COBRAR", "venta", "Cobró la venta PED-ZZZ por Bs 120.00 (EFECTIVO)", "190.129.10.9"),
        (1, "Luis Rojas", "MODIFICAR", "producto", "Modificó el producto Camisa Oxford", "201.222.3.4"),
    ):
        registrar_en_bitacora(db, empresa_id=mundo.a.id, usuario_id=None, usuario=usuario, rol="Cajero", accion=accion, entidad=entidad, detalle=detalle, ip=ip, creado_en=ahora - timedelta(days=dias))
    h = inv.h_admin
    assert _lista(client, h, usuario="Luis Rojas")["total"] == 2
    assert [i["accion"] for i in _lista(client, h, entidad="venta")["items"]] == ["COBRAR"]
    assert [i["entidad"] for i in _lista(client, h, accion="MODIFICAR")["items"]] == ["producto"]
    assert _lista(client, h, q="rsv-aaaa")["total"] == 1 and _lista(client, h, q="190.129")["total"] == 2  # sin distinguir mayúsculas
    hoy = datetime.now().date()
    entre = _lista(client, h, desde=str(hoy - timedelta(days=6)), hasta=str(hoy - timedelta(days=4)))["items"]
    assert [i["usuario"] for i in entre] == ["Ana Suárez"]  # «hasta» incluye todo el día
    pagina1 = _lista(client, h, usuario="Luis Rojas", tamano=1, pagina=1)
    pagina2 = _lista(client, h, usuario="Luis Rojas", tamano=1, pagina=2)
    assert (pagina1["total"], pagina1["items"][0]["entidad"], pagina2["items"][0]["entidad"]) == (2, "producto", "reserva")  # de la más reciente a la más antigua
    assert client.get("/api/bitacora", params={"tamano": 500}, headers=h).status_code == 422
    assert client.get("/api/bitacora", params={"pagina": 0}, headers=h).status_code == 422
    opciones = client.get("/api/bitacora/opciones", headers=h).json()
    assert "Luis Rojas" in opciones["usuarios"] and "reserva" in opciones["entidades"] and {"codigo": "LOGIN", "texto": "Inicio de sesión"} in opciones["acciones"] and opciones["empresas"] == []


def test_13_todas_las_rutas_de_escritura_tienen_etiqueta(client):
    """Regla 16: al crear un endpoint de escritura se agrega su ruta a la tabla de etiquetas."""
    sin_etiqueta = []
    for ruta, ops in app.openapi()["paths"].items():
        for metodo in ops:
            if metodo.upper() in ("POST", "PUT", "PATCH", "DELETE") and etiquetas.buscar(metodo.upper(), ruta) is None:
                sin_etiqueta.append(f"{metodo.upper()} {ruta}")
    assert sin_etiqueta == []


def test_14_una_ruta_sin_etiqueta_se_registra_con_un_texto_generico(inv, mundo, client, db):
    token = inv.h_admin["Authorization"].removeprefix("Bearer ")
    _registrar(client.app, "DELETE", "/api/ruta/nueva/7", 200, {}, {}, token, "10.0.0.1")
    f = _filas(db)[-1]
    assert (f["accion"], f["entidad"], f["detalle"], f["empresa_id"], f["ip"]) == ("ELIMINAR", "sistema", "Realizó una operación de escritura en el sistema", mundo.a.id, "10.0.0.1")
    _registrar(client.app, "POST", "/api/ruta/nueva", 200, {}, {}, "token-invalido", "10.0.0.1")  # sin sesión válida no se registra
    _registrar(client.app, "POST", "/api/ruta/nueva", 500, {}, {}, token, "10.0.0.1")  # tampoco lo que terminó mal
    assert _filas(db)[-1]["id"] == f["id"]  # ninguna de las dos dejó filas


def test_15_el_detalle_se_arma_con_datos_opcionales():
    assert etiquetas.construir_detalle("Registró la sucursal[ {nombre}]", {}, {"nombre": "Centro"}, {}) == "Registró la sucursal Centro"
    assert etiquetas.construir_detalle("Registró la sucursal[ {nombre}]", {}, {}, {}) == "Registró la sucursal"
    assert etiquetas.construir_detalle("Asignó el plan[ {plan.nombre}] a la empresa", {}, {}, {"plan": {"nombre": "Profesional"}}) == "Asignó el plan Profesional a la empresa"
    assert etiquetas.construir_detalle("Eliminó el color #{color_id}", {"color_id": "9"}, {}, {}) == "Eliminó el color #9"
    assert etiquetas.construir_detalle("Registró[ {nombre}]", {}, {"nombre": "Cuerpo"}, {"nombre": "Respuesta"}) == "Registró Respuesta"  # la respuesta manda sobre el cuerpo
    ruta, parametros = etiquetas.buscar("POST", "/api/reservas/12/cancelar")
    assert (ruta.accion, ruta.entidad, parametros) == ("CANCELAR", "reserva", {"reserva_id": "12"}) and etiquetas.buscar("GET", "/api/reservas") is None

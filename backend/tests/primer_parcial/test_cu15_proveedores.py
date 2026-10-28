"""CU-15 Gestionar proveedores — caja negra (pasos de la ficha) + roles, portal y aislamiento entre empresas."""
from tests.catalogo_util import crear_proveedor, entrar

SIN_DATOS = "Debe proporcionar el nombre de la empresa y la información de contacto."


def _proveedor(**extra):
    return {"razon_social": "Textiles del Sur S.R.L.", "nombre_comercial": "Textiles Sur", "nit": "1020304050",
            "email": "ventas@textilessur.com", "telefono": "3-3322110", "direccion": "Av. Industrial 123", **extra}


def test_01_registrar_proveedor_con_datos_completos(datos, mundo, client):
    h = datos.login(mundo.admin_a, mundo.a)
    r = client.post("/api/proveedores", json=_proveedor(), headers=h)
    assert r.status_code == 201
    assert (r.json()["razon_social"], r.json()["activo"], r.json()["tiene_acceso"]) == ("Textiles del Sur S.R.L.", True, False)


def test_02_registrar_proveedor_sin_nombre_o_sin_contacto(datos, mundo, client):
    h = datos.login(mundo.admin_a, mundo.a)
    for cuerpo in ({"razon_social": "Solo nombre"}, {"email": "a@b.com", "telefono": "7"}, {"razon_social": "  ", "email": "a@b.com"}, {}):
        r = client.post("/api/proveedores", json=cuerpo, headers=h)
        assert r.status_code == 422 and r.json()["detail"] == SIN_DATOS
    assert client.post("/api/proveedores", json={"razon_social": "Con correo", "email": "a@b.com"}, headers=h).status_code == 201
    assert client.post("/api/proveedores", json={"razon_social": "Con teléfono", "telefono": "7000"}, headers=h).status_code == 201


def test_03_editar_datos_del_proveedor(datos, mundo, client):
    h = datos.login(mundo.admin_a, mundo.a)
    p = client.post("/api/proveedores", json=_proveedor(), headers=h).json()
    r = client.put(f"/api/proveedores/{p['id']}", json={"telefono": "3-3999999", "direccion": "Nueva dirección"}, headers=h)
    assert r.status_code == 200 and (r.json()["telefono"], r.json()["direccion"]) == ("3-3999999", "Nueva dirección")
    # al editar tampoco se puede dejar al proveedor sin nombre ni contacto
    r = client.put(f"/api/proveedores/{p['id']}", json={"email": None, "telefono": None}, headers=h)
    assert r.status_code == 422 and r.json()["detail"] == SIN_DATOS


def test_04_los_cambios_quedan_guardados(datos, mundo, client):
    h = datos.login(mundo.admin_a, mundo.a)
    p = client.post("/api/proveedores", json=_proveedor(), headers=h).json()
    client.put(f"/api/proveedores/{p['id']}", json={"nombre_comercial": "Sur Textil"}, headers=h)
    assert client.get(f"/api/proveedores/{p['id']}", headers=h).json()["nombre_comercial"] == "Sur Textil"


def test_05_consultar_proveedor_registrado(datos, mundo, client):
    h = datos.login(mundo.admin_a, mundo.a)
    p = client.post("/api/proveedores", json=_proveedor(), headers=h).json()
    r = client.get(f"/api/proveedores/{p['id']}", headers=h).json()
    assert (r["razon_social"], r["nit"], r["email"]) == ("Textiles del Sur S.R.L.", "1020304050", "ventas@textilessur.com")
    assert [x["id"] for x in client.get("/api/proveedores?q=sur", headers=h).json()] == [p["id"]]


def test_nit_unico_por_empresa_y_desactivacion(datos, mundo, client):
    ha, hb = datos.login(mundo.admin_a, mundo.a), datos.login(mundo.admin_b, mundo.b)
    p = client.post("/api/proveedores", json=_proveedor(), headers=ha).json()
    r = client.post("/api/proveedores", json=_proveedor(razon_social="Otra"), headers=ha)
    assert r.status_code == 409 and r.json()["detail"] == "Ya existe un proveedor con ese NIT."
    assert client.post("/api/proveedores", json=_proveedor(), headers=hb).status_code == 201  # otra empresa, mismo NIT
    assert client.post(f"/api/proveedores/{p['id']}/desactivar", headers=ha).json()["activo"] is False
    assert client.get("/api/proveedores?solo_activos=true", headers=ha).json() == []
    assert client.post(f"/api/proveedores/{p['id']}/activar", headers=ha).json()["activo"] is True


def test_portal_cuenta_del_proveedor(datos, mundo, client):
    h = datos.login(mundo.admin_a, mundo.a)
    p = crear_proveedor(client, h, "Hilos Norte")
    assert client.get(f"/api/proveedores/{p['id']}", headers=h).json()["tiene_acceso"] is True
    login = client.post("/api/auth/login", json={"codigo_empresa": "EMP-A", "email": "hilos@proveedor.com", "password": "Clave1234"})
    assert login.status_code == 200 and login.json()["usuario"]["rol"] == "Proveedor" and login.json()["panel"] == "proveedor"
    r = client.post(f"/api/proveedores/{p['id']}/acceso", json={"email": "otro@proveedor.com", "password": "Clave1234"}, headers=h)
    assert r.status_code == 409 and r.json()["detail"] == "El proveedor ya tiene una cuenta de acceso."
    p2 = client.post("/api/proveedores", json=_proveedor(nit=None), headers=h).json()
    r = client.post(f"/api/proveedores/{p2['id']}/acceso", json={"email": "HILOS@proveedor.com", "password": "Clave1234"}, headers=h)
    assert r.status_code == 409 and r.json()["detail"] == "Este correo ya está en uso."
    r = client.post(f"/api/proveedores/{p2['id']}/acceso", json={"email": "x@proveedor.com", "password": "corta"}, headers=h)
    assert r.status_code == 422


def test_roles_el_encargado_solo_consulta(datos, mundo, inv, client):
    h = inv.h_admin
    inactivo = client.post("/api/proveedores", json=_proveedor(), headers=h).json()
    client.post(f"/api/proveedores/{inactivo['id']}/desactivar", headers=h)
    nombres = [p["razon_social"] for p in client.get("/api/proveedores", headers=inv.h_enc_centro).json()]
    assert nombres == ["Textiles Sur"]  # el Encargado ve solo los activos
    assert client.post("/api/proveedores", json=_proveedor(nit="9"), headers=inv.h_enc_centro).status_code == 403
    for cabecera in (inv.h_cliente, inv.h_cajero, inv.h_prov):
        assert client.get("/api/proveedores", headers=cabecera).status_code == 403


def test_vincular_coleccion_con_proveedor(inv, client):
    h = inv.h_admin
    r = client.put(f"/api/colecciones/{inv.col['id']}/proveedor", json={"proveedor_id": inv.proveedor["id"]}, headers=h)
    assert r.status_code == 200 and r.json()["proveedor_id"] == inv.proveedor["id"]
    assert client.get("/api/colecciones", headers=h).json()[0]["proveedor_id"] == inv.proveedor["id"]
    assert client.put(f"/api/colecciones/{inv.col['id']}/proveedor", json={"proveedor_id": None}, headers=h).json()["proveedor_id"] is None


def test_aislamiento_entre_empresas(datos, mundo, inv, tienda_b, client):
    p = inv.proveedor
    assert client.get(f"/api/proveedores/{p['id']}", headers=tienda_b.h_admin).status_code == 404
    assert client.put(f"/api/proveedores/{p['id']}", json={"telefono": "1"}, headers=tienda_b.h_admin).status_code == 404
    assert client.post(f"/api/proveedores/{p['id']}/acceso", json={"email": "x@y.com", "password": "Clave1234"}, headers=tienda_b.h_admin).status_code == 404
    assert client.get("/api/proveedores", headers=tienda_b.h_admin).json() == []
    # ni a una colección de A se le puede poner un proveedor de B, ni al revés
    pb = crear_proveedor(client, tienda_b.h_admin, "Proveedor Bolivia", con_acceso=False)
    assert client.put(f"/api/colecciones/{inv.col['id']}/proveedor", json={"proveedor_id": pb["id"]}, headers=inv.h_admin).status_code == 404
    assert client.put(f"/api/colecciones/{inv.col['id']}/proveedor", json={"proveedor_id": pb["id"]}, headers=tienda_b.h_admin).status_code == 404
    # la cuenta del portal de A no entra con el código de B
    assert client.post("/api/auth/login", json={"codigo_empresa": "EMP-B", "email": "textiles@proveedor.com", "password": "Clave1234"}).status_code == 401

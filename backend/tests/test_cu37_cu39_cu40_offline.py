"""CU-37 Descargar catálogo, CU-39 Consultar operaciones y CU-40 Gestionar conflictos de sincronización."""
from datetime import date, timedelta

from tests.compras_util import existencias
from tests.offline_util import agregar_stock, op_reserva, op_venta, sincronizar_ok, stock_listo

MSG_PLAN = "Su plan no incluye esta funcionalidad. Cambie al plan Profesional."


def _descargar(client, h):
    r = client.get("/api/offline/catalogo", headers=h)
    assert r.status_code == 200, r.text
    return r.json()


# ---------------- CU-37 ----------------
def test_01_el_personal_descarga_el_catalogo_de_su_sucursal_con_clientes(inv, mundo, client):
    stock_listo(inv, mundo, centro=10, norte=4)
    c = _descargar(client, inv.h_cajero)
    assert c["empresa_id"] == mundo.a.id and c["generado_en"] and [s["nombre"] for s in c["sucursales"]] == ["Centro"]  # RN10: solo su sucursal
    camisa = next(p for p in c["productos"] if p["nombre"] == "Camisa Oxford")
    assert (camisa["categoria"], camisa["genero"], len(camisa["variantes"])) == ("Camisas", "UNISEX", 4)
    v = next(v for v in camisa["variantes"] if v["id"] == inv.v_sm_rojo["id"])
    assert (v["sku"], v["talla"], v["color"], v["precio"], v["precio_final"], v["promocion"]) == (inv.v_sm_rojo["sku"], "S", "Rojo", "100.00", "100.00", None)
    assert v["stock"] == {str(inv.centro.id): 10}  # solo el stock de su sucursal
    assert [x["email"] for x in c["clientes"]] == ["cliente@tienda.com"]  # datos mínimos de los clientes


def test_02_el_cliente_descarga_todas_las_sucursales_y_ningun_cliente(inv, mundo, client):
    stock_listo(inv, mundo, centro=10, norte=4)
    c = _descargar(client, inv.h_cliente)
    assert sorted(s["nombre"] for s in c["sucursales"]) == ["Centro", "Norte"] and c["clientes"] == []
    v = next(v for p in c["productos"] for v in p["variantes"] if v["id"] == inv.v_sm_rojo["id"])
    assert v["stock"] == {str(inv.centro.id): 10, str(inv.norte.id): 4}


def test_03_el_catalogo_trae_el_precio_con_promocion_y_omite_lo_inactivo(inv, mundo, client):
    stock_listo(inv, mundo)
    hoy = date.today()
    r = client.post("/api/promociones", json={"nombre": "Liquidación", "tipo_descuento": "PORCENTAJE", "valor": "20", "inicia": str(hoy - timedelta(days=1)),
                                              "termina": str(hoy + timedelta(days=5)), "productos_ids": [inv.camisa["id"]]}, headers=inv.h_admin)
    assert r.status_code == 201, r.text
    v = next(v for p in _descargar(client, inv.h_cajero)["productos"] for v in p["variantes"] if v["id"] == inv.v_sm_rojo["id"])
    assert (v["precio"], v["precio_final"], v["promocion"]) == ("100.00", "80.00", "Liquidación")
    client.post(f"/api/productos/{inv.camisa['id']}/desactivar", headers=inv.h_admin)
    assert _descargar(client, inv.h_cajero)["productos"] == []


def test_04_descarga_roles_plan_y_aislamiento(inv, mundo, tienda_b, db, client):
    stock_listo(inv, mundo)
    assert client.get("/api/offline/catalogo", headers=inv.h_admin).status_code == 403
    assert client.get("/api/offline/catalogo").status_code == 401
    b = tienda_b.h_admin  # el Administrador de EMP-B no descarga; se prueba con un empleado de EMP-B más abajo
    assert client.get("/api/offline/catalogo", headers=b).status_code == 403
    mundo.basico.offline = False
    db.commit()
    r = client.get("/api/offline/catalogo", headers=inv.h_cajero)
    assert r.status_code == 403 and r.json()["detail"] == MSG_PLAN


def test_05_un_empleado_de_otra_empresa_no_recibe_nada_de_esta(inv, mundo, datos, client):
    from app.modules.sucursales.models import Sucursal  # noqa: F401
    from tests.catalogo_util import entrar
    stock_listo(inv, mundo)
    datos.usuario(mundo.b, "Cajero", email="cajero@b.com", sucursal=datos.sucursal(mundo.b, "Sucursal B"))
    c = _descargar(client, entrar(client, mundo.b, "cajero@b.com"))
    assert c["productos"] == [] and c["clientes"] == [] and [s["nombre"] for s in c["sucursales"]] == ["Sucursal B"]


# ---------------- CU-39 ----------------
def test_06_cada_usuario_consulta_el_estado_de_sus_operaciones(inv, mundo, client):
    stock_listo(inv, mundo, centro=1)
    venta, conflicto = op_venta([(inv.v_sm_rojo, 1)], 100, segundos=-5), op_venta([(inv.v_sm_rojo, 1)], 100, segundos=-1)
    sincronizar_ok(client, inv.h_cajero, venta, conflicto)
    sincronizar_ok(client, inv.h_cliente, op_reserva(inv.centro, [(inv.var[("M", "Azul")], 1)]))
    ops = client.get("/api/offline/operaciones", headers=inv.h_cajero).json()
    assert [(o["tipo"], o["estado"]) for o in ops] == [("VENTA_CONTADO", "EN_CONFLICTO"), ("VENTA_CONTADO", "CONFIRMADA")]  # de la más reciente a la más antigua
    assert ops[1]["referencia"] and ops[1]["comprobante"] and ops[0]["detalle"]["faltantes"] and ops[0]["sucursal"] == "Centro" and ops[0]["usuario"]
    mias_cliente = client.get("/api/offline/operaciones", headers=inv.h_cliente).json()
    assert [(o["tipo"], o["estado"]) for o in mias_cliente] == [("RESERVA", "CONFIRMADA")]  # nadie ve las operaciones de otro


# ---------------- CU-40 ----------------
def _conflicto(client, inv, db, cantidad=3, disponible=1):
    """Una venta de `cantidad` prendas con solo `disponible` en la sucursal: queda en conflicto."""
    db.execute(__import__("sqlalchemy").text("UPDATE existencias SET disponible = :d WHERE variante_id = :v AND sucursal_id = :s"), {"d": disponible, "v": inv.v_sm_rojo["id"], "s": inv.centro.id})
    db.commit()
    r = sincronizar_ok(client, inv.h_cajero, op_venta([(inv.v_sm_rojo, cantidad)], 100 * cantidad))[0]
    assert r["estado"] == "EN_CONFLICTO"
    return client.get("/api/offline/conflictos", headers=inv.h_enc_centro).json()[0]


def test_07_el_encargado_ve_los_conflictos_de_su_sucursal(inv, mundo, client, db):
    stock_listo(inv, mundo)
    c = _conflicto(client, inv, db)
    assert (c["estado"], c["tipo"], c["sucursal"], c["detalle"]["faltantes"][0]["solicitadas"], c["detalle"]["faltantes"][0]["disponibles"]) == ("EN_CONFLICTO", "VENTA_CONTADO", "Centro", 3, 1)
    assert client.get("/api/offline/conflictos", headers=inv.h_enc_norte).json() == []  # RN10: Norte no ve los de Centro
    assert [x["id"] for x in client.get("/api/offline/conflictos", headers=inv.h_admin).json()] == [c["id"]]  # el Administrador ve todos


def test_08_reintentar_sigue_en_conflicto_hasta_que_haya_existencias(inv, mundo, client, db):
    stock_listo(inv, mundo)
    c = _conflicto(client, inv, db)
    r = client.post(f"/api/offline/conflictos/{c["id"]}/resolver", json={"accion": "REINTENTAR"}, headers=inv.h_enc_centro)
    assert r.status_code == 409 and r.json()["detail"] == "Todavía no hay existencias suficientes: Camisa Oxford (S, Rojo): solicitadas 3, disponibles 1."
    assert existencias(client, inv.h_enc_centro, inv.v_sm_rojo)["vendida"] == 0  # no se descontó nada
    assert client.get("/api/offline/conflictos", headers=inv.h_enc_centro).json()[0]["intentos"] == 2
    agregar_stock(db, inv.v_sm_rojo, inv.centro, 5)  # llegó mercadería
    r = client.post(f"/api/offline/conflictos/{c["id"]}/resolver", json={"accion": "REINTENTAR"}, headers=inv.h_enc_centro)
    assert r.status_code == 200, r.text
    ok = r.json()
    assert (ok["estado"], ok["resolucion"], ok["detalle"], ok["intentos"]) == ("CONFIRMADA", "REINTENTADA", None, 3) and ok["referencia"] and ok["comprobante"]
    f = existencias(client, inv.h_enc_centro, inv.v_sm_rojo)
    assert (f["disponible"], f["vendida"]) == (3, 3)  # ahora sí se descontó, una sola vez
    assert client.get("/api/offline/conflictos", headers=inv.h_enc_centro).json() == []
    mia = client.get("/api/offline/operaciones", headers=inv.h_cajero).json()[0]
    assert mia["estado"] == "CONFIRMADA"  # el Cajero la ve confirmada al consultar (CU-39)
    assert client.post(f"/api/offline/conflictos/{c["id"]}/resolver", json={"accion": "REINTENTAR"}, headers=inv.h_enc_centro).json()["detail"] == "La operación ya no está en conflicto."


def test_09_descartar_exige_un_motivo_y_avisa_que_se_devuelva_el_efectivo(inv, mundo, client, db):
    stock_listo(inv, mundo)
    c = _conflicto(client, inv, db)
    r = client.post(f"/api/offline/conflictos/{c["id"]}/resolver", json={"accion": "DESCARTAR", "motivo": "  "}, headers=inv.h_enc_centro)
    assert r.status_code == 422 and r.json()["detail"] == "Indique el motivo del descarte."
    r = client.post(f"/api/offline/conflictos/{c["id"]}/resolver", json={"accion": "DESCARTAR", "motivo": "El cliente ya se fue"}, headers=inv.h_enc_centro)
    d = r.json()
    assert (d["estado"], d["resolucion"], d["motivo_resolucion"]) == ("RECHAZADA", "DESCARTADA", "El cliente ya se fue")
    assert d["mensaje"].endswith("Devuelva el efectivo recibido al cliente.") and client.get("/api/offline/conflictos", headers=inv.h_enc_centro).json() == []
    assert client.get("/api/offline/operaciones", headers=inv.h_cajero).json()[0]["estado"] == "RECHAZADA"


def test_10_roles_sucursal_y_empresa_en_la_resolucion(inv, mundo, tienda_b, client, db):
    stock_listo(inv, mundo)
    c = _conflicto(client, inv, db)
    ruta = f"/api/offline/conflictos/{c["id"]}/resolver"
    for h in (inv.h_cajero, inv.h_cliente):
        assert client.get("/api/offline/conflictos", headers=h).status_code == 403
        assert client.post(ruta, json={"accion": "REINTENTAR"}, headers=h).status_code == 403
    assert client.post(ruta, json={"accion": "REINTENTAR"}, headers=inv.h_enc_norte).status_code == 404  # otra sucursal
    assert client.post(ruta, json={"accion": "REINTENTAR"}, headers=tienda_b.h_admin).status_code == 404  # otra empresa
    assert client.post(ruta, json={"accion": "ANULAR"}, headers=inv.h_enc_centro).status_code == 422


def test_11_una_sucursal_con_conflictos_no_se_puede_desactivar(inv, mundo, client, db):
    stock_listo(inv, mundo)
    c = _conflicto(client, inv, db)
    r = client.post(f"/api/sucursales/{inv.centro.id}/desactivar", headers=inv.h_admin)
    assert r.status_code == 409 and "operaciones sin sincronizar" in r.json()["detail"]
    client.post(f"/api/offline/conflictos/{c["id"]}/resolver", json={"accion": "DESCARTAR", "motivo": "Duplicada"}, headers=inv.h_enc_centro)
    assert client.post(f"/api/sucursales/{inv.centro.id}/desactivar", headers=inv.h_admin).status_code == 200  # resuelto el conflicto, ya se puede

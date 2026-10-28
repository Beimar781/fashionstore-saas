"""CU-12 Consultar historial de compras — pasos de la ficha (5.2.1) y aislamiento."""
from tests.catalogo_util import cabecera_cliente, entrar
from tests.compras_util import SIN_FONDOS, TIMEOUT, agregar_ok, checkout_ok, comprar, pagar, stock_listo

MSG_SIN_COMPRAS = "Aún no has realizado ninguna compra en nuestras tiendas."


def test_01_la_lista_muestra_monto_sucursal_y_estado_ordenada_por_fecha(inv, mundo, client):
    stock_listo(inv, mundo)
    a = comprar(client, inv.h_cliente, inv, inv.v_sm_rojo, 1)
    b = comprar(client, inv.h_cliente, inv, inv.var[("M", "Azul")], 2, sucursal=inv.norte)
    r = client.get("/api/compras", headers=inv.h_cliente).json()
    assert r["mensaje"] is None
    assert [c["id"] for c in r["compras"]] == [b["id"], a["id"]]  # la más reciente primero
    nueva = r["compras"][0]
    assert (nueva["total"], nueva["sucursal"], nueva["estado"], nueva["total_unidades"], nueva["canal"]) == ("200.00", "Norte", "PAGADO", 2, "DIGITAL")
    assert nueva["comprobante_numero"].startswith(f"CMP-{inv.norte.id:03d}-")


def test_02_se_listan_las_compras_digitales_y_las_que_esperan_confirmacion(inv, mundo, client):
    stock_listo(inv, mundo)
    comprar(client, inv.h_cliente, inv, inv.v_sm_rojo, 1)
    agregar_ok(client, inv.h_cliente, inv.var[("M", "Azul")], inv.centro)
    p = checkout_ok(client, inv.h_cliente)
    assert pagar(client, inv.h_cliente, p["id"], TIMEOUT).json()["pendiente"] is True
    estados = {c["estado"] for c in client.get("/api/compras", headers=inv.h_cliente).json()["compras"]}
    assert estados == {"PAGADO", "PENDIENTE_CONFIRMACION"}
    pagado = client.get("/api/compras?estado=PAGADO", headers=inv.h_cliente).json()["compras"]
    assert len(pagado) == 1 and pagado[0]["estado"] == "PAGADO"


def test_03_los_pedidos_sin_pagar_no_son_compras(inv, mundo, client):
    stock_listo(inv, mundo)
    agregar_ok(client, inv.h_cliente, inv.v_sm_rojo, inv.centro)
    p = checkout_ok(client, inv.h_cliente)  # pedido por pagar
    pagar(client, inv.h_cliente, p["id"], SIN_FONDOS)  # intento rechazado
    r = client.get("/api/compras", headers=inv.h_cliente).json()
    assert r["compras"] == [] and r["mensaje"] == MSG_SIN_COMPRAS


def test_04_el_detalle_del_pedido(inv, mundo, client):
    stock_listo(inv, mundo)
    p = comprar(client, inv.h_cliente, inv, inv.v_sm_rojo, 2)
    d = client.get(f"/api/compras/{p['id']}", headers=inv.h_cliente).json()
    assert (d["codigo"], d["estado"], d["sucursal"], d["total"], d["tipo_entrega"], d["nit_ci"]) == (p["codigo"], "PAGADO", "Centro", "200.00", "RETIRO", "1234567")
    assert [(i["producto"], i["talla"], i["color"], i["cantidad"], i["subtotal"]) for i in d["items"]] == [("Camisa Oxford", "S", "Rojo", 2, "200.00")]
    assert [(g["estado"], g["tarjeta_marca"], g["tarjeta_ultimos4"]) for g in d["pagos"]] == [("APROBADO", "Visa", "4242")]


def test_05_descargar_el_comprobante(inv, mundo, client):
    stock_listo(inv, mundo)
    p = comprar(client, inv.h_cliente, inv, inv.v_sm_rojo, 1)
    r = client.get(f"/api/compras/{p['id']}/comprobante", headers=inv.h_cliente)
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
    assert r.headers["content-disposition"] == f'attachment; filename="{p["comprobante_numero"]}.pdf"'
    assert r.content.startswith(b"%PDF") and len(r.content) > 1500


def test_06_sin_compras_muestra_el_mensaje_de_la_ficha(inv, client):
    r = client.get("/api/compras", headers=inv.h_cliente)
    assert r.status_code == 200 and r.json() == {"compras": [], "mensaje": MSG_SIN_COMPRAS}


def test_07_no_hay_comprobante_de_un_pedido_sin_pagar(inv, mundo, client):
    stock_listo(inv, mundo)
    agregar_ok(client, inv.h_cliente, inv.v_sm_rojo, inv.centro)
    p = checkout_ok(client, inv.h_cliente)
    r = client.get(f"/api/compras/{p['id']}/comprobante", headers=inv.h_cliente)
    assert r.status_code == 409 and r.json()["detail"] == "Solo hay comprobante para compras pagadas."


def test_08_los_comprobantes_se_numeran_por_sucursal(inv, mundo, client):
    stock_listo(inv, mundo)
    numeros = [comprar(client, inv.h_cliente, inv, inv.v_sm_rojo, 1)["comprobante_numero"] for _ in range(2)]
    en_norte = comprar(client, inv.h_cliente, inv, inv.v_sm_rojo, 1, sucursal=inv.norte)["comprobante_numero"]
    assert numeros == [f"CMP-{inv.centro.id:03d}-000001", f"CMP-{inv.centro.id:03d}-000002"]
    assert en_norte == f"CMP-{inv.norte.id:03d}-000001"  # cada sucursal lleva su propia secuencia


def test_09_solo_se_ven_las_compras_propias(inv, mundo, tienda_b, datos, client):
    stock_listo(inv, mundo)
    p = comprar(client, inv.h_cliente, inv, inv.v_sm_rojo, 1)
    datos.usuario(mundo.a, "Cliente", email="otro@a.com")
    for h in (entrar(client, mundo.a, "otro@a.com"), cabecera_cliente(datos, mundo.b)):
        assert client.get("/api/compras", headers=h).json() == {"compras": [], "mensaje": MSG_SIN_COMPRAS}
        assert client.get(f"/api/compras/{p['id']}", headers=h).status_code == 404
        assert client.get(f"/api/compras/{p['id']}/comprobante", headers=h).status_code == 404


def test_10_solo_el_cliente_consulta_su_historial(inv, client):
    for h in (inv.h_enc_centro, inv.h_cajero, inv.h_admin):
        assert client.get("/api/compras", headers=h).status_code == 403

"""CU-27 Consultar ventas de la sucursal — pasos de la ficha (5.2.1) y aislamiento entre sucursales y empresas."""
from tests.caja_util import stock_listo, vender
from tests.catalogo_util import cabecera_cliente, entrar
from tests.compras_util import agregar_ok, checkout_ok, pagar
from tests.devoluciones_util import venta_con_tarjeta
from tests.reservas_util import fecha_local, reserva_ok

MSG_OTRA_SUCURSAL = "Acceso denegado a datos de otras sucursales."


def _movimiento(inv, mundo, client):
    """Centro: 2 ventas de caja (efectivo y tarjeta), 1 compra digital pagada, 1 reserva completada sin compra. Norte: 1 venta."""
    stock_listo(inv, mundo)
    a = vender(client, inv.h_cajero, (inv.v_sm_rojo, 2), metodo="EFECTIVO", recibido=250)  # Bs 200
    b = {"pedido": venta_con_tarjeta(client, inv, (inv.var[("M", "Azul")], 1))}  # Bs 100 con tarjeta en caja
    agregar_ok(client, inv.h_cliente, inv.v_sm_rojo, inv.centro, 3)
    d = pagar(client, inv.h_cliente, checkout_ok(client, inv.h_cliente)["id"]).json()["pedido"]  # Bs 300 digital
    res = reserva_ok(client, inv.h_cliente, inv.centro, (inv.var[("S", "Azul")], 1))
    client.post(f"/api/atencion-reservas/{res['id']}/atender", headers=inv.h_enc_centro)
    client.post(f"/api/atencion-reservas/{res['id']}/completar", json={"llevara_prendas": False}, headers=inv.h_enc_centro)
    en_norte = vender(client, inv.h_enc_norte, (inv.v_sm_rojo, 4))  # Bs 400 en otra sucursal
    return a["pedido"], b["pedido"], d, en_norte["pedido"]


def test_01_el_resumen_muestra_ventas_cierre_de_caja_y_reservas_completadas(inv, mundo, client):
    _movimiento(inv, mundo, client)
    r = client.get("/api/reportes/sucursal/resumen", headers=inv.h_enc_centro)
    assert r.status_code == 200
    s = r.json()
    assert (s["sucursal"], s["total_vendido"], s["ventas"], s["unidades"], s["ticket_promedio"]) == ("Centro", "600.00", 3, 6, "200.00")
    assert (s["presencial"]["total"], s["presencial"]["ventas"], s["digital"]["total"], s["digital"]["ventas"]) == ("300.00", 2, "300.00", 1)
    cierre = {c["metodo"]: c for c in s["cierre_de_caja"]}
    assert (cierre["EFECTIVO"]["total"], cierre["EFECTIVO"]["recibido"], cierre["EFECTIVO"]["cambio"]) == ("200.00", "250.00", "50.00")
    assert (cierre["TARJETA"]["cobros"], cierre["TARJETA"]["total"]) == (2, "400.00")  # la venta de caja y la compra digital, ambas con tarjeta
    assert s["efectivo_en_caja"] == "200.00" and s["reservas_completadas"] == 1


def test_02_los_totales_coinciden_con_los_tickets(inv, mundo, client):
    _movimiento(inv, mundo, client)
    resumen = client.get("/api/reportes/sucursal/resumen", headers=inv.h_enc_centro).json()
    lista = client.get("/api/reportes/sucursal/ventas", headers=inv.h_enc_centro).json()
    assert lista["total"] == resumen["total_vendido"] == "600.00" and len(lista["tickets"]) == resumen["ventas"] == 3
    assert sum(float(t["total"]) for t in lista["tickets"]) == 600.0
    assert sum(t["unidades"] for t in lista["tickets"]) == resumen["unidades"]
    assert sorted(t["metodo"] for t in lista["tickets"]) == ["EFECTIVO", "TARJETA", "TARJETA"]


def test_03_el_detalle_de_un_ticket(inv, mundo, client):
    a, _, d, _ = _movimiento(inv, mundo, client)
    t = client.get(f"/api/reportes/sucursal/ventas/{a['id']}", headers=inv.h_enc_centro)
    assert t.status_code == 200
    det = t.json()
    assert (det["codigo"], det["comprobante_numero"], det["vendedor"], det["total"], det["estado"]) == (a["codigo"], a["comprobante_numero"], "Cajero Prueba", "200.00", "PAGADO")
    assert [(i["producto"], i["talla"], i["color"], i["cantidad"]) for i in det["items"]] == [("Camisa Oxford", "S", "Rojo", 2)]
    assert [(g["metodo"], g["monto_recibido"], g["cambio"]) for g in det["pagos"]] == [("EFECTIVO", "250.00", "50.00")]
    digital = client.get(f"/api/reportes/sucursal/ventas/{d['id']}", headers=inv.h_enc_centro).json()
    assert (digital["canal"], digital["cliente"]) == ("DIGITAL", "Cliente Prueba")  # también el recojo de pedidos online


def test_04_el_listado_tiene_solo_datos_de_la_sucursal_del_encargado(inv, mundo, client):
    _, _, _, norte = _movimiento(inv, mundo, client)
    ids_centro = {t["id"] for t in client.get("/api/reportes/sucursal/ventas", headers=inv.h_enc_centro).json()["tickets"]}
    assert norte["id"] not in ids_centro
    ventas_norte = client.get("/api/reportes/sucursal/ventas", headers=inv.h_enc_norte).json()
    assert [t["id"] for t in ventas_norte["tickets"]] == [norte["id"]] and ventas_norte["total"] == "400.00"
    assert client.get("/api/reportes/sucursal/resumen", headers=inv.h_enc_norte).json()["total_vendido"] == "400.00"


def test_05_pedir_los_datos_de_otra_sucursal_se_bloquea(inv, mundo, client):
    _, _, _, norte = _movimiento(inv, mundo, client)
    for url in (f"/api/reportes/sucursal/resumen?sucursal={inv.norte.id}", f"/api/reportes/sucursal/ventas?sucursal={inv.norte.id}"):
        r = client.get(url, headers=inv.h_enc_centro)
        assert r.status_code == 403 and r.json()["detail"] == MSG_OTRA_SUCURSAL
    r = client.get(f"/api/reportes/sucursal/ventas/{norte['id']}", headers=inv.h_enc_centro)  # el ticket de otra sucursal
    assert r.status_code == 403 and r.json()["detail"] == MSG_OTRA_SUCURSAL
    assert client.get(f"/api/reportes/sucursal/resumen?sucursal={inv.centro.id}", headers=inv.h_enc_centro).status_code == 200  # la propia sí


def test_06_filtros_por_canal_metodo_y_fecha(inv, mundo, client):
    _movimiento(inv, mundo, client)
    pos = client.get("/api/reportes/sucursal/ventas?canal=PRESENCIAL", headers=inv.h_enc_centro).json()
    assert len(pos["tickets"]) == 2 and pos["total"] == "300.00"
    efectivo = client.get("/api/reportes/sucursal/ventas?metodo=EFECTIVO", headers=inv.h_enc_centro).json()
    assert [t["total"] for t in efectivo["tickets"]] == ["200.00"]
    ayer = client.get(f"/api/reportes/sucursal/ventas?desde={fecha_local(-1)}&hasta={fecha_local(-1)}", headers=inv.h_enc_centro).json()
    assert ayer["tickets"] == [] and ayer["total"] == "0.00"
    resumen = client.get(f"/api/reportes/sucursal/resumen?fecha={fecha_local(-1)}", headers=inv.h_enc_centro).json()
    assert (resumen["total_vendido"], resumen["ventas"], resumen["ticket_promedio"], resumen["cierre_de_caja"], resumen["reservas_completadas"]) == ("0.00", 0, "0.00", [], 0)


def test_07_no_cuentan_las_ventas_sin_cobrar_ni_las_anuladas(inv, mundo, client):
    from tests.caja_util import venta_ok
    stock_listo(inv, mundo)
    pendiente = venta_ok(client, inv.h_cajero, (inv.v_sm_rojo, 1))
    anulada = venta_ok(client, inv.h_cajero, (inv.v_sm_rojo, 1))
    client.delete(f"/api/caja/ventas/{anulada['id']}", headers=inv.h_cajero)
    assert client.get("/api/reportes/sucursal/ventas", headers=inv.h_enc_centro).json()["tickets"] == []
    assert client.get(f"/api/reportes/sucursal/ventas/{pendiente['id']}", headers=inv.h_enc_centro).status_code == 404


def test_08_otra_empresa_no_ve_nada(inv, mundo, tienda_b, datos, client):
    a, *_ = _movimiento(inv, mundo, client)
    datos.usuario(mundo.b, "Encargado", email="enc@b.com", sucursal=datos.sucursal(mundo.b, "Sucursal B"))
    h_b = entrar(client, mundo.b, "enc@b.com")
    assert client.get("/api/reportes/sucursal/ventas", headers=h_b).json()["tickets"] == []
    assert client.get("/api/reportes/sucursal/resumen", headers=h_b).json()["total_vendido"] == "0.00"
    assert client.get(f"/api/reportes/sucursal/ventas/{a['id']}", headers=h_b).status_code == 404  # no se revela que existe en otra empresa
    cabecera_cliente(datos, mundo.b)


def test_09_solo_el_encargado_consulta_las_ventas_de_la_sucursal(inv, client):
    for h in (inv.h_cajero, inv.h_admin, inv.h_cliente, inv.h_prov):
        assert client.get("/api/reportes/sucursal/resumen", headers=h).status_code == 403
        assert client.get("/api/reportes/sucursal/ventas", headers=h).status_code == 403
    assert client.get("/api/reportes/sucursal/resumen").status_code == 401

"""CU-41 Gestionar devoluciones de prendas — comprobante, plazo, cantidades, inventario, reembolso y aislamiento (RN15)."""
from datetime import datetime

from sqlalchemy import select

from app.modules.ventas.models import Devolucion
from app.primer_parcial.ventas.models import Pago
from tests.catalogo_util import cabecera_cliente, entrar
from tests.compras_util import comprar, existencias, stock_listo
from tests.devoluciones_util import devolver, devolver_ok, envejecer_venta, venta_con_tarjeta, venta_en_caja

MSG_SIN_COMPROBANTE = "Para devolver o cambiar una prenda se requiere el comprobante de la venta."
MSG_NO_ENCONTRADA = "No se encontró una venta con ese comprobante en su sucursal."


def test_01_buscar_la_venta_por_su_comprobante(inv, mundo, client):
    stock_listo(inv, mundo)
    p = venta_en_caja(client, inv, (inv.v_sm_rojo, 3))
    r = client.get("/api/devoluciones/venta", params={"comprobante": p["comprobante_numero"].lower()}, headers=inv.h_cajero)
    assert r.status_code == 200
    v = r.json()
    assert (v["pedido"]["codigo"], v["medio_pago"], v["plazo_dias"], v["dentro_del_plazo"], v["devoluciones"]) == (p["codigo"], "EFECTIVO", 15, True, [])
    assert [(i["producto"], i["vendida"], i["devuelta"], i["devolvible"]) for i in v["items"]] == [("Camisa Oxford", 3, 0, 3)]


def test_02_se_requiere_el_comprobante_de_la_venta(inv, mundo, client):
    stock_listo(inv, mundo)
    for comprobante in ("", "   "):
        r = client.get("/api/devoluciones/venta", params={"comprobante": comprobante}, headers=inv.h_cajero)
        assert r.status_code == 422 and r.json()["detail"] == MSG_SIN_COMPROBANTE
        assert devolver(client, inv.h_cajero, comprobante, [({"id": 1}, 1)]).json()["detail"] == MSG_SIN_COMPROBANTE
    r = client.get("/api/devoluciones/venta", params={"comprobante": "CMP-999-000001"}, headers=inv.h_cajero)
    assert r.status_code == 404 and r.json()["detail"] == MSG_NO_ENCONTRADA


def test_03_devolucion_total_reingresa_al_inventario_y_emite_la_nota(inv, mundo, client):
    stock_listo(inv, mundo)
    p = venta_en_caja(client, inv, (inv.v_sm_rojo, 3))
    assert existencias(client, inv.h_enc_centro, inv.v_sm_rojo)["vendida"] == 3
    d = devolver_ok(client, inv.h_cajero, p["comprobante_numero"], [(p["items"][0], 3)], motivo="No era su talla")
    assert (d["numero"], d["tipo"], d["motivo"], d["monto_devuelto"], d["reembolso"], d["medio_reembolso"], d["registrada_por"]) == (
        f"NDV-{inv.centro.id:03d}-000001", "DEVOLUCION", "No era su talla", "300.00", "300.00", "EFECTIVO", "Cajero Prueba")
    assert [(i["sentido"], i["cantidad"], i["subtotal"]) for i in d["items"]] == [("DEVUELTA", 3, "300.00")]
    f = existencias(client, inv.h_enc_centro, inv.v_sm_rojo)
    assert (f["disponible"], f["vendida"]) == (10, 0)  # la prenda vuelve al inventario de la sucursal
    m = client.get("/api/inventario/movimientos", params={"tipo": "DEVOLUCION"}, headers=inv.h_enc_centro).json()["items"][0]
    assert (m["cantidad"], m["referencia_tipo"], m["referencia_id"], m["usuario"]) == (3, "DEVOLUCION", d["id"], "Cajero Prueba")
    assert "No era su talla" in m["nota"] and d["numero"] in m["nota"]


def test_04_devolucion_parcial_y_nunca_mas_de_lo_vendido(inv, mundo, client):
    stock_listo(inv, mundo)
    p = venta_en_caja(client, inv, (inv.v_sm_rojo, 3))
    linea, c = p["items"][0], p["comprobante_numero"]
    devolver_ok(client, inv.h_cajero, c, [(linea, 1)])
    v = client.get("/api/devoluciones/venta", params={"comprobante": c}, headers=inv.h_cajero).json()
    assert (v["items"][0]["devuelta"], v["items"][0]["devolvible"], len(v["devoluciones"])) == (1, 2, 1)
    r = devolver(client, inv.h_cajero, c, [(linea, 3)])  # quedan 2: pedir 3 es más de lo vendido
    assert r.status_code == 409
    assert r.json()["detail"] == "Solo se pueden devolver 2 unidad(es) de Camisa Oxford (S, Rojo): se vendieron 3 y ya se devolvieron 1."
    devolver_ok(client, inv.h_cajero, c, [(linea, 2)])
    f = existencias(client, inv.h_enc_centro, inv.v_sm_rojo)
    assert (f["disponible"], f["vendida"]) == (10, 0)


def test_05_la_misma_prenda_no_se_devuelve_dos_veces(inv, mundo, client):
    stock_listo(inv, mundo)
    p = venta_en_caja(client, inv, (inv.v_sm_rojo, 2))
    linea, c = p["items"][0], p["comprobante_numero"]
    devolver_ok(client, inv.h_cajero, c, [(linea, 2)])
    r = devolver(client, inv.h_cajero, c, [(linea, 1)])  # devolución repetida
    assert r.status_code == 409 and r.json()["detail"] == "Camisa Oxford (S, Rojo) ya fue devuelto por completo."
    assert existencias(client, inv.h_enc_centro, inv.v_sm_rojo)["disponible"] == 10  # la repetida no reingresó nada
    assert len(client.get("/api/devoluciones", headers=inv.h_cajero).json()) == 1
    # lo mismo si se repite el pedido exacto: no se acepta dos veces
    assert devolver(client, inv.h_cajero, c, [(linea, 2)]).status_code == 409


def test_06_motivo_prendas_y_pertenencia_a_la_venta(inv, mundo, client):
    stock_listo(inv, mundo)
    p = venta_en_caja(client, inv, (inv.v_sm_rojo, 1))
    otra = venta_en_caja(client, inv, (inv.var[("M", "Azul")], 1))
    linea, c = p["items"][0], p["comprobante_numero"]
    r = devolver(client, inv.h_cajero, c, [(linea, 1)], motivo="   ")
    assert r.status_code == 422 and r.json()["detail"] == "Indique el motivo de la devolución."
    r = devolver(client, inv.h_cajero, c, [])
    assert r.status_code == 422 and r.json()["detail"] == "Seleccione al menos una prenda a devolver."
    r = devolver(client, inv.h_cajero, c, [(otra["items"][0], 1)])  # una línea de OTRA venta
    assert r.status_code == 422 and r.json()["detail"] == "La prenda indicada no pertenece a esa venta."
    assert devolver(client, inv.h_cajero, c, [(linea, 0)]).status_code == 422  # cantidad inválida
    assert existencias(client, inv.h_enc_centro, inv.v_sm_rojo)["vendida"] == 1


def test_07_fuera_del_plazo_no_se_acepta_y_el_plazo_es_configurable(inv, mundo, client, db):
    stock_listo(inv, mundo)
    p = venta_en_caja(client, inv, (inv.v_sm_rojo, 1))
    linea, c = p["items"][0], p["comprobante_numero"]
    envejecer_venta(db, p["id"], 20)
    r = devolver(client, inv.h_cajero, c, [(linea, 1)])
    assert r.status_code == 409 and r.json()["detail"].startswith("El plazo para devolver o cambiar esta compra venció el ")
    assert r.json()["detail"].endswith("(plazo de 15 días).")
    assert client.get("/api/devoluciones/venta", params={"comprobante": c}, headers=inv.h_cajero).json()["dentro_del_plazo"] is False
    assert client.get("/api/devoluciones/configuracion", headers=inv.h_cajero).json() == {"plazo_dias": 15}
    # el Administrador amplía el plazo de su empresa y la misma venta ya se puede devolver
    assert client.put("/api/devoluciones/configuracion", json={"plazo_dias": 30}, headers=inv.h_admin).json() == {"plazo_dias": 30}
    assert devolver(client, inv.h_cajero, c, [(linea, 1)]).status_code == 201


def test_08_solo_el_administrador_cambia_el_plazo(inv, mundo, tienda_b, client):
    for h in (inv.h_cajero, inv.h_enc_centro, inv.h_cliente, inv.h_prov):
        assert client.put("/api/devoluciones/configuracion", json={"plazo_dias": 5}, headers=h).status_code == 403
    for dias in (-1, 400):
        assert client.put("/api/devoluciones/configuracion", json={"plazo_dias": dias}, headers=inv.h_admin).status_code == 422
    client.put("/api/devoluciones/configuracion", json={"plazo_dias": 3}, headers=inv.h_admin)
    assert client.get("/api/devoluciones/configuracion", headers=tienda_b.h_admin).json() == {"plazo_dias": 15}  # cada empresa tiene su plazo


def test_09_compra_digital_con_tarjeta_se_reembolsa_por_la_pasarela(inv, mundo, client, db):
    stock_listo(inv, mundo)
    p = comprar(client, inv.h_cliente, inv, inv.v_sm_rojo, 2)  # compra online pagada con tarjeta
    d = devolver_ok(client, inv.h_enc_centro, p["comprobante_numero"], [(p["items"][0], 1)])
    assert (d["medio_reembolso"], d["reembolso"]) == ("TARJETA", "100.00") and d["referencia_reembolso"].startswith("sim_re_")
    f = existencias(client, inv.h_enc_centro, inv.v_sm_rojo)
    assert (f["disponible"], f["vendida"]) == (9, 1)
    pago = db.scalars(select(Pago).where(Pago.pedido_id == p["id"])).one()
    assert db.scalars(select(Devolucion.reembolso_pasarela).where(Devolucion.pedido_id == p["id"])).one() == round(pago.monto_pasarela / 2)


def test_10_venta_de_caja_con_tarjeta_tambien_se_reembolsa_a_la_tarjeta(inv, mundo, client):
    stock_listo(inv, mundo)
    p = venta_con_tarjeta(client, inv, (inv.v_sm_rojo, 1))
    d = devolver_ok(client, inv.h_cajero, p["comprobante_numero"], [(p["items"][0], 1)])
    assert (d["medio_reembolso"], d["reembolso"]) == ("TARJETA", "100.00") and d["referencia_reembolso"]


def test_11_reembolsos_parciales_suman_exactamente_lo_cobrado(inv, mundo, client, db):
    stock_listo(inv, mundo)
    p = comprar(client, inv.h_cliente, inv, inv.v_sm_rojo, 3)  # Bs 300 cobrados
    pago = db.scalars(select(Pago).where(Pago.pedido_id == p["id"])).one()
    for _ in range(3):
        devolver_ok(client, inv.h_cajero, p["comprobante_numero"], [(p["items"][0], 1)])
    centavos = db.scalars(select(Devolucion.reembolso_pasarela).where(Devolucion.pedido_id == p["id"])).all()
    assert sum(centavos) == pago.monto_pasarela  # el último reembolso devuelve lo que quedaba, sin descuadre por redondeo


def test_12_si_la_pasarela_falla_la_devolucion_no_se_registra(inv, mundo, client, db, monkeypatch):
    from app.primer_parcial.ventas.cu32_pago_electronico.pasarela import PasarelaSimulada

    stock_listo(inv, mundo)
    p = comprar(client, inv.h_cliente, inv, inv.v_sm_rojo, 1)
    monkeypatch.setattr(PasarelaSimulada, "reembolsar", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("sin conexión")))
    r = devolver(client, inv.h_cajero, p["comprobante_numero"], [(p["items"][0], 1)])
    assert r.status_code == 502 and r.json()["detail"] == "No se pudo reembolsar el pago en la pasarela: la devolución no se registró. Intente nuevamente."
    f = existencias(client, inv.h_enc_centro, inv.v_sm_rojo)
    assert (f["disponible"], f["vendida"]) == (9, 1)  # nada a medias: el inventario no cambió
    assert client.get("/api/devoluciones", headers=inv.h_cajero).json() == []
    monkeypatch.undo()
    assert devolver(client, inv.h_cajero, p["comprobante_numero"], [(p["items"][0], 1)]).status_code == 201  # al volver la pasarela se puede


def test_13_reembolso_de_stripe_se_hace_con_la_misma_tarjeta(inv, mundo, client, db, monkeypatch):
    from app.modules.ventas.cu41_devoluciones import service
    from app.primer_parcial.ventas.cu32_pago_electronico.pasarela import PasarelaStripe
    from tests.stripe_falso import StripeFalso

    stock_listo(inv, mundo)
    p = comprar(client, inv.h_cliente, inv, inv.v_sm_rojo, 2)  # Bs 200 = 2874 centavos de dólar
    db.execute(Pago.__table__.update().where(Pago.pedido_id == p["id"]).values(proveedor="STRIPE", referencia_externa="pi_prueba"))
    db.commit()
    falso = StripeFalso()
    monkeypatch.setattr(service, "pasarela_para", lambda proveedor: PasarelaStripe("sk_test_falsa", "pk_test_falsa", sdk=falso) if proveedor == "STRIPE" else None)
    d = devolver_ok(client, inv.h_cajero, p["comprobante_numero"], [(p["items"][0], 1)])
    assert falso.hizo("reembolsar")[0][1]["payment_intent"] == "pi_prueba" and falso.hizo("reembolsar")[0][1]["amount"] == 1437  # la mitad
    assert d["referencia_reembolso"] == "re_1"
    devolver_ok(client, inv.h_cajero, p["comprobante_numero"], [(p["items"][0], 1)])
    assert falso.hizo("reembolsar")[1][1]["amount"] == 2874 - 1437  # el último devuelve exactamente el resto


def test_14_stripe_ya_no_configurado_no_permite_reembolsar_ese_pago(inv, mundo, client, db):
    stock_listo(inv, mundo)
    p = comprar(client, inv.h_cliente, inv, inv.v_sm_rojo, 1)
    db.execute(Pago.__table__.update().where(Pago.pedido_id == p["id"]).values(proveedor="STRIPE", referencia_externa="pi_prueba"))
    db.commit()
    r = devolver(client, inv.h_cajero, p["comprobante_numero"], [(p["items"][0], 1)])  # sin claves de Stripe en este entorno
    assert r.status_code == 502 and existencias(client, inv.h_enc_centro, inv.v_sm_rojo)["vendida"] == 1


def test_15_la_nota_se_descarga_en_pdf_y_se_consulta(inv, mundo, client):
    stock_listo(inv, mundo)
    p = venta_en_caja(client, inv, (inv.v_sm_rojo, 2))
    d = devolver_ok(client, inv.h_cajero, p["comprobante_numero"], [(p["items"][0], 1)])
    r = client.get(f"/api/devoluciones/{d['id']}/nota", headers=inv.h_cajero)
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf" and r.content.startswith(b"%PDF") and len(r.content) > 1500
    assert r.headers["content-disposition"] == f'inline; filename="{d["numero"]}.pdf"'
    assert client.get(f"/api/devoluciones/{d['id']}", headers=inv.h_enc_centro).json()["comprobante"] == p["comprobante_numero"]
    assert [x["id"] for x in client.get("/api/devoluciones", headers=inv.h_enc_centro).json()] == [d["id"]]


def test_16_las_notas_se_numeran_por_sucursal(inv, mundo, client):
    stock_listo(inv, mundo)
    a = venta_en_caja(client, inv, (inv.v_sm_rojo, 2))
    d1 = devolver_ok(client, inv.h_cajero, a["comprobante_numero"], [(a["items"][0], 1)])
    d2 = devolver_ok(client, inv.h_cajero, a["comprobante_numero"], [(a["items"][0], 1)])
    from tests.caja_util import vender
    n = vender(client, inv.h_enc_norte, (inv.v_sm_rojo, 1))["pedido"]
    d3 = devolver_ok(client, inv.h_enc_norte, n["comprobante_numero"], [(n["items"][0], 1)])
    assert [d1["numero"], d2["numero"], d3["numero"]] == [f"NDV-{inv.centro.id:03d}-000001", f"NDV-{inv.centro.id:03d}-000002", f"NDV-{inv.norte.id:03d}-000001"]


def test_17_el_personal_solo_devuelve_ventas_de_su_sucursal(inv, mundo, client):
    stock_listo(inv, mundo)
    p = venta_en_caja(client, inv, (inv.v_sm_rojo, 1))  # venta de Centro
    r = devolver(client, inv.h_enc_norte, p["comprobante_numero"], [(p["items"][0], 1)])
    assert r.status_code == 404 and r.json()["detail"] == MSG_NO_ENCONTRADA
    assert client.get("/api/devoluciones/venta", params={"comprobante": p["comprobante_numero"]}, headers=inv.h_enc_norte).status_code == 404
    d = devolver_ok(client, inv.h_enc_centro, p["comprobante_numero"], [(p["items"][0], 1)])  # el Encargado de Centro sí
    assert client.get(f"/api/devoluciones/{d['id']}", headers=inv.h_enc_norte).status_code == 404
    assert client.get(f"/api/devoluciones/{d['id']}/nota", headers=inv.h_enc_norte).status_code == 404
    assert client.get("/api/devoluciones", headers=inv.h_enc_norte).json() == []


def test_18_aislamiento_entre_empresas(inv, mundo, tienda_b, datos, client):
    stock_listo(inv, mundo)
    p = venta_en_caja(client, inv, (inv.v_sm_rojo, 1))
    d = devolver_ok(client, inv.h_cajero, p["comprobante_numero"], [(p["items"][0], 1)])
    datos.usuario(mundo.b, "Cajero", email="cajero@b.com", sucursal=datos.sucursal(mundo.b, "Sucursal B"))
    h_b = entrar(client, mundo.b, "cajero@b.com")
    r = devolver(client, h_b, p["comprobante_numero"], [(p["items"][0], 1)])  # el comprobante de A no existe en B
    assert r.status_code == 404 and r.json()["detail"] == MSG_NO_ENCONTRADA
    assert client.get(f"/api/devoluciones/{d['id']}", headers=h_b).status_code == 404
    assert client.get("/api/devoluciones", headers=h_b).json() == []
    assert client.get("/api/devoluciones", headers=tienda_b.h_admin).json() == []
    cabecera_cliente(datos, mundo.b)


def test_19_roles(inv, mundo, client):
    stock_listo(inv, mundo)
    p = venta_en_caja(client, inv, (inv.v_sm_rojo, 1))
    for h in (inv.h_cliente, inv.h_admin, inv.h_prov):  # solo Cajero y Encargado registran devoluciones
        assert devolver(client, h, p["comprobante_numero"], [(p["items"][0], 1)]).status_code == 403
        assert client.get("/api/devoluciones/venta", params={"comprobante": p["comprobante_numero"]}, headers=h).status_code == 403
    d = devolver_ok(client, inv.h_cajero, p["comprobante_numero"], [(p["items"][0], 1)])
    assert client.get("/api/devoluciones", headers=inv.h_admin).json()[0]["id"] == d["id"]  # el Administrador consulta todas
    assert client.get(f"/api/devoluciones/{d['id']}/nota", headers=inv.h_admin).status_code == 200
    assert client.get("/api/devoluciones", headers=inv.h_cliente).status_code == 403
    assert client.get("/api/devoluciones").status_code == 401


def test_20_las_devoluciones_restan_en_las_ventas_netas_del_reporte(inv, mundo, client):
    stock_listo(inv, mundo)
    a = venta_en_caja(client, inv, (inv.v_sm_rojo, 3))  # Bs 300 en efectivo
    p = comprar(client, inv.h_cliente, inv, inv.var[("M", "Azul")], 2)  # Bs 200 online con tarjeta
    devolver_ok(client, inv.h_cajero, a["comprobante_numero"], [(a["items"][0], 1)])  # reembolso de Bs 100 en efectivo
    devolver_ok(client, inv.h_cajero, p["comprobante_numero"], [(p["items"][0], 1)])  # reembolso de Bs 100 a la tarjeta
    s = client.get("/api/reportes/sucursal/resumen", headers=inv.h_enc_centro).json()
    assert (s["total_vendido"], s["ventas_netas"]) == ("500.00", "300.00")  # 500 vendidos menos 200 devueltos
    dev = s["devoluciones"]
    assert (dev["notas"], dev["devuelto"], dev["reembolsado_efectivo"], dev["reembolsado_tarjeta"], dev["entregado_en_cambios"]) == (2, "200.00", "100.00", "100.00", "0.00")
    assert s["efectivo_en_caja"] == "200.00"  # 300 cobrados en efectivo menos 100 devueltos en efectivo

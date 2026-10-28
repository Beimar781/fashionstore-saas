"""CU-11 Realizar compra digital (checkout) — pasos de la ficha (5.2.1), stock al pagar y aislamiento entre empresas."""
from sqlalchemy import select

from app.primer_parcial.ventas.models import Pago
from tests.catalogo_util import cabecera_cliente, entrar
from tests.compras_util import (
    MOTIVO_BANCO, MSG_RECHAZO, SIN_FONDOS, agregar_ok, checkout, checkout_ok, existencias, iniciar, pagar, stock_listo,
)


def test_01_proceder_al_pago_crea_el_pedido_con_el_carrito(inv, mundo, client):
    stock_listo(inv, mundo)
    agregar_ok(client, inv.h_cliente, inv.v_sm_rojo, inv.centro, 2)
    agregar_ok(client, inv.h_cliente, inv.var[("M", "Azul")])
    p = checkout_ok(client, inv.h_cliente)
    assert p["estado"] == "PENDIENTE_PAGO" and p["canal"] == "DIGITAL" and p["codigo"].startswith("PED-") and p["sucursal"] == "Centro"
    assert (p["subtotal"], p["total"], p["total_unidades"], p["comprobante_numero"]) == ("300.00", "300.00", 3, None)
    assert {(i["sku"], i["cantidad"], i["precio_final"]) for i in p["items"]} == {
        (inv.v_sm_rojo["sku"], 2, "100.00"), (inv.var[("M", "Azul")]["sku"], 1, "100.00")}
    assert client.get("/api/carrito", headers=inv.h_cliente).json()["total_unidades"] == 3  # el carrito sigue hasta que el pago se apruebe
    assert existencias(client, inv.h_enc_centro, inv.v_sm_rojo)["disponible"] == 10  # y el stock no se toca todavía


def test_02_datos_de_entrega_y_facturacion(inv, mundo, client):
    stock_listo(inv, mundo)
    agregar_ok(client, inv.h_cliente, inv.v_sm_rojo, inv.centro)
    r = checkout(client, inv.h_cliente, "DELIVERY", direccion_entrega="  ")
    assert r.status_code == 422 and r.json()["detail"] == "Ingrese la dirección de entrega."
    r = checkout(client, inv.h_cliente, "RETIRO", nit_ci="")
    assert r.status_code == 422 and r.json()["detail"] == "Ingrese su NIT o CI para la facturación."
    d = checkout_ok(client, inv.h_cliente, "DELIVERY", direccion_entrega="Calle 5 #20", nit_ci="7654321", razon_social="Mi Empresa SRL")
    assert (d["tipo_entrega"], d["direccion_entrega"], d["nit_ci"], d["razon_social"]) == ("DELIVERY", "Calle 5 #20", "7654321", "Mi Empresa SRL")
    r = checkout_ok(client, inv.h_cliente, "RETIRO", direccion_entrega="ignorada")
    assert r["direccion_entrega"] == "" and r["tipo_entrega"] == "RETIRO"  # el retiro es en la sucursal del carrito


def test_03_carrito_vacio(inv, client):
    r = checkout(client, inv.h_cliente)
    assert r.status_code == 422 and r.json()["detail"] == "Su carrito está vacío."


def test_04_pago_aprobado_genera_pedido_descuenta_stock_y_vacia_el_carrito(inv, mundo, client):
    stock_listo(inv, mundo)
    agregar_ok(client, inv.h_cliente, inv.v_sm_rojo, inv.centro, 3)
    p = checkout_ok(client, inv.h_cliente)
    r = pagar(client, inv.h_cliente, p["id"])
    assert r.status_code == 200
    res = r.json()
    assert res["aprobado"] is True and res["pedido"]["estado"] == "PAGADO" and res["pedido"]["pagado_en"]
    assert res["pedido"]["comprobante_numero"] == f"CMP-{inv.centro.id:03d}-000001"
    f = existencias(client, inv.h_enc_centro, inv.v_sm_rojo)
    assert (f["disponible"], f["vendida"]) == (7, 3)  # el stock sale de la sucursal elegida
    assert existencias(client, inv.h_enc_norte, inv.v_sm_rojo)["disponible"] == 10  # y de ninguna otra
    mov = next(m for m in client.get("/api/inventario/movimientos", params={"tipo": "VENTA"}, headers=inv.h_enc_centro).json()["items"])
    assert (mov["cantidad"], mov["referencia_tipo"], mov["referencia_id"], mov["usuario"], mov["nota"]) == (3, "PEDIDO", p["id"], "Cliente Prueba", f"Venta {p['codigo']}")
    assert client.get("/api/carrito", headers=inv.h_cliente).json()["items"] == []


def test_05_pago_rechazado_no_toca_stock_ni_carrito(inv, mundo, client):
    stock_listo(inv, mundo)
    agregar_ok(client, inv.h_cliente, inv.v_sm_rojo, inv.centro, 2)
    p = checkout_ok(client, inv.h_cliente)
    r = pagar(client, inv.h_cliente, p["id"], SIN_FONDOS)
    assert r.status_code == 402 and r.json()["detail"] == MSG_RECHAZO and r.json()["motivo"] == MOTIVO_BANCO
    f = existencias(client, inv.h_enc_centro, inv.v_sm_rojo)
    assert (f["disponible"], f["vendida"]) == (10, 0)
    assert client.get("/api/carrito", headers=inv.h_cliente).json()["total_unidades"] == 2
    assert client.get(f"/api/compras/{p['id']}", headers=inv.h_cliente).json()["estado"] == "PENDIENTE_PAGO"


def test_06_si_el_stock_cambia_antes_del_checkout_se_avisa(inv, mundo, client):
    stock_listo(inv, mundo)
    agregar_ok(client, inv.h_cliente, inv.v_sm_rojo, inv.centro, 5)
    client.post("/api/inventario/sucursal/movimientos", json={"variante_id": inv.v_sm_rojo["id"], "tipo": "AJUSTE_SALIDA", "cantidad": 8, "nota": "Merma"}, headers=inv.h_enc_centro)
    r = checkout(client, inv.h_cliente)
    assert r.status_code == 409 and "Hay prendas sin stock suficiente" in r.json()["detail"] and "en Centro hay 2 disponible(s)" in r.json()["detail"]
    assert client.get("/api/compras", headers=inv.h_cliente).json()["compras"] == []


def test_07_si_el_stock_cambia_entre_el_checkout_y_el_pago_no_se_cobra(inv, mundo, client):
    stock_listo(inv, mundo)
    agregar_ok(client, inv.h_cliente, inv.v_sm_rojo, inv.centro, 5)
    p = checkout_ok(client, inv.h_cliente)
    client.post("/api/inventario/sucursal/movimientos", json={"variante_id": inv.v_sm_rojo["id"], "tipo": "AJUSTE_SALIDA", "cantidad": 8, "nota": "Merma"}, headers=inv.h_enc_centro)
    r = iniciar(client, inv.h_cliente, p["id"])  # se avisa antes de pedir la tarjeta
    assert r.status_code == 409
    assert r.json()["detail"] == ("Algunas prendas se agotaron: Camisa Oxford (S, Rojo): quedan 2, necesita 5. "
                                  "No se realizó ningún cobro. Ajuste su carrito e intente de nuevo.")


def test_08_si_el_stock_se_agota_mientras_paga_se_anula_el_cobro(inv, mundo, client, db):
    stock_listo(inv, mundo)
    agregar_ok(client, inv.h_cliente, inv.v_sm_rojo, inv.centro, 5)
    p = checkout_ok(client, inv.h_cliente)
    pago_id = iniciar(client, inv.h_cliente, p["id"]).json()["pago_id"]  # el cliente está en el formulario de la tarjeta…
    client.post("/api/inventario/sucursal/movimientos", json={"variante_id": inv.v_sm_rojo["id"], "tipo": "AJUSTE_SALIDA", "cantidad": 8, "nota": "Merma"}, headers=inv.h_enc_centro)
    from tests.compras_util import tarjeta
    r = client.post(f"/api/pagos/{pago_id}/confirmar", json={"tarjeta": tarjeta()}, headers=inv.h_cliente)  # …y alguien compró lo mismo
    assert r.status_code == 409 and "se agotaron mientras pagaba" in r.json()["detail"] and "No se realizó ningún cobro" in r.json()["detail"]
    pago = client.get(f"/api/pagos/{pago_id}", headers=inv.h_cliente).json()
    assert pago["pago"]["estado"] == "CANCELADO" and pago["aprobado"] is False and pago["pedido"]["estado"] == "CANCELADO"
    assert pago["pedido"]["comprobante_numero"] is None
    f = existencias(client, inv.h_enc_centro, inv.v_sm_rojo)
    assert (f["disponible"], f["vendida"]) == (2, 0)  # no quedó ningún descuento a medias
    assert client.get("/api/carrito", headers=inv.h_cliente).json()["total_unidades"] == 5  # el carrito se conserva para corregirlo


def test_09_un_pedido_pagado_no_se_cobra_dos_veces(inv, mundo, client):
    stock_listo(inv, mundo)
    agregar_ok(client, inv.h_cliente, inv.v_sm_rojo, inv.centro, 2)
    p = checkout_ok(client, inv.h_cliente)
    pago_id = iniciar(client, inv.h_cliente, p["id"]).json()["pago_id"]
    from tests.compras_util import tarjeta
    for _ in range(2):  # confirmar dos veces (por ejemplo, doble clic)
        assert client.post(f"/api/pagos/{pago_id}/confirmar", json={"tarjeta": tarjeta()}, headers=inv.h_cliente).json()["aprobado"] is True
    assert existencias(client, inv.h_enc_centro, inv.v_sm_rojo)["vendida"] == 2
    r = iniciar(client, inv.h_cliente, p["id"])
    assert r.status_code == 409 and r.json()["detail"] == "El pedido no está pendiente de pago."


def test_10_un_nuevo_checkout_reemplaza_al_pedido_pendiente(inv, mundo, client):
    stock_listo(inv, mundo)
    agregar_ok(client, inv.h_cliente, inv.v_sm_rojo, inv.centro)
    viejo = checkout_ok(client, inv.h_cliente)
    pago_viejo = iniciar(client, inv.h_cliente, viejo["id"]).json()["pago_id"]
    nuevo = checkout_ok(client, inv.h_cliente)
    assert nuevo["id"] != viejo["id"]
    assert client.get(f"/api/pagos/{pago_viejo}", headers=inv.h_cliente).json()["pedido"]["estado"] == "CANCELADO"
    assert client.get(f"/api/pagos/{pago_viejo}", headers=inv.h_cliente).json()["pago"]["estado"] == "CANCELADO"


def test_11_la_sucursal_recibe_el_aviso_del_pedido(inv, mundo, client):
    stock_listo(inv, mundo)
    agregar_ok(client, inv.h_cliente, inv.v_sm_rojo, inv.centro, 2)
    p = checkout_ok(client, inv.h_cliente, "DELIVERY")
    pagar(client, inv.h_cliente, p["id"])
    aviso = next(n for n in client.get("/api/notificaciones", headers=inv.h_enc_centro).json() if n["tipo"] == "PEDIDO_NUEVO")
    assert p["codigo"] in aviso["titulo"] and "2 prenda(s)" in aviso["mensaje"] and "entrega a domicilio" in aviso["mensaje"]
    assert not any(n["tipo"] == "PEDIDO_NUEVO" for n in client.get("/api/notificaciones", headers=inv.h_enc_norte).json())


def test_12_aislamiento_entre_clientes_y_empresas(inv, mundo, tienda_b, datos, client):
    stock_listo(inv, mundo)
    agregar_ok(client, inv.h_cliente, inv.v_sm_rojo, inv.centro)
    p = checkout_ok(client, inv.h_cliente)
    datos.usuario(mundo.a, "Cliente", email="otro@a.com")
    for h in (entrar(client, mundo.a, "otro@a.com"), cabecera_cliente(datos, mundo.b)):
        assert iniciar(client, h, p["id"]).status_code == 404
    assert client.get(f"/api/compras/{p['id']}", headers=cabecera_cliente(datos, mundo.b)).status_code == 404


def test_13_solo_el_cliente_hace_checkout(inv, client):
    for h in (inv.h_enc_centro, inv.h_cajero, inv.h_admin):
        assert checkout(client, h).status_code == 403


def test_14_el_intento_rechazado_queda_registrado(inv, mundo, client, db):
    stock_listo(inv, mundo)
    agregar_ok(client, inv.h_cliente, inv.v_sm_rojo, inv.centro)
    p = checkout_ok(client, inv.h_cliente)
    pagar(client, inv.h_cliente, p["id"], SIN_FONDOS)
    pago = db.scalars(select(Pago).where(Pago.pedido_id == p["id"])).one()
    assert (pago.estado, pago.metodo, pago.proveedor, pago.tarjeta_ultimos4, pago.motivo, str(pago.monto)) == (
        "RECHAZADO", "TARJETA", "SIMULADO", "9995", MOTIVO_BANCO, "100.00")

"""Ayudas de las pruebas de la Fase D (carrito, compra digital, historial y pago)."""
VISA_OK = "4242 4242 4242 4242"
MASTERCARD_OK = "5555 5555 5555 4444"
SIN_FONDOS = "4000 0000 0000 9995"
RECHAZADA = "4000 0000 0000 0002"
VENCIDA = "4000 0000 0000 0069"
CVC_MALO = "4000 0000 0000 0127"
TIMEOUT = "4000 0000 0000 0119"
REAL_NO_DE_PRUEBA = "4111 1111 1111 1111"  # número válido (Luhn) que no es de prueba: jamás se procesa

MSG_RECHAZO = "La transacción no pudo ser procesada, verifique su método de pago o saldo disponible."
MOTIVO_BANCO = "Transacción denegada por su banco"


def stock_listo(inv, mundo, centro=10, norte=10):
    """Camisa Oxford (S y M × Rojo y Azul) con stock en Centro y Norte."""
    for v in inv.var.values():
        inv.stock(mundo.a.id, inv.centro.id, v["id"], centro)
        inv.stock(mundo.a.id, inv.norte.id, v["id"], norte)


def agregar(client, h, variante, sucursal=None, cantidad=1):
    cuerpo = {"variante_id": variante["id"], "cantidad": cantidad}
    if sucursal is not None:
        cuerpo["sucursal_id"] = sucursal.id
    return client.post("/api/carrito/items", json=cuerpo, headers=h)


def agregar_ok(client, h, variante, sucursal=None, cantidad=1):
    r = agregar(client, h, variante, sucursal, cantidad)
    assert r.status_code == 201, r.text
    return r.json()


def checkout(client, h, tipo="RETIRO", **extra):
    cuerpo = {"tipo_entrega": tipo, "nit_ci": "1234567", "razon_social": "Cliente Prueba", **extra}
    if tipo == "DELIVERY" and "direccion_entrega" not in extra:
        cuerpo["direccion_entrega"] = "Av. Banzer #123"
    return client.post("/api/compras/checkout", json=cuerpo, headers=h)


def checkout_ok(client, h, tipo="RETIRO", **extra):
    r = checkout(client, h, tipo, **extra)
    assert r.status_code == 201, r.text
    return r.json()


def tarjeta(numero=VISA_OK, mes=12, anio=2099, cvc="123", titular="Cliente Prueba"):
    return {"numero": numero, "mes": mes, "anio": anio, "cvc": cvc, "titular": titular}


def iniciar(client, h, pedido_id, guardada=None, guardar=False):
    return client.post(f"/api/pagos/pedidos/{pedido_id}/iniciar", json={"tarjeta_guardada_id": guardada, "guardar_tarjeta": guardar}, headers=h)


def pagar(client, h, pedido_id, numero=VISA_OK, guardar=False, **extra):
    """Inicia el pago y lo confirma con una tarjeta de prueba. Devuelve la respuesta de «confirmar»."""
    r = iniciar(client, h, pedido_id, guardar=guardar)
    assert r.status_code == 201, r.text
    return client.post(f"/api/pagos/{r.json()['pago_id']}/confirmar", json={"tarjeta": tarjeta(numero, **extra)}, headers=h)


def comprar(client, h, inv, variante=None, cantidad=1, numero=VISA_OK, sucursal=None):
    """Del carrito al pago aprobado. Devuelve el pedido ya pagado."""
    agregar_ok(client, h, variante or inv.v_sm_rojo, sucursal or inv.centro, cantidad)
    pedido = checkout_ok(client, h)
    r = pagar(client, h, pedido["id"], numero)
    assert r.status_code == 200 and r.json()["aprobado"], r.text
    return r.json()["pedido"]


def existencias(client, h_encargado, variante):
    r = client.get("/api/inventario/sucursal", params={"q": variante["sku"]}, headers=h_encargado).json()
    return next(x for x in r["items"] if x["sku"] == variante["sku"])

"""Ayudas de las pruebas de la Fase E (punto de venta)."""
from tests.compras_util import stock_listo  # noqa: F401  (se reutiliza: Camisa Oxford con stock en Centro y Norte)


def venta(client, h, *prendas, **extra):
    """prendas: pares (variante, cantidad). Devuelve la respuesta HTTP de «registrar venta presencial»."""
    cuerpo = {"items": [{"variante_id": v["id"], "cantidad": c} for v, c in prendas], **extra}
    return client.post("/api/caja/ventas", json=cuerpo, headers=h)


def venta_ok(client, h, *prendas, **extra):
    r = venta(client, h, *prendas, **extra)
    assert r.status_code == 201, r.text
    return r.json()


def cobrar(client, h, pedido_id, metodo="EFECTIVO", recibido=None):
    cuerpo = {"metodo": metodo}
    if recibido is not None:
        cuerpo["monto_recibido"] = str(recibido)
    return client.post(f"/api/caja/ventas/{pedido_id}/cobrar", json=cuerpo, headers=h)


def vender(client, h, *prendas, metodo="EFECTIVO", recibido=None, **extra):
    """Registra la venta y la cobra (por defecto en efectivo, con lo justo). Devuelve el resultado del cobro."""
    p = venta_ok(client, h, *prendas, **extra)
    r = cobrar(client, h, p["id"], metodo, recibido if recibido is not None else p["total"])
    assert r.status_code == 200, r.text
    return r.json()


def con_barras(client, inv, variante, codigo):
    r = client.put(f"/api/productos/{inv.camisa['id']}/variantes/{variante['id']}", json={"codigo_barras": codigo}, headers=inv.h_admin)
    assert r.status_code == 200, r.text
    return codigo

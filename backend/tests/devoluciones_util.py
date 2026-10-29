"""Ayudas de las pruebas de la Fase F (devoluciones y cambios)."""
from sqlalchemy import text

from tests.caja_util import cobrar, stock_listo, vender, venta_ok  # noqa: F401
from tests.compras_util import existencias, iniciar, tarjeta  # noqa: F401


def _cuerpo(comprobante, items, tipo, motivo, nuevos):
    """items: pares (línea del pedido, cantidad) con la línea tal como la devuelve la API (`pedido['items'][i]`)."""
    return {
        "comprobante": comprobante, "tipo": tipo, "motivo": motivo,
        "items": [{"pedido_item_id": i["id"], "cantidad": c} for i, c in (items or [])],
        "nuevos": [{"variante_id": v["id"], "cantidad": c} for v, c in (nuevos or [])],
    }


def devolver(client, h, comprobante, items=None, tipo="DEVOLUCION", motivo="Le quedó pequeña", nuevos=None, cobro=None):
    cuerpo = _cuerpo(comprobante, items, tipo, motivo, nuevos)
    if cobro:
        cuerpo["cobro"] = cobro
    return client.post("/api/devoluciones", json=cuerpo, headers=h)


def iniciar_diferencia(client, h, comprobante, items, nuevos, motivo="Quiero otra talla"):
    """Inicia el cobro con tarjeta de la diferencia de un cambio (el servidor calcula el monto)."""
    return client.post("/api/devoluciones/diferencia", json=_cuerpo(comprobante, items, "CAMBIO", motivo, nuevos), headers=h)


def devolver_ok(client, h, comprobante, items=None, **extra):
    r = devolver(client, h, comprobante, items, **extra)
    assert r.status_code == 201, r.text
    return r.json()


def venta_en_caja(client, inv, *prendas, metodo="EFECTIVO"):
    """Vende en caja y devuelve el pedido cobrado (con su comprobante y sus líneas)."""
    return vender(client, inv.h_cajero, *prendas, metodo=metodo)["pedido"]


def venta_con_tarjeta(client, inv, *prendas):
    p = venta_ok(client, inv.h_cajero, *prendas)
    pago_id = iniciar(client, inv.h_cajero, p["id"]).json()["pago_id"]
    r = client.post(f"/api/pagos/{pago_id}/confirmar", json={"tarjeta": tarjeta()}, headers=inv.h_cajero)
    assert r.status_code == 200 and r.json()["aprobado"], r.text
    return r.json()["pedido"]


def envejecer_venta(db, pedido_id, dias):
    """Retrasa la fecha de pago de una venta para probar el plazo de devolución."""
    db.execute(text("UPDATE pedidos SET pagado_en = pagado_en - make_interval(days => :d) WHERE id = :i"), {"d": dias, "i": pedido_id})
    db.commit()

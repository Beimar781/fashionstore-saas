"""Ayudas de las pruebas de reservas (Fase C)."""
from datetime import timedelta

from app.core.tiempo import a_local, ahora


def cuando(dias=1, hora=11):
    """Horario local (sin zona, como lo envía la web) a `dias` días de hoy."""
    d = (a_local(ahora()) + timedelta(days=dias)).replace(hour=hora, minute=0, second=0, microsecond=0)
    return d.replace(tzinfo=None).isoformat()


def fecha_local(dias=1):
    return (a_local(ahora()) + timedelta(days=dias)).date().isoformat()


def reservar(client, h, sucursal, *prendas, dias=1, hora=11, **extra):
    """prendas: pares (variante, cantidad). Devuelve la respuesta HTTP."""
    cuerpo = {"sucursal_id": sucursal.id, "programada_para": cuando(dias, hora),
              "items": [{"variante_id": v["id"], "cantidad": c} for v, c in prendas], **extra}
    return client.post("/api/reservas", json=cuerpo, headers=h)


def reserva_ok(client, h, sucursal, *prendas, **extra):
    r = reservar(client, h, sucursal, *prendas, **extra)
    assert r.status_code == 201, r.text
    return r.json()


def fila(client, h_encargado, variante):
    """Existencias de una variante en la sucursal del Encargado: disponible, reservada, vendida."""
    r = client.get("/api/inventario/sucursal", params={"q": variante["sku"]}, headers=h_encargado).json()
    return next(x for x in r["items"] if x["sku"] == variante["sku"])


def avisos(client, h):
    return client.get("/api/notificaciones", headers=h).json()


def vencer(db, reserva_id):
    """Envejece una reserva: su horario y su vigencia quedan en el pasado."""
    from app.modules.reservas.models import Reserva
    r = db.get(Reserva, reserva_id)
    r.programada_para = ahora() - timedelta(hours=30)
    r.vence_en = ahora() - timedelta(hours=1)
    db.commit()

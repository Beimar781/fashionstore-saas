"""Ayudas de las pruebas de la Fase H (operación offline y sincronización)."""
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from tests.compras_util import stock_listo  # noqa: F401
from tests.reservas_util import cuando


def ahora_iso(segundos: int = 0) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=segundos)).isoformat()


def op_venta(items, recibido, id_=None, segundos=0, **extra):
    """Venta de contado registrada sin conexión. items: pares (variante, cantidad)."""
    payload = {"items": [{"variante_id": v["id"], "cantidad": c} for v, c in items], "monto_recibido": str(recibido), **extra}
    return {"id": str(id_ or uuid.uuid4()), "tipo": "VENTA_CONTADO", "creada_en": ahora_iso(segundos), "payload": payload}


def op_reserva(sucursal, items, id_=None, dias=1, segundos=0, **extra):
    payload = {"sucursal_id": sucursal.id, "programada_para": cuando(dias), "items": [{"variante_id": v["id"], "cantidad": c} for v, c in items], **extra}
    return {"id": str(id_ or uuid.uuid4()), "tipo": "RESERVA", "creada_en": ahora_iso(segundos), "payload": payload, "sucursal_id": sucursal.id}


def sincronizar(client, h, *operaciones):
    return client.post("/api/offline/sincronizar", json={"operaciones": list(operaciones)}, headers=h)


def sincronizar_ok(client, h, *operaciones):
    r = sincronizar(client, h, *operaciones)
    assert r.status_code == 200, r.text
    return r.json()["resultados"]


def agregar_stock(db, variante, sucursal, cantidad):
    db.execute(text("UPDATE existencias SET disponible = disponible + :c WHERE variante_id = :v AND sucursal_id = :s"), {"c": cantidad, "v": variante["id"], "s": sucursal.id})
    db.commit()


def contar(db, tabla, **filtros):
    donde = " AND ".join(f"{k} = :{k}" for k in filtros) or "TRUE"
    return db.execute(text(f"SELECT count(*) FROM {tabla} WHERE {donde}"), filtros).scalar()

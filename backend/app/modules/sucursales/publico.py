"""Interfaz pública del paquete P3 para otros paquetes (evita acoplarse a sus repositorios)."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.sucursales.models import Ciudad, Sucursal


def contar_sucursales_activas(db: Session, empresa_id: int) -> int:
    return db.scalar(
        select(func.count()).select_from(Sucursal).where(Sucursal.empresa_id == empresa_id, Sucursal.activa.is_(True))
    ) or 0


def sucursal_de_empresa(db: Session, empresa_id: int, sucursal_id: int) -> bool:
    """¿La sucursal existe y pertenece a la empresa? (un id de otra empresa cuenta como inexistente)."""
    return db.scalar(select(Sucursal.id).where(Sucursal.empresa_id == empresa_id, Sucursal.id == sucursal_id)) is not None


def sucursales_activas(db: Session, empresa_id: int) -> list[dict]:
    """Sucursales activas de la empresa con los datos que ve un cliente (para elegir dónde consultar disponibilidad)."""
    filas = db.execute(
        select(Sucursal.id, Sucursal.nombre, Ciudad.nombre, Sucursal.direccion, Sucursal.horario)
        .join(Ciudad, Ciudad.id == Sucursal.ciudad_id)
        .where(Sucursal.empresa_id == empresa_id, Sucursal.activa.is_(True))
        .order_by(Ciudad.nombre, Sucursal.nombre)
    )
    return [{"id": i, "nombre": n, "ciudad": c, "direccion": d, "horario": h} for i, n, c, d, h in filas]


def sucursal_activa_de_empresa(db: Session, empresa_id: int, sucursal_id: int) -> bool:
    return db.scalar(
        select(Sucursal.id).where(Sucursal.empresa_id == empresa_id, Sucursal.id == sucursal_id, Sucursal.activa.is_(True))
    ) is not None


def nombres_de_sucursales(db: Session, empresa_id: int) -> dict[int, str]:
    return {i: n for i, n in db.execute(select(Sucursal.id, Sucursal.nombre).where(Sucursal.empresa_id == empresa_id))}


def datos_de_sucursal_activa(db: Session, empresa_id: int, sucursal_id: int) -> dict | None:
    """Nombre y horario de una sucursal activa de la empresa; None si no existe, está inactiva o es de otra empresa."""
    fila = db.execute(
        select(Sucursal.id, Sucursal.nombre, Sucursal.horario)
        .where(Sucursal.empresa_id == empresa_id, Sucursal.id == sucursal_id, Sucursal.activa.is_(True))
    ).first()
    return None if fila is None else {"id": fila[0], "nombre": fila[1], "horario": fila[2]}


# Verificadores de «trabajo pendiente» de una sucursal. Cada paquete que deja cosas por resolver en una sucursal (reservas, operaciones
# sin sincronizar) registra el suyo al cargarse; así `sucursales` no depende de ellos y no hay ciclos entre paquetes.
_VERIFICADORES_PENDIENTES: list = []


def registrar_verificador_de_pendientes(verificador) -> None:
    """`verificador(db, empresa_id, sucursal_id) -> bool`: ¿la sucursal tiene algo pendiente que impida desactivarla?"""
    _VERIFICADORES_PENDIENTES.append(verificador)


def tiene_pendientes(db: Session, empresa_id: int, sucursal_id: int) -> bool:
    return any(verificador(db, empresa_id, sucursal_id) for verificador in _VERIFICADORES_PENDIENTES)


def datos_de_sucursal(db: Session, empresa_id: int, sucursal_id: int) -> dict:
    """Nombre, dirección y teléfono de una sucursal (aunque ya esté inactiva), para documentos impresos."""
    fila = db.execute(
        select(Sucursal.nombre, Sucursal.direccion, Sucursal.telefono, Ciudad.nombre)
        .join(Ciudad, Ciudad.id == Sucursal.ciudad_id)
        .where(Sucursal.empresa_id == empresa_id, Sucursal.id == sucursal_id)
    ).first()
    return {"nombre": fila[0], "direccion": fila[1] or "", "telefono": fila[2] or "", "ciudad": fila[3]} if fila else {}

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

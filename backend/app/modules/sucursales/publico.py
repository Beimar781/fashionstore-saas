"""Interfaz pública del paquete P3 para otros paquetes (evita acoplarse a sus repositorios)."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.sucursales.models import Sucursal


def contar_sucursales_activas(db: Session, empresa_id: int) -> int:
    return db.scalar(
        select(func.count()).select_from(Sucursal).where(Sucursal.empresa_id == empresa_id, Sucursal.activa.is_(True))
    ) or 0

"""Fechas y horas: la base guarda instantes con zona; las tiendas piensan en hora local."""
from datetime import datetime, timedelta, timezone

from app.core.config import get_settings


def zona_local() -> timezone:
    return timezone(timedelta(hours=get_settings().zona_horaria_horas))


def ahora() -> datetime:
    return datetime.now(timezone.utc)


def a_local(momento: datetime) -> datetime:
    """Hora de la tienda; un valor sin zona (por ejemplo del campo datetime-local de la web) ya se toma como hora local."""
    return momento.replace(tzinfo=zona_local()) if momento.tzinfo is None else momento.astimezone(zona_local())

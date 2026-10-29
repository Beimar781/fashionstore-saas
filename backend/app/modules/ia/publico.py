"""Interfaz pública del paquete P9 ia para otros paquetes (el asistente del primer parcial registra su uso aquí)."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.tiempo import ahora
from app.modules.ia.models import UsoIA


def registrar_uso_ia(db: Session, empresa_id: int, usuario_id: int | None, funcion: str, origen: str) -> None:
    """Anota una consulta a la IA (sin commit: lo hace el caso de uso que la llama)."""
    db.add(UsoIA(empresa_id=empresa_id, usuario_id=usuario_id, funcion=funcion, origen=origen))


def consultas_ia_del_mes(db: Session, empresa_id: int) -> int:
    inicio = ahora().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return db.scalar(select(func.count(UsoIA.id)).where(UsoIA.empresa_id == empresa_id, UsoIA.creado_en >= inicio)) or 0


from app.modules.plataforma.publico import registrar_medidor  # noqa: E402

registrar_medidor("consultas_ia", "Consultas de IA del mes", consultas_ia_del_mes)

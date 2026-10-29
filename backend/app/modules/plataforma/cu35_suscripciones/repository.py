from datetime import date

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.constantes import SUS_ACTIVA, SUS_VENCIDA
from app.modules.plataforma.models import Plan, Suscripcion


class SuscripcionRepository:
    """Las suscripciones las administra la plataforma (SuperAdministrador): se consultan siempre
    con un `empresa_id` explícito. Son datos de la plataforma, no del tenant."""

    def __init__(self, db: Session):
        self.db = db

    def agregar(self, sus: Suscripcion) -> Suscripcion:
        self.db.add(sus)
        self.db.flush()
        return sus

    def vigente(self, empresa_id: int) -> Suscripcion | None:
        return self.db.scalar(
            select(Suscripcion).where(Suscripcion.empresa_id == empresa_id, Suscripcion.estado == SUS_ACTIVA)
        )

    def ultima(self, empresa_id: int) -> Suscripcion | None:
        """La vigente si existe; si no, la más reciente (Vencida, Suspendida o Cancelada)."""
        return self.db.scalar(
            select(Suscripcion)
            .where(Suscripcion.empresa_id == empresa_id)
            .order_by((Suscripcion.estado == SUS_ACTIVA).desc(), Suscripcion.id.desc())
            .limit(1)
        )

    def uso_su_prueba(self, empresa_id: int) -> bool:
        """¿La empresa ya tuvo, en algún momento, una suscripción de prueba gratuita?"""
        return self.db.scalar(
            select(Suscripcion.id).join(Plan, Plan.id == Suscripcion.plan_id).where(Suscripcion.empresa_id == empresa_id, Plan.es_prueba.is_(True)).limit(1)
        ) is not None

    def historial(self, empresa_id: int) -> list[Suscripcion]:
        return list(
            self.db.scalars(
                select(Suscripcion).where(Suscripcion.empresa_id == empresa_id).order_by(Suscripcion.id.desc())
            )
        )

    def marcar_vencidas(self, empresa_id: int | None = None) -> int:
        """RN05: toda suscripción Activa cuya fecha de vencimiento ya pasó queda Vencida."""
        stmt = (
            update(Suscripcion)
            .where(Suscripcion.estado == SUS_ACTIVA, Suscripcion.fecha_vencimiento < date.today())
            .values(estado=SUS_VENCIDA)
        )
        if empresa_id is not None:
            stmt = stmt.where(Suscripcion.empresa_id == empresa_id)
        return self.db.execute(stmt).rowcount

    def cerrar(self, sus: Suscripcion, estado: str) -> None:
        sus.estado = estado
        self.db.flush()

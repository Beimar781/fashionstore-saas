from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.modules.acceso.models import RestablecimientoPassword, Usuario


class AutenticacionRepository:
    """Consultas previas a conocer el tenant: la empresa se resuelve por su código (RN09)."""

    def __init__(self, db: Session):
        self.db = db

    def usuario_de_empresa(self, empresa_id: int, email: str) -> Usuario | None:
        return self.db.scalar(
            select(Usuario).where(Usuario.empresa_id == empresa_id, func.lower(Usuario.email) == email.lower())
        )

    def usuario_de_plataforma(self, email: str) -> Usuario | None:
        return self.db.scalar(
            select(Usuario).where(Usuario.empresa_id.is_(None), func.lower(Usuario.email) == email.lower())
        )

    # --- recuperación de contraseña ---
    def invalidar_pendientes(self, usuario_id: int) -> None:
        self.db.execute(
            update(RestablecimientoPassword)
            .where(RestablecimientoPassword.usuario_id == usuario_id, RestablecimientoPassword.usado.is_(False))
            .values(usado=True)
        )

    def crear_restablecimiento(self, usuario_id: int, token_hash: str, expira_en: datetime) -> None:
        self.db.add(RestablecimientoPassword(usuario_id=usuario_id, token_hash=token_hash, expira_en=expira_en))

    def restablecimiento_vigente(self, token_hash: str, ahora: datetime) -> RestablecimientoPassword | None:
        return self.db.scalar(
            select(RestablecimientoPassword).where(
                RestablecimientoPassword.token_hash == token_hash,
                RestablecimientoPassword.usado.is_(False),
                RestablecimientoPassword.expira_en > ahora,
            )
        )

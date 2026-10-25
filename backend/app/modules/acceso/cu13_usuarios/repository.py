from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.constantes import ADMIN, ROLES_INTERNOS
from app.core.tenant import TenantRepository
from app.modules.acceso.models import Rol, Usuario


class RolRepository:
    def __init__(self, db: Session):
        self.db = db

    def por_nombre(self, nombre: str) -> Rol | None:
        return self.db.scalar(select(Rol).where(Rol.nombre == nombre))


class UsuarioRepository(TenantRepository[Usuario]):
    """Usuarios de UNA empresa. El filtro empresa_id lo aplica TenantRepository (RN02)."""

    model = Usuario

    def listar_internos(self) -> list[Usuario]:
        stmt = (
            self._consulta()
            .join(Rol, Usuario.rol_id == Rol.id)
            .where(Rol.nombre.in_(ROLES_INTERNOS))
            .order_by(Usuario.id)
        )
        return list(self.db.scalars(stmt))

    def obtener_interno(self, usuario_id: int) -> Usuario | None:
        stmt = self._consulta().join(Rol, Usuario.rol_id == Rol.id).where(
            Usuario.id == usuario_id, Rol.nombre.in_(ROLES_INTERNOS)
        )
        return self.db.scalar(stmt)

    def existe_email(self, email: str, excluir_id: int | None = None) -> bool:
        stmt = self._consulta().where(func.lower(Usuario.email) == email.lower())
        if excluir_id is not None:
            stmt = stmt.where(Usuario.id != excluir_id)
        return self.db.scalar(stmt.limit(1)) is not None

    def contar_administradores_activos(self) -> int:
        stmt = (
            select(func.count())
            .select_from(Usuario)
            .join(Rol, Usuario.rol_id == Rol.id)
            .where(Usuario.empresa_id == self.empresa_id, Rol.nombre == ADMIN, Usuario.activo.is_(True))
        )
        return self.db.scalar(stmt) or 0

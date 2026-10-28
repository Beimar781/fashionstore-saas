"""Interfaz pública del paquete P2 acceso para otros paquetes."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.constantes import PROVEEDOR
from app.core.errors import Conflicto
from app.core.security import hash_password
from app.modules.acceso.cu13_usuarios.repository import RolRepository, UsuarioRepository
from app.modules.acceso.cu13_usuarios.schemas import validar_password  # noqa: F401
from app.modules.acceso.models import Usuario


def crear_usuario_proveedor(db: Session, empresa_id: int, nombre: str, email: str, password: str) -> int:
    """Cuenta del portal de un proveedor (rol Proveedor) dentro de la empresa. No hace commit: lo hace quien la llama."""
    usuarios = UsuarioRepository(db, empresa_id)
    email = email.strip().lower()
    if usuarios.existe_email(email):
        raise Conflicto("Este correo ya está en uso.")  # RN09: único dentro de la empresa
    usuario = usuarios.agregar(Usuario(
        rol_id=RolRepository(db).por_nombre(PROVEEDOR).id, nombre=nombre.strip(), apellidos="", email=email,
        password_hash=hash_password(password), activo=True,
    ))
    return usuario.id


def nombres_de_usuarios(db: Session, empresa_id: int, ids: set[int]) -> dict[int, str]:
    if not ids:
        return {}
    filas = db.execute(select(Usuario.id, Usuario.nombre, Usuario.apellidos).where(Usuario.empresa_id == empresa_id, Usuario.id.in_(ids)))
    return {i: f"{n} {a}".strip() for i, n, a in filas}

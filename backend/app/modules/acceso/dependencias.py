"""Autenticación y autorización por rol (RNF01). Las peticiones se resuelven siempre contra
la base: si el usuario fue desactivado, su token deja de servir de inmediato."""
from dataclasses import dataclass

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import NoAutenticado, Prohibido
from app.core.security import decodificar_token
from app.modules.acceso.models import Usuario

_bearer = HTTPBearer(auto_error=False)


@dataclass
class Contexto:
    """Contexto del usuario autenticado: de aquí sale el tenant de TODA operación."""

    usuario: Usuario
    rol: str
    empresa_id: int | None
    sucursal_id: int | None


def get_contexto(
    cred: HTTPAuthorizationCredentials | None = Depends(_bearer), db: Session = Depends(get_db)
) -> Contexto:
    if cred is None:
        raise NoAutenticado("Debe iniciar sesión.")
    claims = decodificar_token(cred.credentials, "access")
    usuario = db.get(Usuario, int(claims["sub"]))
    if usuario is None or not usuario.activo:
        raise NoAutenticado("Sesión inválida o vencida. Inicie sesión nuevamente.")
    return Contexto(usuario, usuario.rol.nombre, usuario.empresa_id, usuario.sucursal_id)


def requerir_roles(*roles: str):
    def _dep(ctx: Contexto = Depends(get_contexto)) -> Contexto:
        if ctx.rol not in roles:
            raise Prohibido("No tiene permisos para esta operación.")
        return ctx

    return _dep

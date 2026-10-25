"""Hash de contraseñas (Argon2) y tokens JWT con contexto de empresa (RNF01, RNF02)."""
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.core.config import get_settings
from app.core.errors import NoAutenticado

_hasher = PasswordHasher()
_HASH_FALSO = _hasher.hash("contraseña-inexistente")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str | None, password: str) -> bool:
    """Si no hay usuario se verifica contra un hash falso para igualar tiempos de respuesta."""
    try:
        return _hasher.verify(password_hash or _HASH_FALSO, password) and password_hash is not None
    except (VerificationError, InvalidHashError):
        return False


def crear_token(claims: dict, tipo: str) -> str:
    cfg = get_settings()
    ahora = datetime.now(timezone.utc)
    vida = timedelta(minutes=cfg.access_token_minutes) if tipo == "access" else timedelta(days=cfg.refresh_token_days)
    payload = {**claims, "type": tipo, "iat": ahora, "exp": ahora + vida}
    return jwt.encode(payload, cfg.secret_key, algorithm=cfg.jwt_algorithm)


def decodificar_token(token: str, tipo: str) -> dict:
    cfg = get_settings()
    try:
        payload = jwt.decode(token, cfg.secret_key, algorithms=[cfg.jwt_algorithm])
    except jwt.PyJWTError:
        raise NoAutenticado("Sesión inválida o vencida. Inicie sesión nuevamente.")
    if payload.get("type") != tipo:
        raise NoAutenticado("Sesión inválida o vencida. Inicie sesión nuevamente.")
    return payload

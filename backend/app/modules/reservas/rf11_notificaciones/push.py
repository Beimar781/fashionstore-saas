"""RF11 · Avisos push (regla 17): servicio reutilizable para avisarle algo importante a un usuario en su navegador (Web Push) o en su móvil (FCM).

Dos canales con sus adaptadores (regla 12):
- WEB: Web Push con claves VAPID (`pywebpush`). Sin claves en el `.env` queda en modo simulado: el aviso sigue en la campana del usuario.
- MOVIL: Firebase Cloud Messaging con la cuenta de servicio del `.env`. Sin credenciales, modo simulado: el backend deja el aviso pendiente en la campana y la app lo muestra
  como notificación local al abrirse o al sincronizar.
Un fallo del push NUNCA deshace la operación que lo originó: se registra el error en `push_envios` y nada más.
"""
import json
import logging
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import DatosInvalidos
from app.modules.reservas.models import Dispositivo, PushEnvio
from app.modules.reservas.rf11_notificaciones.repository import DispositivoRepository, PushEnvioRepository
from app.modules.reservas.rf11_notificaciones.service import notificar

logger = logging.getLogger(__name__)
MSG_SUSCRIPCION = "La suscripción del navegador no es válida."
MSG_DISPOSITIVO = "El identificador del dispositivo no es válido."


class DispositivoCaducado(Exception):
    """El navegador o el móvil ya no acepta avisos (se desinstaló o revocó el permiso): hay que dejar de intentarlo."""


@dataclass
class Mensaje:
    titulo: str
    cuerpo: str
    datos: dict = field(default_factory=dict)


# ---------------- adaptadores ----------------
def _enviar_webpush(**kw) -> None:
    from pywebpush import WebPushException, webpush

    try:
        webpush(**kw)
    except WebPushException as e:
        if e.response is not None and e.response.status_code in (404, 410):
            raise DispositivoCaducado() from e
        raise


class AdaptadorWebPush:
    """Web Push con VAPID. La PWA usa el service worker de Angular, que muestra la notificación que viaja en `notification`."""

    def __init__(self, clave_privada: str, subject: str, enviar=None):
        self.clave_privada, self.subject, self._enviar = clave_privada, subject, enviar or _enviar_webpush

    def enviar(self, token: str, m: Mensaje) -> None:
        carga = {"notification": {"title": m.titulo, "body": m.cuerpo, "icon": "icons/icon-192.png", "data": m.datos}}
        self._enviar(subscription_info=json.loads(token), data=json.dumps(carga), vapid_private_key=self.clave_privada, vapid_claims={"sub": self.subject})


class AdaptadorFCM:
    """Firebase Cloud Messaging (API HTTP v1) con la cuenta de servicio del `.env`."""

    ALCANCE = "https://www.googleapis.com/auth/firebase.messaging"

    def __init__(self, credenciales: str, proyecto: str, enviar=None):
        self.credenciales, self.proyecto, self._enviar = credenciales, proyecto, enviar or self._post

    def _token_de_acceso(self) -> str:
        from google.auth.transport.requests import Request
        from google.oauth2 import service_account

        c = service_account.Credentials.from_service_account_file(self.credenciales, scopes=[self.ALCANCE])
        c.refresh(Request())
        return c.token

    def _post(self, url: str, cuerpo: dict):
        import requests

        return requests.post(url, json=cuerpo, headers={"Authorization": f"Bearer {self._token_de_acceso()}"}, timeout=10)

    def enviar(self, token: str, m: Mensaje) -> None:
        r = self._enviar(
            f"https://fcm.googleapis.com/v1/projects/{self.proyecto}/messages:send",
            {"message": {"token": token, "notification": {"title": m.titulo, "body": m.cuerpo}, "data": {k: str(v) for k, v in m.datos.items()}}},
        )
        if r.status_code in (404, 410):
            raise DispositivoCaducado()
        if r.status_code >= 300:
            raise RuntimeError(f"FCM respondió {r.status_code}")


def adaptadores_por_defecto() -> tuple[AdaptadorWebPush | None, AdaptadorFCM | None]:
    """Los adaptadores reales según el `.env`; None = modo simulado (sin claves)."""
    cfg = get_settings()
    web = AdaptadorWebPush(cfg.vapid_private_key, cfg.vapid_subject) if cfg.vapid_activo else None
    movil = AdaptadorFCM(cfg.fcm_credenciales, cfg.fcm_proyecto) if cfg.fcm_activo else None
    return web, movil


# ---------------- servicio ----------------
class ServicioPush:
    def __init__(self, db: Session, web=None, movil=None):
        """Sin adaptadores indicados se usan los del `.env`; en las pruebas se inyectan dobles en memoria."""
        self.db = db
        por_defecto = adaptadores_por_defecto() if web is None and movil is None else (None, None)
        self.web, self.movil = web or por_defecto[0], movil or por_defecto[1]

    def enviar(self, empresa_id: int, usuario_id: int, m: Mensaje) -> list[str]:
        """Intenta el aviso en cada dispositivo activo del usuario y anota el resultado. No lanza nunca: devuelve el estado de cada intento."""
        estados: list[str] = []
        try:
            envios = PushEnvioRepository(self.db, empresa_id)
            for d in DispositivoRepository(self.db, empresa_id).activos_de(usuario_id):
                adaptador = self.web if d.canal == "WEB" else self.movil
                estado, error = "SIMULADO", None
                if adaptador is not None:
                    try:
                        adaptador.enviar(d.token, m)
                        estado = "ENVIADO"
                    except DispositivoCaducado:
                        d.activo, estado, error = False, "FALLIDO", "El dispositivo ya no acepta avisos."
                    except Exception as e:  # noqa: BLE001  un fallo del servicio de push no deshace nada
                        estado, error = "FALLIDO", str(e)[:300] or e.__class__.__name__
                        logger.warning("Push fallido (%s, usuario %s): %s", d.canal, usuario_id, error)
                envios.agregar(PushEnvio(usuario_id=usuario_id, dispositivo_id=d.id, canal=d.canal, estado=estado, titulo=m.titulo[:200], error=error))
                estados.append(estado)
            self.db.commit()
        except Exception:  # noqa: BLE001
            logger.exception("No se pudo enviar el push al usuario %s", usuario_id)
            self.db.rollback()
        return estados


def enviar_push(db: Session, empresa_id: int, usuario_id: int, titulo: str, cuerpo: str, datos: dict | None = None) -> list[str]:
    """Push a los dispositivos activos del usuario (sin dejar aviso en la campana)."""
    return ServicioPush(db).enviar(empresa_id, usuario_id, Mensaje(titulo, cuerpo, datos or {}))


def avisar_cliente(
    db: Session, empresa_id: int, usuario_id: int | None, tipo: str, titulo: str, mensaje: str, referencia_tipo: str = "", referencia_id: int | None = None,
) -> None:
    """Aviso importante: la campana (RF11) y el push. Va DESPUÉS de confirmar la operación y nunca la deshace: si algo falla, solo se anota."""
    if usuario_id is None:  # venta de mostrador sin cuenta de cliente: no hay a quién avisar
        return
    try:
        notificar(db, empresa_id, tipo, titulo, mensaje, usuario_id=usuario_id, referencia_tipo=referencia_tipo, referencia_id=referencia_id)
        db.commit()
    except Exception:  # noqa: BLE001
        db.rollback()
        logger.exception("No se pudo dejar el aviso en la campana del usuario %s", usuario_id)
    enviar_push(db, empresa_id, usuario_id, titulo, mensaje, {"tipo": tipo, "referencia_tipo": referencia_tipo, "referencia_id": referencia_id or ""})


# ---------------- dispositivos del usuario ----------------
def validar_token(canal: str, token: str) -> str:
    token = token.strip()
    if canal == "WEB":
        try:
            s = json.loads(token)
            if not (isinstance(s, dict) and str(s.get("endpoint", "")).startswith("https://") and isinstance(s.get("keys"), dict) and s["keys"].get("p256dh") and s["keys"].get("auth")):
                raise ValueError
        except ValueError:
            raise DatosInvalidos(MSG_SUSCRIPCION) from None
    elif not 1 <= len(token) <= 4000:
        raise DatosInvalidos(MSG_DISPOSITIVO)
    return token


def registrar_dispositivo(db: Session, empresa_id: int, usuario_id: int, canal: str, token: str) -> Dispositivo:
    """Un mismo dispositivo no se duplica: si ya estaba (aunque inactivo), se reactiva."""
    token = validar_token(canal, token)
    repo = DispositivoRepository(db, empresa_id)
    d = repo.por_token(usuario_id, canal, token) or repo.agregar(Dispositivo(usuario_id=usuario_id, canal=canal, token=token))
    d.activo = True
    db.commit()
    return d


def quitar_dispositivo(db: Session, empresa_id: int, usuario_id: int, canal: str, token: str) -> bool:
    d = DispositivoRepository(db, empresa_id).por_token(usuario_id, canal, token.strip())
    if d is None or not d.activo:
        return False
    d.activo = False
    db.commit()
    return True

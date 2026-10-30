"""Envío de correos transaccionales. Producción: API de Brevo. Desarrollo (sin BREVO_API_KEY): se imprime en consola."""
import logging

import httpx

from app.core.config import get_settings
from app.core.errors import AppError

log = logging.getLogger("fashionstore.correo")
URL_BREVO = "https://api.brevo.com/v3/smtp/email"
MSG_CORREO = "No se pudo enviar el correo. Intente nuevamente en unos minutos o avise al administrador."


class ErrorCorreo(AppError):
    """Brevo rechazó el envío o no respondió. `detalle` explica la causa para quien opera el sistema (no se muestra al usuario final)."""

    status_code = 502

    def __init__(self, detalle: str):
        super().__init__(MSG_CORREO)
        self.detalle = detalle


def explicar_error_brevo(estado: int, cuerpo: str) -> str:
    """Traduce lo que respondió Brevo a una causa legible, con el paso que corrige los casos más comunes."""
    texto = cuerpo.lower()
    if estado in (401, 403) and ("ip" in texto or "unrecognised" in texto):
        return f"Brevo rechazó la IP del servidor ({estado}). En Brevo → Seguridad → Direcciones IP autorizadas, desactive la restricción o agregue la IP del backend. Respuesta: {cuerpo}"
    if estado in (401, 403):
        return f"Brevo no aceptó la clave de API ({estado}). Revise BREVO_API_KEY (debe ser una clave de API v3, no una clave SMTP). Respuesta: {cuerpo}"
    if "sender" in texto or "remitente" in texto:
        return f"El remitente no está verificado en Brevo ({estado}). Verifique BREVO_SENDER_EMAIL en Brevo → Remitentes y dominios, y use exactamente ese correo. Respuesta: {cuerpo}"
    return f"Brevo respondió {estado}: {cuerpo}"


def enviar_correo(destino: str, asunto: str, html: str, texto_consola: str = "") -> None:
    """Envía el correo. Sin BREVO_API_KEY lo imprime en consola. Si Brevo lo rechaza, lo registra y lanza ErrorCorreo (502)."""
    cfg = get_settings()
    if not cfg.brevo_api_key:
        print(f"\n[CORREO · modo desarrollo] Para: {destino} | {asunto}\n{texto_consola}\n", flush=True)
        return
    try:
        r = httpx.post(
            URL_BREVO,
            headers={"api-key": cfg.brevo_api_key, "accept": "application/json"},
            json={
                "sender": {"name": cfg.brevo_sender_name, "email": cfg.brevo_sender_email},
                "to": [{"email": destino}],
                "subject": asunto,
                "htmlContent": html,
            },
            timeout=10,
        )
    except httpx.HTTPError as e:
        log.error("No se pudo contactar a Brevo para enviar el correo a %s: %s", destino, e)
        raise ErrorCorreo(f"No se pudo contactar a Brevo: {e.__class__.__name__}") from e
    if r.status_code >= 300:
        detalle = explicar_error_brevo(r.status_code, r.text[:500])
        log.error("Brevo rechazó el correo a %s: %s", destino, detalle)
        raise ErrorCorreo(detalle)

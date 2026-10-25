"""Envío de correos transaccionales. Producción: API de Brevo. Desarrollo (sin BREVO_API_KEY): se imprime en consola."""
import logging

import httpx

from app.core.config import get_settings

log = logging.getLogger("fashionstore.correo")


def enviar_correo(destino: str, asunto: str, html: str, texto_consola: str = "") -> None:
    cfg = get_settings()
    if not cfg.brevo_api_key:
        print(f"\n[CORREO · modo desarrollo] Para: {destino} | {asunto}\n{texto_consola}\n", flush=True)
        return
    try:
        r = httpx.post(
            "https://api.brevo.com/v3/smtp/email",
            headers={"api-key": cfg.brevo_api_key, "accept": "application/json"},
            json={
                "sender": {"name": cfg.brevo_sender_name, "email": cfg.brevo_sender_email},
                "to": [{"email": destino}],
                "subject": asunto,
                "htmlContent": html,
            },
            timeout=10,
        )
        r.raise_for_status()
    except httpx.HTTPError:  # no se revela al usuario si el correo existe; se registra para el operador
        log.exception("No se pudo enviar el correo a %s", destino)

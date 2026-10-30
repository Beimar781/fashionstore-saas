"""Envía un correo de prueba por Brevo para comprobar BREVO_API_KEY y el remitente verificado, e imprime la causa legible si Brevo lo rechaza.

Uso (desde la carpeta backend, con las variables del .env o las de Railway):  python scripts/probar_correo.py destino@correo.com
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import get_settings  # noqa: E402
from app.core.correo import ErrorCorreo, enviar_correo  # noqa: E402


def main() -> int:
    if len(sys.argv) != 2 or "@" not in sys.argv[1]:
        print("Uso: python scripts/probar_correo.py destino@correo.com")
        return 2
    cfg = get_settings()
    if not cfg.brevo_api_key:
        print("Falta BREVO_API_KEY: sin ella el correo solo se imprime en la consola (modo desarrollo). Defínala en backend/.env o en las variables del servicio.")
        return 1
    print(f"Remitente: {cfg.brevo_sender_name} <{cfg.brevo_sender_email}>")
    try:
        enviar_correo(sys.argv[1], "Prueba de correo · FashionStore", "<p>Si usted lee esto, el correo de FashionStore funciona.</p>")
    except ErrorCorreo as e:
        print(f"ERROR: {e.detalle}")
        return 1
    print(f"Correo de prueba enviado a {sys.argv[1]}. Revise también la carpeta de spam.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

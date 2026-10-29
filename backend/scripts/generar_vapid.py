"""Genera las claves VAPID del Web Push y las agrega a backend/.env (la clave privada no se imprime). Uso: python scripts/generar_vapid.py"""
import base64
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from py_vapid import Vapid


def b64url(datos: bytes) -> str:
    return base64.urlsafe_b64encode(datos).decode().rstrip("=")


def main() -> None:
    env = Path(__file__).resolve().parent.parent / ".env"
    texto = env.read_text(encoding="utf-8") if env.exists() else ""
    if "VAPID_PRIVATE_KEY=" in texto and any(l.startswith("VAPID_PRIVATE_KEY=") and l.split("=", 1)[1].strip() for l in texto.splitlines()):
        print("El .env ya tiene claves VAPID; no se cambian (cambiarlas deja sin avisos a los navegadores ya suscritos).")
        return
    v = Vapid()
    v.generate_keys()
    privada = b64url(v.private_key.private_numbers().private_value.to_bytes(32, "big"))
    publica = b64url(v.public_key.public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint))
    lineas = [l for l in texto.splitlines() if not l.startswith(("VAPID_PUBLIC_KEY=", "VAPID_PRIVATE_KEY="))]
    lineas += [f"VAPID_PUBLIC_KEY={publica}", f"VAPID_PRIVATE_KEY={privada}"]
    env.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print(f"Claves VAPID agregadas a {env}. Reinicie el backend. La clave pública es la que usa el navegador para suscribirse.")


if __name__ == "__main__":
    main()

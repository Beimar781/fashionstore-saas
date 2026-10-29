"""Adaptador de la IA externa (regla 12). Claude se consume por API con la clave del `.env`; sin clave, o si la API falla,
`json_estructurado` devuelve None y cada caso de uso responde con su modo de respaldo (reglas locales)."""
import json
import logging

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)
URL_MENSAJES = "https://api.anthropic.com/v1/messages"


class ClienteIA:
    def __init__(self, clave: str, modelo: str, http=None):
        self.clave = clave
        self.modelo = modelo
        self.http = http or httpx.post  # en las pruebas se reemplaza por un doble en memoria

    @property
    def activo(self) -> bool:
        return bool(self.clave)

    def json_estructurado(self, sistema: str, usuario: str) -> dict | None:
        """Pide a la IA una respuesta JSON. None si no hay clave, si la API no responde o si lo devuelto no es un objeto JSON."""
        if not self.activo:
            return None
        try:
            r = self.http(
                URL_MENSAJES, timeout=20,
                headers={"x-api-key": self.clave, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                json={"model": self.modelo, "max_tokens": 600, "system": sistema, "messages": [{"role": "user", "content": usuario}]},
            )
            if r.status_code != 200:
                return None
            texto = "".join(b.get("text", "") for b in r.json().get("content", []))
            return json.loads(texto[texto.index("{"): texto.rindex("}") + 1])
        except Exception:  # sin red, JSON inválido, etc.: se usa el respaldo
            logger.warning("La IA externa no respondió; se usa el modo de respaldo.")
            return None


def obtener_ia() -> ClienteIA:
    cfg = get_settings()
    return ClienteIA(cfg.anthropic_api_key, cfg.ia_modelo)

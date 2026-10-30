"""Adaptador de la IA externa (regla 12). Dos proveedores por API, con la clave del `.env`: Google Gemini (gratuito, el predeterminado) y Claude (Anthropic, de pago).
Sin clave, o si la API falla (429 límite gratuito, 503 saturada, red caída...), `json_estructurado` devuelve None y cada caso de uso responde con su modo de respaldo (reglas locales)."""
import json
import logging

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)
URL_MENSAJES = "https://api.anthropic.com/v1/messages"
URL_GEMINI = "https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent"
MODELOS_POR_DEFECTO = {"gemini": "gemini-3.1-flash-lite", "anthropic": "claude-haiku-5-5"}


def _objeto_json(texto: str) -> dict:
    return json.loads(texto[texto.index("{"): texto.rindex("}") + 1])


class ClienteIA:
    def __init__(self, clave: str, modelo: str, http=None, proveedor: str = "anthropic"):
        self.clave = clave
        self.modelo = modelo
        self.proveedor = proveedor
        self.http = http or httpx.post  # en las pruebas se reemplaza por un doble en memoria

    @property
    def activo(self) -> bool:
        return bool(self.clave)

    def json_estructurado(self, sistema: str, usuario: str) -> dict | None:
        """Pide a la IA una respuesta JSON. None si no hay clave, si la API no responde o si lo devuelto no es un objeto JSON."""
        if not self.activo:
            return None
        try:
            return self._gemini(sistema, usuario) if self.proveedor == "gemini" else self._anthropic(sistema, usuario)
        except Exception as error:  # sin red, JSON inválido, etc.: se usa el respaldo (solo se registra el tipo de error, nunca la clave ni el prompt)
            logger.warning("La IA externa (%s) no respondió (%s); se usa el modo de respaldo.", self.proveedor, type(error).__name__)
            return None

    def _anthropic(self, sistema: str, usuario: str) -> dict | None:
        r = self.http(
            URL_MENSAJES, timeout=20,
            headers={"x-api-key": self.clave, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": self.modelo, "max_tokens": 600, "system": sistema, "messages": [{"role": "user", "content": usuario}]},
        )
        if r.status_code != 200:
            logger.warning("Claude respondió %s; se usa el modo de respaldo.", r.status_code)
            return None
        return _objeto_json("".join(b.get("text", "") for b in r.json().get("content", [])))

    def _gemini(self, sistema: str, usuario: str) -> dict | None:
        cuerpo = {
            "systemInstruction": {"parts": [{"text": sistema}]},
            "contents": [{"role": "user", "parts": [{"text": usuario}]}],
            "generationConfig": {"responseMimeType": "application/json", "maxOutputTokens": 1024, "thinkingConfig": {"thinkingBudget": 0}},  # sin «pensamiento»: no gasta tokens
        }
        enviar = lambda: self.http(  # noqa: E731
            URL_GEMINI.format(modelo=self.modelo), timeout=20,
            headers={"x-goog-api-key": self.clave, "content-type": "application/json"}, json=cuerpo,
        )
        r = enviar()
        if r.status_code == 400:  # un modelo que no admite apagar el pensamiento: se reintenta sin esa opción
            del cuerpo["generationConfig"]["thinkingConfig"]
            r = enviar()
        if r.status_code != 200:  # 429 = límite gratuito, 503 = modelo saturado
            logger.warning("Gemini respondió %s; se usa el modo de respaldo.", r.status_code)
            return None
        partes = r.json()["candidates"][0]["content"]["parts"]
        return _objeto_json("".join(p.get("text", "") for p in partes if not p.get("thought")))


def obtener_ia() -> ClienteIA:
    cfg = get_settings()
    proveedor = cfg.ia_proveedor.strip().lower()
    if proveedor not in MODELOS_POR_DEFECTO:
        proveedor = "gemini"
    clave = cfg.gemini_api_key if proveedor == "gemini" else cfg.anthropic_api_key
    return ClienteIA(clave, cfg.ia_modelo or MODELOS_POR_DEFECTO[proveedor], proveedor=proveedor)

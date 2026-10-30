"""Prompt L · IA con Google Gemini (gratuito) o Claude — mismo contrato `json_estructurado`, fallos y límites caen al respaldo, y la elección del proveedor sale del `.env`."""
import json

from app.core import ia
from app.core.config import get_settings
from app.core.ia import ClienteIA, obtener_ia


class GeminiFalso:
    """Imita generateContent de Gemini: devuelve las respuestas dadas, en orden, y guarda cada llamada."""

    def __init__(self, *respuestas):
        self.respuestas, self.llamadas = list(respuestas), []

    def __call__(self, url, headers, json, timeout):
        self.llamadas.append((url, headers, json))
        estado, partes = self.respuestas.pop(0) if len(self.respuestas) > 1 else self.respuestas[0]
        return type("R", (), {"status_code": estado, "json": lambda s: {"candidates": [{"content": {"parts": partes}}]}})()


def _ok(texto):
    return 200, [{"text": texto}]


def _gemini(api, modelo="gemini-flash-latest"):
    return ClienteIA("clave-gemini", modelo, http=api, proveedor="gemini")


def test_01_gemini_recibe_la_peticion_con_el_formato_de_la_api():
    api = GeminiFalso(_ok(json.dumps({"seleccion": [1, 2]})))
    r = _gemini(api).json_estructurado("Eres un asistente de moda.", "Quiero una camisa")
    assert r == {"seleccion": [1, 2]}
    url, headers, cuerpo = api.llamadas[0]
    assert url == "https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent"
    assert headers["x-goog-api-key"] == "clave-gemini" and "Authorization" not in headers
    assert cuerpo["systemInstruction"] == {"parts": [{"text": "Eres un asistente de moda."}]}
    assert cuerpo["contents"] == [{"role": "user", "parts": [{"text": "Quiero una camisa"}]}]
    assert cuerpo["generationConfig"]["responseMimeType"] == "application/json" and cuerpo["generationConfig"]["thinkingConfig"] == {"thinkingBudget": 0}


def test_02_ignora_las_partes_de_pensamiento_y_el_texto_alrededor_del_json():
    api = GeminiFalso((200, [{"text": "razonando...", "thought": True}, {"text": 'Aquí va: {"a": 1}'}]))
    assert _gemini(api).json_estructurado("s", "u") == {"a": 1}


def test_03_un_modelo_que_no_admite_apagar_el_pensamiento_se_reintenta_sin_esa_opcion():
    api = GeminiFalso((400, []), _ok('{"a": 1}'))
    assert _gemini(api).json_estructurado("s", "u") == {"a": 1}
    assert len(api.llamadas) == 2 and "thinkingConfig" not in api.llamadas[1][2]["generationConfig"]


def test_04_limite_gratuito_saturacion_y_fallos_caen_al_respaldo():
    for estado in (429, 503, 500, 403):
        api = GeminiFalso((estado, []))
        assert _gemini(api).json_estructurado("s", "u") is None, estado
    assert _gemini(GeminiFalso(_ok("no es json"))).json_estructurado("s", "u") is None

    def sin_red(**_):
        raise ConnectionError("sin internet")

    assert _gemini(lambda url, **kw: sin_red()).json_estructurado("s", "u") is None
    sin_clave = GeminiFalso(_ok("{}"))
    assert ClienteIA("", "m", http=sin_clave, proveedor="gemini").json_estructurado("s", "u") is None and sin_clave.llamadas == []


def test_05_claude_sigue_funcionando_como_proveedor_alterno():
    llamadas = []

    def claude(url, headers, json, timeout):
        llamadas.append((url, headers))
        return type("R", (), {"status_code": 200, "json": lambda s: {"content": [{"type": "text", "text": '{"b": 2}'}]}})()

    assert ClienteIA("sk", "claude-haiku-5-5", http=claude, proveedor="anthropic").json_estructurado("s", "u") == {"b": 2}
    assert llamadas[0][0] == ia.URL_MENSAJES and llamadas[0][1]["x-api-key"] == "sk"


def test_06_el_proveedor_y_el_modelo_salen_de_la_configuracion(monkeypatch):
    cfg = get_settings()
    monkeypatch.setattr(cfg, "ia_modelo", "")
    monkeypatch.setattr(cfg, "gemini_api_key", "g")
    monkeypatch.setattr(cfg, "anthropic_api_key", "a")
    monkeypatch.setattr(cfg, "ia_proveedor", "gemini")
    cliente = obtener_ia()
    assert (cliente.proveedor, cliente.modelo, cliente.clave) == ("gemini", "gemini-flash-latest", "g")
    monkeypatch.setattr(cfg, "ia_proveedor", "anthropic")
    cliente = obtener_ia()
    assert (cliente.proveedor, cliente.modelo, cliente.clave) == ("anthropic", "claude-haiku-5-5", "a")
    monkeypatch.setattr(cfg, "ia_proveedor", "gemini")
    monkeypatch.setattr(cfg, "ia_modelo", "gemini-otro")
    assert obtener_ia().modelo == "gemini-otro"  # el modelo se cambia sin tocar código
    monkeypatch.setattr(cfg, "ia_proveedor", "inventado")
    assert obtener_ia().proveedor == "gemini"


def test_07_sin_clave_todo_sigue_en_modo_de_respaldo(monkeypatch):
    cfg = get_settings()
    monkeypatch.setattr(cfg, "gemini_api_key", "")
    monkeypatch.setattr(cfg, "ia_proveedor", "gemini")
    assert not obtener_ia().activo and obtener_ia().json_estructurado("s", "u") is None


def test_08_los_casos_de_uso_funcionan_igual_con_gemini(inv, mundo, db, client, monkeypatch):
    """CU-23 con el doble de Gemini: la interfaz `json_estructurado` no cambió, así que el caso de uso no se entera del proveedor."""
    from app.modules.ia.cu23_reportes_generativos import service
    from tests.reportes_util import con_ia, movimiento

    con_ia(db, mundo)
    movimiento(client, inv, mundo)
    api = GeminiFalso(_ok(json.dumps({"ventas": True, "periodo": "mes"})))
    monkeypatch.setattr(service, "obtener_ia", lambda: ClienteIA("clave", "gemini-flash-latest", http=api, proveedor="gemini"))
    r = client.post("/api/ia/reportes", json={"prompt": "ventas de este mes"}, headers=inv.h_admin)
    assert r.status_code == 201 and r.json()["origen"] in ("IA", "REGLAS") and len(api.llamadas) == 1
    api_caida = GeminiFalso((429, []))
    monkeypatch.setattr(service, "obtener_ia", lambda: ClienteIA("clave", "gemini-flash-latest", http=api_caida, proveedor="gemini"))
    r = client.post("/api/ia/reportes", json={"prompt": "ventas de este mes"}, headers=inv.h_admin)
    assert r.status_code == 201 and r.json()["origen"] == "REGLAS"  # el límite gratuito no deja sin reporte al usuario

"""Prompt L · Despliegue en Railway — conexión a la base, SECRET_KEY de producción, /salud, datos de demostración sin duplicar, Brevo y credenciales de FCM por variable."""
import importlib.util
import json
import logging
from pathlib import Path

import pytest
from sqlalchemy import func, select

import app.main as principal
from app import arranque
from app.core import correo
from app.core.config import Settings, get_settings
from app.core.correo import MSG_CORREO, ErrorCorreo
from app.modules.plataforma.models import Empresa
from app.modules.reservas.rf11_notificaciones import push
from app.modules.reservas.rf11_notificaciones.push import AdaptadorFCM

MSG_SECRET_KEY = arranque.MSG_SECRET_KEY


def test_01_la_url_de_railway_se_convierte_al_driver_psycopg():
    assert Settings(database_url="postgresql://u:p@host:5432/railway").database_url == "postgresql+psycopg://u:p@host:5432/railway"
    assert Settings(database_url="postgres://u:p@host/db").database_url == "postgresql+psycopg://u:p@host/db"
    ya_lista = "postgresql+psycopg://u:p@localhost/db"
    assert Settings(database_url=ya_lista).database_url == ya_lista


def test_02_en_produccion_no_arranca_con_la_secret_key_por_defecto():
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        arranque.validar_configuracion(Settings(entorno="produccion"))
    with pytest.raises(RuntimeError):
        arranque.validar_configuracion(Settings(railway_environment="production"))  # Railway lo define solo
    arranque.validar_configuracion(Settings(entorno="produccion", secret_key="una-clave-larga-y-secreta-de-verdad"))
    arranque.validar_configuracion(Settings(entorno="desarrollo"))  # en desarrollo se permite la de por defecto
    assert Settings(railway_environment="production").es_produccion and not Settings().es_produccion


def test_03_salud_responde_ok_y_503_si_la_base_no_contesta(client, monkeypatch):
    r = client.get("/salud")
    assert r.status_code == 200 and r.json() == {"estado": "ok"}

    class BaseCaida:
        def connect(self):
            raise ConnectionError("sin base")

    monkeypatch.setattr(principal, "engine", BaseCaida())
    assert client.get("/salud").status_code == 503


def test_04_los_datos_de_demostracion_se_cargan_una_sola_vez(db):
    assert arranque.base_vacia(db)
    assert arranque.cargar_datos_demo(db) == "Datos de demostración cargados."
    assert db.scalar(select(func.count()).select_from(Empresa)) == 2 and not arranque.base_vacia(db)
    mensaje = arranque.cargar_datos_demo(db)  # segundo arranque: no duplica nada
    assert mensaje.startswith("La base ya tiene datos") and db.scalar(select(func.count()).select_from(Empresa)) == 2


def test_05_sin_cargar_datos_demo_el_arranque_no_toca_la_base(db, monkeypatch):
    monkeypatch.setattr(get_settings(), "cargar_datos_demo", False)
    arranque.main()
    assert arranque.base_vacia(db)


# ---------------- correo (Brevo) ----------------
class RespuestaBrevo:
    def __init__(self, estado, texto="{}"):
        self.status_code, self.text = estado, texto


def _brevo(monkeypatch, estado, texto="{}"):
    monkeypatch.setattr(get_settings(), "brevo_api_key", "clave-de-prueba")
    llamadas = []
    monkeypatch.setattr(correo.httpx, "post", lambda url, **kw: llamadas.append((url, kw)) or RespuestaBrevo(estado, texto))
    return llamadas


def test_06_el_correo_sale_por_brevo(monkeypatch):
    llamadas = _brevo(monkeypatch, 201)
    correo.enviar_correo("cliente@x.com", "Asunto", "<p>Hola</p>")
    url, kw = llamadas[0]
    assert url == "https://api.brevo.com/v3/smtp/email" and kw["json"]["to"] == [{"email": "cliente@x.com"}] and kw["headers"]["api-key"] == "clave-de-prueba"


def test_07_si_brevo_rechaza_el_envio_hay_un_error_claro_y_queda_registrado(monkeypatch, caplog):
    _brevo(monkeypatch, 400, '{"code":"invalid_parameter","message":"Sender is not valid / not verified"}')
    with caplog.at_level(logging.ERROR, logger="fashionstore.correo"), pytest.raises(ErrorCorreo) as e:
        correo.enviar_correo("cliente@x.com", "Asunto", "<p>Hola</p>")
    assert e.value.status_code == 502 and e.value.message == MSG_CORREO and "remitente no está verificado" in e.value.detalle
    assert "Brevo rechazó el correo a cliente@x.com" in caplog.text
    _brevo(monkeypatch, 401, '{"message":"Key not found"}')
    with pytest.raises(ErrorCorreo) as e:
        correo.enviar_correo("cliente@x.com", "Asunto", "<p>Hola</p>")
    assert "clave de API" in e.value.detalle
    _brevo(monkeypatch, 403, '{"message":"We have detected you are using an unrecognised IP address 1.2.3.4"}')
    with pytest.raises(ErrorCorreo) as e:
        correo.enviar_correo("cliente@x.com", "Asunto", "<p>Hola</p>")
    assert "IP" in e.value.detalle


def test_08_la_api_devuelve_el_error_de_correo_al_pedir_restablecer_la_contrasena(datos, mundo, client, monkeypatch):
    _brevo(monkeypatch, 400, "Sender not verified")
    r = client.post("/api/auth/olvide-password", json={"codigo_empresa": "EMP-A", "email": mundo.admin_a.email})
    assert r.status_code == 502 and r.json()["detail"] == MSG_CORREO
    assert "Sender" not in r.text  # el detalle técnico queda en los registros, no en la respuesta


def test_09_el_script_de_prueba_de_correo_imprime_la_causa(monkeypatch, capsys):
    ruta = Path(__file__).resolve().parent.parent / "scripts" / "probar_correo.py"
    especificacion = importlib.util.spec_from_file_location("probar_correo", ruta)
    modulo = importlib.util.module_from_spec(especificacion)
    especificacion.loader.exec_module(modulo)
    monkeypatch.setattr(get_settings(), "brevo_api_key", "")
    monkeypatch.setattr("sys.argv", ["probar_correo.py", "yo@x.com"])
    assert modulo.main() == 1 and "Falta BREVO_API_KEY" in capsys.readouterr().out
    _brevo(monkeypatch, 400, "Sender not verified")
    assert modulo.main() == 1 and "remitente no está verificado" in capsys.readouterr().out
    _brevo(monkeypatch, 201)
    assert modulo.main() == 0 and "enviado" in capsys.readouterr().out


# ---------------- FCM con el JSON en una variable ----------------
def test_10_fcm_acepta_el_contenido_del_json_de_la_cuenta_de_servicio(monkeypatch):
    leido = {}

    class Credenciales:
        token = "token-de-acceso"

        def refresh(self, _):
            pass

    def desde_info(info, scopes):
        leido["info"], leido["scopes"] = info, scopes
        return Credenciales()

    from google.oauth2 import service_account

    monkeypatch.setattr(service_account.Credentials, "from_service_account_info", staticmethod(desde_info))
    adaptador = AdaptadorFCM("", "mi-proyecto", credenciales_json=json.dumps({"client_email": "a@b.iam", "private_key": "k"}))
    assert adaptador._token_de_acceso() == "token-de-acceso" and leido["info"]["client_email"] == "a@b.iam" and leido["scopes"] == [AdaptadorFCM.ALCANCE]
    assert Settings(fcm_credenciales_json="{}", fcm_proyecto="p").fcm_activo and not Settings(fcm_proyecto="p").fcm_activo


def test_11_el_aviso_movil_usa_el_canal_de_alta_importancia(monkeypatch):
    enviadas = []
    AdaptadorFCM("c", "p", enviar=lambda url, cuerpo: enviadas.append(cuerpo) or type("R", (), {"status_code": 200})()).enviar("t", push.Mensaje("a", "b"))
    assert enviadas[0]["message"]["android"] == {"priority": "HIGH", "notification": {"channel_id": push.CANAL_ANDROID}}

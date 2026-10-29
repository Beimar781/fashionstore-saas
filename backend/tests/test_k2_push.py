"""Fase K, ajuste 2 · Avisos push (regla 17): dispositivos del usuario, adaptadores Web Push y FCM con modo simulado, y el aviso al cliente en la devolución o cambio (CU-41)."""
import json

import pytest
from sqlalchemy import text

from app.modules.reservas import publico as reservas
from app.modules.reservas.rf11_notificaciones import push
from app.modules.reservas.rf11_notificaciones.push import AdaptadorFCM, AdaptadorWebPush, DispositivoCaducado, Mensaje, ServicioPush
from tests.compras_util import stock_listo
from tests.caja_util import vender
from tests.devoluciones_util import devolver_ok, venta_en_caja

SUSCRIPCION = json.dumps({"endpoint": "https://push.ejemplo.com/abc123", "keys": {"p256dh": "BPclave", "auth": "authsecreto"}})


class Doble:
    """Adaptador en memoria: guarda lo que se le envía o falla como se le indique."""

    def __init__(self, falla=None):
        self.enviados, self.falla = [], falla

    def enviar(self, token, mensaje):
        if self.falla:
            raise self.falla
        self.enviados.append((token, mensaje))


def _cliente(datos, mundo, inv):
    """Sesión del cliente de EMP-A (cliente@tienda.com) y su usuario."""
    from app.modules.acceso.models import Usuario
    u = datos.db.query(Usuario).filter_by(empresa_id=mundo.a.id, email="cliente@tienda.com").first()
    return inv.h_cliente, u


def _dispositivo(client, h, canal="WEB", token=SUSCRIPCION):
    return client.post("/api/notificaciones/dispositivos", json={"canal": canal, "token": token}, headers=h)


def _venta_a_cliente(client, inv):
    return vender(client, inv.h_cajero, (inv.v_sm_rojo, 1), cliente_email="cliente@tienda.com")["pedido"]  # la venta queda en el historial del cliente


def _devolucion_a_cliente(client, inv):
    p = _venta_a_cliente(client, inv)
    return devolver_ok(client, inv.h_cajero, p["comprobante_numero"], [(p["items"][0], 1)])


def _envios(db, usuario_id):
    return db.execute(text("SELECT canal, estado, titulo, error FROM push_envios WHERE usuario_id = :u ORDER BY id"), {"u": usuario_id}).all()


def test_01_sin_claves_la_configuracion_queda_en_modo_simulado(inv, client):
    r = client.get("/api/notificaciones/push/config", headers=inv.h_cliente)
    assert r.status_code == 200 and r.json() == {"vapid_public_key": "", "web_real": False, "movil_real": False}


def test_02_el_usuario_registra_y_quita_sus_dispositivos(inv, mundo, datos, client, db):
    h, u = _cliente(datos, mundo, inv)
    assert _dispositivo(client, h).status_code == 201
    assert _dispositivo(client, h).json()["id"] == _dispositivo(client, h).json()["id"]  # el mismo navegador no se duplica
    assert _dispositivo(client, h, "MOVIL", "token-fcm-1").status_code == 201
    assert db.execute(text("SELECT count(*) FROM dispositivos WHERE usuario_id = :u AND activo"), {"u": u.id}).scalar() == 2
    r = client.post("/api/notificaciones/dispositivos/baja", json={"canal": "WEB", "token": SUSCRIPCION}, headers=h)
    assert r.status_code == 204
    assert db.execute(text("SELECT count(*) FROM dispositivos WHERE usuario_id = :u AND activo"), {"u": u.id}).scalar() == 1
    assert _dispositivo(client, h).status_code == 201  # volver a activarlos reutiliza el registro
    assert db.execute(text("SELECT count(*) FROM dispositivos WHERE usuario_id = :u"), {"u": u.id}).scalar() == 2


def test_03_los_datos_del_dispositivo_se_validan(inv, client):
    r = _dispositivo(client, inv.h_cliente, "WEB", "esto no es una suscripción")
    assert r.status_code == 422 and r.json()["detail"] == "La suscripción del navegador no es válida."
    r = _dispositivo(client, inv.h_cliente, "WEB", json.dumps({"endpoint": "http://inseguro.com", "keys": {}}))
    assert r.status_code == 422 and r.json()["detail"] == "La suscripción del navegador no es válida."
    assert _dispositivo(client, inv.h_cliente, "MOVIL", "   ").status_code == 422
    assert client.post("/api/notificaciones/dispositivos", json={"canal": "TV", "token": "x"}, headers=inv.h_cliente).status_code == 422
    assert client.post("/api/notificaciones/dispositivos", json={"canal": "WEB", "token": SUSCRIPCION}).status_code in (401, 403)


def test_04_la_devolucion_avisa_al_cliente_en_la_campana_y_por_push(inv, mundo, datos, client, db):
    stock_listo(inv, mundo)
    h, u = _cliente(datos, mundo, inv)
    _dispositivo(client, h)
    _dispositivo(client, h, "MOVIL", "token-fcm-1")
    d = _devolucion_a_cliente(client, inv)
    avisos = [n for n in client.get("/api/notificaciones", headers=h).json() if n["tipo"] == "DEVOLUCION"]
    medio = "tarjeta" if d["medio_reembolso"] == "TARJETA" else "efectivo"
    assert len(avisos) == 1 and avisos[0]["titulo"] == "Devolución registrada"
    assert avisos[0]["mensaje"] == f"Su devolución {d['numero']} fue registrada. Reembolso: Bs {d['reembolso']} por {medio}."
    assert (avisos[0]["referencia_tipo"], avisos[0]["referencia_id"]) == ("DEVOLUCION", d["id"])
    assert [(canal, estado, titulo) for canal, estado, titulo, _ in _envios(db, u.id)] == [("WEB", "SIMULADO", "Devolución registrada"), ("MOVIL", "SIMULADO", "Devolución registrada")]


def test_05_un_cambio_se_avisa_con_su_propio_titulo(inv, mundo, datos, client, db):
    stock_listo(inv, mundo)
    h, u = _cliente(datos, mundo, inv)
    _dispositivo(client, h)
    p = _venta_a_cliente(client, inv)
    devolver_ok(client, inv.h_cajero, p["comprobante_numero"], [(p["items"][0], 1)], tipo="CAMBIO", nuevos=[(inv.var[("M", "Rojo")], 1)])
    assert [t for _, _, t, _ in _envios(db, u.id)] == ["Cambio registrado"]
    aviso = next(n for n in client.get("/api/notificaciones", headers=h).json() if n["tipo"] == "DEVOLUCION")
    assert aviso["mensaje"].startswith("Su cambio NDV-") and aviso["mensaje"].endswith("fue registrado.")  # sin diferencia a favor del cliente no hay reembolso


def test_06_una_venta_sin_cuenta_de_cliente_o_sin_dispositivos_no_falla(inv, mundo, datos, client, db):
    stock_listo(inv, mundo)
    p = venta_en_caja(client, inv, (inv.v_sm_rojo, 1))  # venta de mostrador sin cliente registrado
    devolver_ok(client, inv.h_cajero, p["comprobante_numero"], [(p["items"][0], 1)])
    assert db.execute(text("SELECT count(*) FROM push_envios")).scalar() == 0
    h, u = _cliente(datos, mundo, inv)  # con cuenta pero sin dispositivos: solo la campana
    _devolucion_a_cliente(client, inv)
    assert any(n["tipo"] == "DEVOLUCION" for n in client.get("/api/notificaciones", headers=h).json()) and _envios(db, u.id) == []


def test_07_el_push_solo_llega_a_los_dispositivos_de_ese_cliente(inv, mundo, datos, client, db):
    stock_listo(inv, mundo)
    h, u = _cliente(datos, mundo, inv)
    _dispositivo(client, h)
    otro = datos.usuario(mundo.a, "Cliente", email="otro@tienda.com")
    h_otro = datos.login(otro, mundo.a)
    _dispositivo(client, h_otro, "WEB", json.dumps({"endpoint": "https://push.ejemplo.com/otro", "keys": {"p256dh": "k", "auth": "a"}}))
    h_b = datos.login(mundo.admin_b, mundo.b)
    _dispositivo(client, h_b, "MOVIL", "token-de-emp-b")
    _devolucion_a_cliente(client, inv)
    assert len(_envios(db, u.id)) == 1 and _envios(db, otro.id) == []
    assert db.execute(text("SELECT count(*) FROM push_envios WHERE empresa_id = :e"), {"e": mundo.b.id}).scalar() == 0  # EMP-B no recibe nada
    assert not any(n["tipo"] == "DEVOLUCION" for n in client.get("/api/notificaciones", headers=h_otro).json())


def test_08_el_servicio_envia_por_cada_canal_y_anota_el_resultado(inv, mundo, datos, client, db):
    h, u = _cliente(datos, mundo, inv)
    _dispositivo(client, h)
    _dispositivo(client, h, "MOVIL", "token-fcm-1")
    web, movil = Doble(), Doble()
    estados = ServicioPush(db, web, movil).enviar(mundo.a.id, u.id, Mensaje("Hola", "Cuerpo", {"k": "v"}))
    assert estados == ["ENVIADO", "ENVIADO"]
    assert web.enviados[0][0] == SUSCRIPCION and movil.enviados[0][0] == "token-fcm-1" and web.enviados[0][1].titulo == "Hola"
    assert [e for _, e, _, _ in _envios(db, u.id)] == ["ENVIADO", "ENVIADO"]


def test_09_si_el_push_falla_se_anota_y_la_devolucion_sigue_confirmada(inv, mundo, datos, client, db, monkeypatch):
    stock_listo(inv, mundo)
    h, u = _cliente(datos, mundo, inv)
    _dispositivo(client, h)
    monkeypatch.setattr(push, "adaptadores_por_defecto", lambda: (Doble(RuntimeError("El servicio de push no responde")), None))
    d = _devolucion_a_cliente(client, inv)  # el 201 de _devolucion_a_cliente demuestra que la operación no se deshizo
    assert client.get(f"/api/devoluciones/{d['id']}", headers=inv.h_cajero).status_code == 200
    assert _envios(db, u.id) == [("WEB", "FALLIDO", "Devolución registrada", "El servicio de push no responde")]
    assert any(n["tipo"] == "DEVOLUCION" for n in client.get("/api/notificaciones", headers=h).json())  # la campana sí quedó


def test_10_un_dispositivo_que_ya_no_acepta_avisos_se_desactiva(inv, mundo, datos, client, db):
    h, u = _cliente(datos, mundo, inv)
    _dispositivo(client, h, "MOVIL", "token-viejo")
    assert ServicioPush(db, None, Doble(DispositivoCaducado())).enviar(mundo.a.id, u.id, Mensaje("Hola", "x")) == ["FALLIDO"]
    assert db.execute(text("SELECT activo FROM dispositivos WHERE usuario_id = :u"), {"u": u.id}).scalar() is False
    assert ServicioPush(db, None, Doble()).enviar(mundo.a.id, u.id, Mensaje("Hola", "x")) == []  # ya no se vuelve a intentar


def test_11_adaptador_web_arma_la_notificacion_para_el_service_worker():
    llamadas = []
    AdaptadorWebPush("clave-privada", "mailto:a@b.com", enviar=lambda **kw: llamadas.append(kw)).enviar(SUSCRIPCION, Mensaje("Título", "Cuerpo", {"referencia_id": 7}))
    kw = llamadas[0]
    assert kw["subscription_info"]["endpoint"] == "https://push.ejemplo.com/abc123" and kw["vapid_claims"] == {"sub": "mailto:a@b.com"}
    assert json.loads(kw["data"])["notification"] == {"title": "Título", "body": "Cuerpo", "icon": "icons/icon-192.png", "data": {"referencia_id": 7}}


def test_12_adaptador_fcm_interpreta_la_respuesta_del_servicio():
    class Resp:
        def __init__(self, codigo):
            self.status_code = codigo

    enviadas = []
    ok = AdaptadorFCM("cuenta.json", "mi-proyecto", enviar=lambda url, cuerpo: enviadas.append((url, cuerpo)) or Resp(200))
    ok.enviar("token-1", Mensaje("Título", "Cuerpo", {"referencia_id": 7}))
    url, cuerpo = enviadas[0]
    assert url == "https://fcm.googleapis.com/v1/projects/mi-proyecto/messages:send"
    assert cuerpo["message"] == {"token": "token-1", "notification": {"title": "Título", "body": "Cuerpo"}, "data": {"referencia_id": "7"}}
    with pytest.raises(DispositivoCaducado):
        AdaptadorFCM("c", "p", enviar=lambda *_: Resp(404)).enviar("t", Mensaje("a", "b"))
    with pytest.raises(RuntimeError):
        AdaptadorFCM("c", "p", enviar=lambda *_: Resp(500)).enviar("t", Mensaje("a", "b"))


def test_13_la_bitacora_registra_los_dispositivos_sin_guardar_el_token(inv, mundo, datos, client, db):
    h, u = _cliente(datos, mundo, inv)
    _dispositivo(client, h)
    _dispositivo(client, h, "MOVIL", "token-fcm-secreto")
    client.post("/api/notificaciones/dispositivos/baja", json={"canal": "MOVIL", "token": "token-fcm-secreto"}, headers=h)
    filas = db.execute(text("SELECT accion, detalle FROM bitacora WHERE entidad = 'notificación' AND usuario_id = :u ORDER BY id"), {"u": u.id}).all()
    assert [a for a, _ in filas] == ["CREAR", "CREAR", "DESACTIVAR"]
    assert filas[0][1] == "Activó los avisos push en un dispositivo (WEB)" and filas[2][1] == "Desactivó los avisos push en un dispositivo (MOVIL)"
    todo = " ".join(str(c) for c in db.execute(text("SELECT * FROM bitacora")).all())
    assert "token-fcm-secreto" not in todo and "abc123" not in todo and "authsecreto" not in todo


def test_14_avisar_cliente_esta_en_la_interfaz_publica_del_paquete():
    assert reservas.avisar_cliente is push.avisar_cliente

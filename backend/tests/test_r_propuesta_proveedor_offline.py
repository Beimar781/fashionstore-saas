"""Prompt R · B9: el proveedor registra una propuesta de producto sin conexión; se sincroniza con las mismas validaciones del formulario en línea."""
import uuid

from tests.offline_util import ahora_iso, sincronizar, sincronizar_ok


def _op(**payload):
    return {"id": str(uuid.uuid4()), "tipo": "PROPUESTA_PROVEEDOR", "creada_en": ahora_iso(), "payload": payload}


def _cuerpo(inv, **extra):
    return {"nombre": "Chaqueta Impermeable", "coleccion_id": inv.col["id"], "genero": "UNISEX", "precio_base": "260", "material": "Poliéster", **extra}


def test_la_propuesta_offline_llega_al_administrador_y_reenviar_no_la_duplica(inv, client):
    op = _op(**_cuerpo(inv))
    primero, segundo = sincronizar_ok(client, inv.h_prov, op)[0], sincronizar_ok(client, inv.h_prov, op)[0]
    assert primero["estado"] == "CONFIRMADA" and primero["referencia"].startswith("PRO-") and segundo["ya_procesada"] is True
    pendientes = client.get("/api/abastecimiento/propuestas?estado=PENDIENTE", headers=inv.h_admin).json()
    assert [p["nombre"] for p in pendientes] == ["Chaqueta Impermeable"]  # una sola


def test_las_validaciones_son_las_del_formulario_en_linea(inv, client):
    sin_nombre = sincronizar_ok(client, inv.h_prov, _op(**_cuerpo(inv, nombre="")))[0]
    coleccion_ajena = sincronizar_ok(client, inv.h_prov, _op(**_cuerpo(inv, coleccion_id=999999)))[0]
    assert sin_nombre["estado"] == "RECHAZADA"
    assert coleccion_ajena["estado"] == "RECHAZADA" and coleccion_ajena["mensaje"] == "Colección no encontrada."
    assert client.get("/api/abastecimiento/propuestas", headers=inv.h_admin).json() == []


def test_solo_el_proveedor_registra_propuestas_y_otra_empresa_no_las_ve(inv, tienda_b, client):
    assert sincronizar(client, inv.h_admin, _op(**_cuerpo(inv))).status_code == 403  # el Administrador ni siquiera usa la cola
    assert sincronizar_ok(client, inv.h_cajero, _op(**_cuerpo(inv)))[0]["estado"] == "RECHAZADA"
    sincronizar_ok(client, inv.h_prov, _op(**_cuerpo(inv)))
    assert client.get("/api/abastecimiento/propuestas", headers=tienda_b.h_admin).json() == []

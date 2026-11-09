"""Prompt Q · una operación CANCELAR_RESERVA no puede tocar la reserva de otra empresa (404, aislamiento RN18)."""
import uuid

from tests.catalogo_util import cabecera_cliente
from tests.offline_util import sincronizar_ok, stock_listo
from tests.reservas_util import cuando


def test_cancelar_reserva_de_otra_empresa_queda_rechazada_y_no_la_cancela(inv, mundo, datos, client):
    stock_listo(inv, mundo)
    reserva = client.post("/api/reservas", json={"sucursal_id": inv.centro.id, "programada_para": cuando(1), "notas": "", "items": [{"variante_id": inv.v_sm_rojo["id"], "cantidad": 1}]}, headers=inv.h_cliente).json()
    h_b = cabecera_cliente(datos, mundo.b)
    operacion = {"id": str(uuid.uuid4()), "tipo": "CANCELAR_RESERVA", "creada_en": "2026-11-08T12:00:00Z", "sucursal_id": None, "payload": {"reserva_id": reserva["id"], "motivo": "intruso"}}
    resultado = client.post("/api/offline/sincronizar", json={"operaciones": [operacion]}, headers=h_b)
    assert resultado.status_code in (200, 403, 404), resultado.text
    if resultado.status_code == 200:
        assert resultado.json()["resultados"][0]["estado"] in ("RECHAZADA", "ERROR")
    assert client.get(f"/api/reservas/{reserva['id']}", headers=inv.h_cliente).json()["estado"] != "CANCELADA"

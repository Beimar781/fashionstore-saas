"""CU-38 Sincronizar operaciones pendientes — ventas de contado y reservas offline, idempotencia (RN12), conflicto sin descuento parcial (RN14), rechazos, orden, fallos y aislamiento."""
import uuid

from sqlalchemy import text

from app.modules.offline.cu38_sincronizar import service
from app.modules.offline.ejecucion import Ejecutor
from tests.compras_util import existencias
from tests.offline_util import agregar_stock, ahora_iso, contar, op_reserva, op_venta, sincronizar, sincronizar_ok, stock_listo
from tests.reservas_util import fila


def _centro(client, inv, variante=None):
    return existencias(client, inv.h_enc_centro, variante or inv.v_sm_rojo)


def test_01_la_venta_de_contado_offline_se_confirma_con_su_comprobante(inv, mundo, client, db):
    stock_listo(inv, mundo)
    r = sincronizar_ok(client, inv.h_cajero, op_venta([(inv.v_sm_rojo, 2)], 250))[0]
    assert (r["estado"], r["mensaje"], r["ya_procesada"], r["detalle"]) == ("CONFIRMADA", "Operación confirmada.", False, None)
    assert r["referencia"] and r["comprobante"].startswith(f"CMP-{inv.centro.id:03d}-")
    f = _centro(client, inv)
    assert (f["disponible"], f["vendida"]) == (8, 2)  # el stock se descontó al confirmar
    pedido = db.execute(text("SELECT estado, canal, total FROM pedidos WHERE codigo = :c"), {"c": r["referencia"]}).one()
    assert (pedido[0], pedido[1], str(pedido[2])) == ("PAGADO", "PRESENCIAL", "200.00")
    pago = db.execute(text("SELECT p.metodo, p.estado, p.monto_recibido, p.cambio FROM pagos p JOIN pedidos o ON o.id = p.pedido_id WHERE o.codigo = :c"), {"c": r["referencia"]}).one()
    assert (pago[0], pago[1], str(pago[2]), str(pago[3])) == ("EFECTIVO", "APROBADO", "250.00", "50.00")  # RN13: de contado, con su cambio
    resumen = client.get("/api/reportes/sucursal/resumen", headers=inv.h_enc_centro).json()
    assert resumen["total_vendido"] == "200.00"  # aparece en las ventas de la sucursal como cualquier venta de caja


def test_02_reenviar_una_operacion_confirmada_no_la_duplica(inv, mundo, client, db):
    stock_listo(inv, mundo)
    op = op_venta([(inv.v_sm_rojo, 3)], 300)
    primera = sincronizar_ok(client, inv.h_cajero, op)[0]
    segunda = sincronizar_ok(client, inv.h_cajero, op)[0]  # reintento tras una respuesta perdida (RN12, RNF05)
    assert segunda["ya_procesada"] is True and (segunda["estado"], segunda["referencia"], segunda["comprobante"]) == (primera["estado"], primera["referencia"], primera["comprobante"])
    assert contar(db, "pedidos", canal="PRESENCIAL") == 1 and contar(db, "operaciones_offline") == 1
    assert (_centro(client, inv)["disponible"], _centro(client, inv)["vendida"]) == (7, 3)
    doble = sincronizar_ok(client, inv.h_cajero, op, op)  # el mismo id dos veces en un lote
    assert [r["ya_procesada"] for r in doble] == [True, True] and contar(db, "pedidos", canal="PRESENCIAL") == 1


def test_03_sin_existencias_queda_en_conflicto_y_no_descuenta_nada(inv, mundo, client, db):
    stock_listo(inv, mundo, centro=10)
    op = op_venta([(inv.v_sm_rojo, 3), (inv.var[("M", "Azul")], 11)], 5000)  # una línea alcanza y la otra no: nada se descuenta a medias (RN14)
    r = sincronizar_ok(client, inv.h_cajero, op)[0]
    assert r["estado"] == "EN_CONFLICTO" and r["referencia"] is None and r["mensaje"].startswith("No hay existencias suficientes para esta operación. No se descontó nada")
    assert r["detalle"]["faltantes"] == [{"variante_id": inv.var[("M", "Azul")]["id"], "producto": "Camisa Oxford", "talla": "M", "color": "Azul", "solicitadas": 11, "disponibles": 10}]
    for v in (inv.v_sm_rojo, inv.var[("M", "Azul")]):
        f = _centro(client, inv, v)
        assert (f["disponible"], f["vendida"]) == (10, 0)
    assert contar(db, "pedidos") == 0 and contar(db, "pagos") == 0
    avisos = client.get("/api/notificaciones", headers=inv.h_enc_centro).json()
    assert any(a["tipo"] == "CONFLICTO_SYNC" for a in avisos)  # RF11: el Encargado se entera
    assert sincronizar_ok(client, inv.h_cajero, op)[0]["ya_procesada"] is True  # un conflicto reenviado no se vuelve a aplicar solo


def test_04_rechazos_con_el_mensaje_de_la_regla(inv, mundo, client, db):
    stock_listo(inv, mundo)
    corto = sincronizar_ok(client, inv.h_cajero, op_venta([(inv.v_sm_rojo, 2)], 150))[0]  # el total es Bs 200
    assert (corto["estado"], corto["mensaje"]) == ("RECHAZADA", "El monto recibido es menor al total de la venta.")
    inexistente = sincronizar_ok(client, inv.h_cajero, op_venta([({"id": 99999}, 1)], 100))[0]
    assert (inexistente["estado"], inexistente["mensaje"]) == ("RECHAZADA", "Una o más prendas ya no están disponibles en el catálogo.")
    malformada = sincronizar_ok(client, inv.h_cajero, {"id": str(uuid.uuid4()), "tipo": "VENTA_CONTADO", "creada_en": ahora_iso(), "payload": {"items": []}})[0]
    assert (malformada["estado"], malformada["mensaje"]) == ("RECHAZADA", "La operación no tiene el formato esperado.")
    assert contar(db, "pedidos") == 0 and _centro(client, inv)["vendida"] == 0
    assert contar(db, "operaciones_offline", estado="RECHAZADA") == 3  # queda constancia de cada rechazo


def test_05_la_reserva_offline_del_cliente(inv, mundo, client, db):
    stock_listo(inv, mundo)
    r = sincronizar_ok(client, inv.h_cliente, op_reserva(inv.centro, [(inv.v_sm_rojo, 2)]))[0]
    assert r["estado"] == "CONFIRMADA" and r["referencia"].startswith("RSV-") and r["comprobante"] is None
    f = fila(client, inv.h_enc_centro, inv.v_sm_rojo)
    assert (f["disponible"], f["reservada"]) == (8, 2)  # el stock pasó de disponible a reservado
    assert any(x["codigo"] == r["referencia"] for x in client.get("/api/reservas", headers=inv.h_cliente).json())
    pasada = sincronizar_ok(client, inv.h_cliente, op_reserva(inv.centro, [(inv.v_sm_rojo, 1)], dias=-3))[0]  # el horario ya pasó al sincronizar
    assert pasada["estado"] == "RECHAZADA" and fila(client, inv.h_enc_centro, inv.v_sm_rojo)["reservada"] == 2
    sin_stock = sincronizar_ok(client, inv.h_cliente, op_reserva(inv.centro, [(inv.v_sm_rojo, 9)]))[0]
    assert sin_stock["estado"] == "EN_CONFLICTO" and sin_stock["detalle"]["faltantes"][0]["disponibles"] == 8


def test_06_cada_rol_solo_registra_lo_suyo_y_en_su_sucursal(inv, mundo, client):
    stock_listo(inv, mundo)
    assert sincronizar_ok(client, inv.h_cajero, op_reserva(inv.centro, [(inv.v_sm_rojo, 1)]))[0]["mensaje"] == "No tiene permisos para registrar este tipo de operación sin conexión."
    assert sincronizar_ok(client, inv.h_cliente, op_venta([(inv.v_sm_rojo, 1)], 100))[0]["mensaje"] == "No tiene permisos para registrar este tipo de operación sin conexión."
    de_otra = op_venta([(inv.v_sm_rojo, 1)], 100) | {"sucursal_id": inv.norte.id}  # el Cajero es de Centro (RN10)
    assert sincronizar_ok(client, inv.h_cajero, de_otra)[0]["mensaje"] == "La operación corresponde a otra sucursal."
    sin_sucursal = op_reserva(inv.centro, [(inv.v_sm_rojo, 1)]) | {"sucursal_id": 99999, "payload": {"sucursal_id": 99999, "programada_para": "2030-01-01T10:00", "items": []}}
    assert sincronizar_ok(client, inv.h_cliente, sin_sucursal)[0]["mensaje"] == "Sucursal no encontrada."
    assert sincronizar(client, inv.h_admin, op_venta([(inv.v_sm_rojo, 1)], 100)).status_code == 403
    assert sincronizar(client, inv.h_cajero).status_code == 422  # un lote vacío no es válido
    assert _centro(client, inv)["vendida"] == 0


def test_07_un_identificador_ajeno_no_pisa_la_operacion_original(inv, mundo, client, db):
    stock_listo(inv, mundo)
    op = op_venta([(inv.v_sm_rojo, 1)], 100)
    original = sincronizar_ok(client, inv.h_cajero, op)[0]
    ajeno = sincronizar_ok(client, inv.h_enc_centro, op)[0]
    assert (ajeno["estado"], ajeno["mensaje"], ajeno["ya_procesada"]) == ("RECHAZADA", "Este identificador de operación ya fue utilizado por otro usuario.", False)
    assert contar(db, "operaciones_offline") == 1 and sincronizar_ok(client, inv.h_cajero, op)[0]["referencia"] == original["referencia"]


def test_08_las_operaciones_se_aplican_en_el_orden_en_que_ocurrieron(inv, mundo, client):
    stock_listo(inv, mundo, centro=1)  # queda una sola unidad
    tarde = op_venta([(inv.v_sm_rojo, 1)], 100, segundos=60)
    temprano = op_venta([(inv.v_sm_rojo, 1)], 100, segundos=-60)
    resultados = sincronizar_ok(client, inv.h_cajero, tarde, temprano)  # llegan en el orden contrario
    assert [r["estado"] for r in resultados] == ["EN_CONFLICTO", "CONFIRMADA"]  # los resultados salen en el orden del lote; la unidad fue de la más antigua
    assert _centro(client, inv)["vendida"] == 1


def test_09_cada_operacion_es_independiente_en_un_lote(inv, mundo, client):
    stock_listo(inv, mundo)
    buena, mala, otra = op_venta([(inv.v_sm_rojo, 1)], 100, segundos=-3), op_venta([(inv.v_sm_rojo, 1)], 10, segundos=-2), op_venta([(inv.var[("M", "Azul")], 1)], 100, segundos=-1)
    r = sincronizar_ok(client, inv.h_cajero, buena, mala, otra)
    assert [x["estado"] for x in r] == ["CONFIRMADA", "RECHAZADA", "CONFIRMADA"]
    assert _centro(client, inv)["vendida"] == 1 and _centro(client, inv, inv.var[("M", "Azul")])["vendida"] == 1


def test_10_un_fallo_del_servidor_no_deja_nada_a_medias_y_se_reintenta(inv, mundo, client, db, monkeypatch):
    from app.primer_parcial.ventas.publico import CobroCajaService
    stock_listo(inv, mundo)
    op = op_venta([(inv.v_sm_rojo, 2)], 200)
    original = CobroCajaService.cobrar
    monkeypatch.setattr(CobroCajaService, "cobrar", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("falla pasajera")))
    r = sincronizar_ok(client, inv.h_cajero, op)[0]
    assert r["estado"] == "ERROR" and "se reintentará" in r["mensaje"]
    assert contar(db, "pedidos") == 0 and contar(db, "operaciones_offline") == 0 and _centro(client, inv)["vendida"] == 0  # RNF04, RNF06: nada a medias y el cliente la conserva
    monkeypatch.setattr(CobroCajaService, "cobrar", original)
    assert sincronizar_ok(client, inv.h_cajero, op)[0]["estado"] == "CONFIRMADA"  # el reintento sí la procesa, una sola vez
    assert contar(db, "pedidos") == 1


def test_11_plan_suscripcion_y_aislamiento(inv, mundo, tienda_b, db, client):
    stock_listo(inv, mundo)
    op = op_venta([(inv.v_sm_rojo, 1)], 100)
    sincronizar_ok(client, inv.h_cajero, op)
    assert client.get("/api/offline/operaciones", headers=tienda_b.h_admin).status_code == 403  # el Administrador no sincroniza
    mundo.basico.offline = False
    db.commit()
    r = sincronizar(client, inv.h_cajero, op_venta([(inv.v_sm_rojo, 1)], 100))
    assert r.status_code == 403 and r.json()["detail"] == "Su plan no incluye esta funcionalidad. Cambie al plan Profesional."
    mundo.basico.offline = True
    db.execute(text("UPDATE suscripciones SET estado = 'VENCIDA' WHERE empresa_id = :e"), {"e": mundo.a.id})
    db.commit()
    assert sincronizar(client, inv.h_cajero, op_venta([(inv.v_sm_rojo, 1)], 100)).status_code == 403
    assert client.get("/api/offline/operaciones", headers=inv.h_cajero).status_code == 403

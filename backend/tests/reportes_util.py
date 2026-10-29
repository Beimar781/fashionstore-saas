"""Ayudas de las pruebas de la Fase G (reportes, indicadores, IA y plan)."""
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import text

from app.core.tiempo import ahora
from app.primer_parcial.ventas.models import Pedido, PedidoItem
from tests.caja_util import vender
from tests.compras_util import SIN_FONDOS, TIMEOUT, agregar_ok, checkout_ok, comprar, pagar, stock_listo
from tests.devoluciones_util import devolver_ok, venta_con_tarjeta
from tests.reservas_util import reserva_ok


def con_ia(db, mundo):
    """Pasa el plan Básico de EMP-A al plan con IA (por defecto solo EMP-B, Profesional, la tiene)."""
    mundo.basico.reportes_ia = True
    db.commit()


def sin_reportes(db, mundo):
    mundo.basico.reportes_convencionales = False
    db.commit()


def movimiento(client, inv, mundo):
    """EMP-A, sucursal Centro: venta en efectivo Bs 200 y con tarjeta Bs 100 en caja, compra digital de Bs 300 con tarjeta, una devolución de Bs 100 (efectivo),
    un pago rechazado y otro pendiente de confirmación, una reserva completada y otra pendiente. Devuelve los pedidos pagados."""
    stock_listo(inv, mundo)
    a = vender(client, inv.h_cajero, (inv.v_sm_rojo, 2), recibido=250)["pedido"]  # Bs 200 en efectivo
    b = venta_con_tarjeta(client, inv, (inv.var[("M", "Azul")], 1))  # Bs 100 con tarjeta en caja
    d = comprar(client, inv.h_cliente, inv, inv.v_sm_rojo, 3)  # Bs 300 digital con tarjeta
    devolver_ok(client, inv.h_cajero, a["comprobante_numero"], [(a["items"][0], 1)])  # devuelve Bs 100 en efectivo
    agregar_ok(client, inv.h_cliente, inv.var[("S", "Azul")], inv.centro, 1)
    pendiente = checkout_ok(client, inv.h_cliente)
    assert pagar(client, inv.h_cliente, pendiente["id"], SIN_FONDOS).status_code == 402  # pago rechazado
    assert pagar(client, inv.h_cliente, pendiente["id"], TIMEOUT).json()["pendiente"] is True  # pago pendiente de confirmación
    res = reserva_ok(client, inv.h_cliente, inv.centro, (inv.var[("M", "Rojo")], 1))
    client.post(f"/api/atencion-reservas/{res['id']}/atender", headers=inv.h_enc_centro)
    client.post(f"/api/atencion-reservas/{res['id']}/completar", json={"llevara_prendas": False}, headers=inv.h_enc_centro)
    reserva_ok(client, inv.h_cliente, inv.centro, (inv.var[("M", "Rojo")], 1), dias=2)
    return a, b, d


def envejecer(db, pedido_id, dias):
    db.execute(text("UPDATE pedidos SET pagado_en = pagado_en - make_interval(days => :d) WHERE id = :i"), {"d": dias, "i": pedido_id})
    db.commit()


def historial_semanal(db, inv, mundo, unidades_por_semana: list[int], variante=None):
    """Ventas históricas de la camisa: una venta pagada por semana (la primera cantidad es la de hace más semanas). Inserta directo en la base."""
    variante = variante or inv.v_sm_rojo
    for i, unidades in enumerate(reversed(unidades_por_semana)):
        momento = ahora() - timedelta(days=7 * i + 1)
        precio = Decimal("100.00")
        pedido = Pedido(
            empresa_id=mundo.a.id, codigo=f"HIST{i:04d}", sucursal_id=inv.centro.id, canal="PRESENCIAL", tipo_entrega="EN_TIENDA", estado="PAGADO",
            subtotal=precio * unidades, total=precio * unidades, pagado_en=momento,
        )
        pedido.items.append(PedidoItem(
            empresa_id=mundo.a.id, variante_id=variante["id"], sku=variante["sku"], producto="Camisa Oxford", talla="S", color="Rojo", cantidad=unidades,
            precio_unitario=precio, precio_final=precio, subtotal=precio * unidades,
        ))
        db.add(pedido)
    db.commit()

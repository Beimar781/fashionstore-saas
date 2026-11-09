"""Prompt R · A11: el historial de demostración es de 3 meses, por sucursal, idempotente y no toca lo existente."""
from sqlalchemy import func, select, text

from app import demo_historial
from app.primer_parcial.ventas.models import Pedido
from tests.compras_util import stock_listo


def test_genera_tres_meses_por_sucursal_marcado_y_es_idempotente(inv, mundo, db, client):
    stock_listo(inv, mundo)
    antes = db.scalar(select(func.count(Pedido.id)))
    primera = demo_historial.generar(db)
    creados = sum(primera.values())
    assert creados > 50 and any(k.endswith(inv.centro.nombre) for k in primera) and any(k.endswith(inv.norte.nombre) for k in primera)
    assert db.scalar(select(func.count(Pedido.id))) == antes + creados
    assert db.scalar(select(func.count(Pedido.id)).where(Pedido.codigo.like("DEMO-%"))) == creados  # todo marcado como demostración
    dias = db.execute(text("SELECT (max(pagado_en)::date - min(pagado_en)::date) FROM pedidos WHERE codigo LIKE 'DEMO-%'")).scalar()
    assert 60 <= dias <= 90
    segunda = demo_historial.generar(db)
    assert sum(segunda.values()) == 0 and db.scalar(select(func.count(Pedido.id))) == antes + creados


def test_las_ventas_de_demostracion_aparecen_en_los_reportes_por_sucursal(inv, mundo, db, client):
    from datetime import date, timedelta

    stock_listo(inv, mundo)
    demo_historial.generar(db)
    r = client.get(f"/api/reportes/ventas?desde={date.today() - timedelta(days=90)}", headers=inv.h_admin)
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["totales"]["ventas"] > 50 and {s["sucursal"] for s in cuerpo["por_sucursal"]} == {inv.centro.nombre, inv.norte.nombre}

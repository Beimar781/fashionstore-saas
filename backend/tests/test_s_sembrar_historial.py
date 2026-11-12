"""Script scripts/sembrar_historial_demo.py: siembra marcada, sin tocar el inventario, idempotente, borrable y limitada a una empresa."""
import importlib.util
from datetime import timedelta
from pathlib import Path

from sqlalchemy import func, select

from app.core.tiempo import ahora
from app.modules.inventario.models import Existencia
from app.modules.plataforma.models import Empresa
from app.primer_parcial.ventas.models import Pago, Pedido, PedidoItem, SecuenciaComprobante
from tests.compras_util import stock_listo

RUTA = Path(__file__).resolve().parents[2] / "scripts" / "sembrar_historial_demo.py"
_spec = importlib.util.spec_from_file_location("sembrar_historial_demo", RUTA)
script = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(script)


def _empresa(db, mundo) -> Empresa:
    return db.scalar(select(Empresa).where(Empresa.id == mundo.a.id))


def test_01_siembra_60_a_90_ventas_marcadas_con_fechas_pasadas_y_totales_coherentes(inv, mundo, db):
    stock_listo(inv, mundo)
    empresa = _empresa(db, mundo)
    antes = script._existencias(db, empresa.id)
    ventas = script.planear(db, empresa)
    assert 60 <= len(ventas) <= 90
    script.aplicar(db, empresa, ventas)
    db.flush()
    pedidos = list(db.scalars(select(Pedido).where(Pedido.empresa_id == empresa.id, Pedido.codigo.like("DH-%")).order_by(Pedido.pagado_en)))
    assert len(pedidos) == len(ventas) and all(p.estado == "PAGADO" and p.comprobante_numero.startswith("CMP-") for p in pedidos)
    assert max(p.pagado_en for p in pedidos) <= ahora() - timedelta(days=2) and min(p.pagado_en for p in pedidos) >= ahora() - timedelta(days=121)
    antiguas = sum(1 for p in pedidos if p.pagado_en < ahora() - timedelta(days=90))
    assert 0 < antiguas < len(pedidos)                                   # hay ventas de más de 3 meses y de los últimos 3 meses
    assert {p.sucursal_id for p in pedidos} == {inv.centro.id, inv.norte.id}
    for p in pedidos:
        assert p.total == sum(i.subtotal for i in p.items) and p.iva_incluido == script.iva_incluido(p.total)
    pagos = list(db.scalars(select(Pago).where(Pago.referencia_externa.like("demo-hist-%"))))
    assert len(pagos) == len(pedidos) and {g.metodo for g in pagos} <= {"EFECTIVO", "QR", "TARJETA"} and len({g.metodo for g in pagos}) >= 2
    assert script._existencias(db, empresa.id) == antes                  # el inventario no cambió


def test_02_comprobantes_correlativos_por_sucursal_y_ranking_distinto(inv, mundo, db):
    stock_listo(inv, mundo)
    empresa = _empresa(db, mundo)
    script.aplicar(db, empresa, script.planear(db, empresa))
    db.flush()
    for suc in (inv.centro, inv.norte):
        numeros = [int(c.split("-")[2]) for c in db.scalars(select(Pedido.comprobante_numero).where(Pedido.empresa_id == empresa.id, Pedido.sucursal_id == suc.id).order_by(Pedido.pagado_en))]
        assert numeros == list(range(1, len(numeros) + 1))              # sin saltos ni repetidos, en orden de fecha
        assert db.scalar(select(SecuenciaComprobante.ultimo).where(SecuenciaComprobante.sucursal_id == suc.id)) == len(numeros)


def test_03_borrar_elimina_solo_lo_sembrado_y_no_toca_otra_empresa(inv, mundo, tienda_b, db):
    stock_listo(inv, mundo)
    empresa = _empresa(db, mundo)
    pedidos_antes = db.scalar(select(func.count(Pedido.id)))
    script.aplicar(db, empresa, script.planear(db, empresa))
    db.flush()
    assert db.scalar(select(func.count(Pedido.id)).where(Pedido.empresa_id == mundo.b.id)) == 0   # EMP-B de la prueba no recibió nada
    eliminadas = script.borrar(db, empresa)
    assert eliminadas > 0 and db.scalar(select(func.count(Pedido.id))) == pedidos_antes
    assert db.scalar(select(func.count(PedidoItem.id))) == 0 and db.scalar(select(func.count(Pago.id))) == 0
    assert script.borrar(db, empresa) == 0                                # borrar dos veces no falla


def test_04_el_resumen_muestra_ventas_por_sucursal_por_mes_y_top_5(inv, mundo, db):
    stock_listo(inv, mundo)
    empresa = _empresa(db, mundo)
    texto = script.resumen(db, empresa, script.planear(db, empresa))
    assert "Ventas por sucursal:" in texto and "Ventas por mes:" in texto and "Top 5 por sucursal" in texto and "Centro" in texto and "Norte" in texto


def test_05_por_defecto_solo_apunta_a_emp_b():
    assert script.EMPRESA_POR_DEFECTO == "EMP-B"


def test_06_el_script_carga_solo_todos_los_modelos_sin_otros_imports():
    """Ejecutado como script (sin la app ni las pruebas) debe poder resolver todas las claves foráneas; si faltan modelos, el flush falla con NoReferencedTableError."""
    import subprocess
    import sys

    codigo = (
        "import importlib.util, sys; "
        f"s = importlib.util.spec_from_file_location('sembrar', r'{RUTA}'); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); "
        "from sqlalchemy.orm import configure_mappers; configure_mappers(); "
        "[fk.column for t in m.Pedido.metadata.sorted_tables for fk in t.foreign_keys]; "
        "[fk.column for fk in m.Pedido.__table__.foreign_keys]; print('OK')"
    )
    r = subprocess.run([sys.executable, "-c", codigo], capture_output=True, text=True, cwd=RUTA.parents[1] / "backend", timeout=120)
    assert r.returncode == 0 and "OK" in r.stdout, r.stderr[-600:]

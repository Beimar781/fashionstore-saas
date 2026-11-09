"""Prompt R · A9 (RNF09): las consultas críticas usan índices. Con pocos datos Postgres prefiere recorrer la tabla, así que se apaga ese plan
para comprobar que existe un índice utilizable para cada consulta."""
import pytest
from sqlalchemy import text

CONSULTAS = {
    "catálogo por empresa y categoría": "SELECT id FROM productos WHERE empresa_id = 1 AND activo AND categoria_id = 1",
    "existencias por sucursal": "SELECT variante_id FROM existencias WHERE empresa_id = 1 AND sucursal_id = 1",
    "ventas pagadas por fecha y sucursal": "SELECT id FROM pedidos WHERE empresa_id = 1 AND estado = 'PAGADO' AND sucursal_id = 1 AND pagado_en >= now() - interval '90 days'",
    "líneas de un pedido": "SELECT id FROM pedido_items WHERE empresa_id = 1 AND pedido_id = 1",
    "bitácora por empresa y fecha": "SELECT id FROM bitacora WHERE empresa_id = 1 ORDER BY creado_en DESC LIMIT 20",
    "bitácora por usuario": "SELECT id FROM bitacora WHERE empresa_id = 1 AND usuario_id = 1 ORDER BY creado_en DESC LIMIT 20",
    "reservas de una sucursal": "SELECT id FROM reservas WHERE empresa_id = 1 AND sucursal_id = 1 AND estado = 'PENDIENTE'",
    "operaciones offline del usuario": "SELECT id FROM operaciones_offline WHERE empresa_id = 1 AND usuario_id = 1 ORDER BY recibida_en DESC",
}


@pytest.mark.parametrize("nombre", list(CONSULTAS))
def test_la_consulta_critica_tiene_un_indice_utilizable(nombre, db):
    db.execute(text("SET LOCAL enable_seqscan = off"))
    plan = "\n".join(f[0] for f in db.execute(text("EXPLAIN " + CONSULTAS[nombre])))
    assert "Index" in plan or "Bitmap" in plan, f"{nombre}:\n{plan}"

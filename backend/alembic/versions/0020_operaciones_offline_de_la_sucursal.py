"""Prompt R (B3, B5, B6): la cola offline admite DEVOLUCION, RECEPCION y AJUSTE_INVENTARIO (regla 14: se amplía el CHECK).

Revision ID: 0020
Revises: 0019
"""
from alembic import op

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None

NUEVOS = "'VENTA_CONTADO','RESERVA','COMPRA','CANCELAR_RESERVA','DEVOLUCION','RECEPCION','AJUSTE_INVENTARIO'"
ANTERIORES = "'VENTA_CONTADO','RESERVA','COMPRA','CANCELAR_RESERVA'"


def upgrade() -> None:
    op.execute("ALTER TABLE operaciones_offline DROP CONSTRAINT IF EXISTS operaciones_offline_tipo_check")
    op.execute(f"ALTER TABLE operaciones_offline ADD CONSTRAINT operaciones_offline_tipo_check CHECK (tipo IN ({NUEVOS}))")


def downgrade() -> None:
    op.execute("DELETE FROM operaciones_offline WHERE tipo IN ('DEVOLUCION','RECEPCION','AJUSTE_INVENTARIO')")
    op.execute("ALTER TABLE operaciones_offline DROP CONSTRAINT IF EXISTS operaciones_offline_tipo_check")
    op.execute(f"ALTER TABLE operaciones_offline ADD CONSTRAINT operaciones_offline_tipo_check CHECK (tipo IN ({ANTERIORES}))")

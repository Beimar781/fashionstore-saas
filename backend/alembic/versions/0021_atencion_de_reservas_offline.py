"""Prompt R (B4): la cola offline admite PREPARAR_RESERVA, PRENDA_NO_ENCONTRADA y ATENDER_RESERVA (regla 14: se amplía el CHECK).

Revision ID: 0021
Revises: 0020
"""
from alembic import op

revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None

NUEVOS = "'VENTA_CONTADO','RESERVA','COMPRA','CANCELAR_RESERVA','DEVOLUCION','RECEPCION','AJUSTE_INVENTARIO','PREPARAR_RESERVA','PRENDA_NO_ENCONTRADA','ATENDER_RESERVA'"
ANTERIORES = "'VENTA_CONTADO','RESERVA','COMPRA','CANCELAR_RESERVA','DEVOLUCION','RECEPCION','AJUSTE_INVENTARIO'"


def upgrade() -> None:
    op.execute("ALTER TABLE operaciones_offline ALTER COLUMN tipo TYPE VARCHAR(24)")
    op.execute("ALTER TABLE operaciones_offline DROP CONSTRAINT IF EXISTS operaciones_offline_tipo_check")
    op.execute(f"ALTER TABLE operaciones_offline ADD CONSTRAINT operaciones_offline_tipo_check CHECK (tipo IN ({NUEVOS}))")


def downgrade() -> None:
    op.execute("DELETE FROM operaciones_offline WHERE tipo IN ('PREPARAR_RESERVA','PRENDA_NO_ENCONTRADA','ATENDER_RESERVA')")
    op.execute("ALTER TABLE operaciones_offline DROP CONSTRAINT IF EXISTS operaciones_offline_tipo_check")
    op.execute(f"ALTER TABLE operaciones_offline ADD CONSTRAINT operaciones_offline_tipo_check CHECK (tipo IN ({ANTERIORES}))")
    op.execute("ALTER TABLE operaciones_offline ALTER COLUMN tipo TYPE VARCHAR(20)")

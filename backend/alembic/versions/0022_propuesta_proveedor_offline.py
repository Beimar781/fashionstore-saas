"""Prompt R (B9): la cola offline admite PROPUESTA_PROVEEDOR, que no pertenece a una sucursal (regla 14: se amplía el CHECK y la sucursal puede ser nula).

Revision ID: 0022
Revises: 0021
"""
from alembic import op

revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None

NUEVOS = "'VENTA_CONTADO','RESERVA','COMPRA','CANCELAR_RESERVA','DEVOLUCION','RECEPCION','AJUSTE_INVENTARIO','PREPARAR_RESERVA','PRENDA_NO_ENCONTRADA','ATENDER_RESERVA','PROPUESTA_PROVEEDOR'"
ANTERIORES = "'VENTA_CONTADO','RESERVA','COMPRA','CANCELAR_RESERVA','DEVOLUCION','RECEPCION','AJUSTE_INVENTARIO','PREPARAR_RESERVA','PRENDA_NO_ENCONTRADA','ATENDER_RESERVA'"


def upgrade() -> None:
    op.execute("ALTER TABLE operaciones_offline ALTER COLUMN tipo TYPE VARCHAR(24)")
    op.execute("ALTER TABLE operaciones_offline ALTER COLUMN sucursal_id DROP NOT NULL")
    op.execute("ALTER TABLE operaciones_offline DROP CONSTRAINT IF EXISTS operaciones_offline_tipo_check")
    op.execute(f"ALTER TABLE operaciones_offline ADD CONSTRAINT operaciones_offline_tipo_check CHECK (tipo IN ({NUEVOS}))")


def downgrade() -> None:
    op.execute("DELETE FROM operaciones_offline WHERE tipo = 'PROPUESTA_PROVEEDOR'")
    op.execute("ALTER TABLE operaciones_offline DROP CONSTRAINT IF EXISTS operaciones_offline_tipo_check")
    op.execute(f"ALTER TABLE operaciones_offline ADD CONSTRAINT operaciones_offline_tipo_check CHECK (tipo IN ({ANTERIORES}))")
    op.execute("ALTER TABLE operaciones_offline ALTER COLUMN sucursal_id SET NOT NULL")

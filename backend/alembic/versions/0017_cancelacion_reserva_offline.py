"""Fase Q: agrega cancelación offline de reservas a la cola.

Revision ID: 0017
Revises: 0016
"""
from alembic import op

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE operaciones_offline ALTER COLUMN tipo TYPE VARCHAR(20)")
    op.execute("ALTER TABLE operaciones_offline DROP CONSTRAINT IF EXISTS operaciones_offline_tipo_check")
    op.execute("ALTER TABLE operaciones_offline ADD CONSTRAINT operaciones_offline_tipo_check CHECK (tipo IN ('VENTA_CONTADO','RESERVA','COMPRA','CANCELAR_RESERVA'))")


def downgrade() -> None:
    op.execute("DELETE FROM operaciones_offline WHERE tipo = 'CANCELAR_RESERVA'")
    op.execute("ALTER TABLE operaciones_offline DROP CONSTRAINT IF EXISTS operaciones_offline_tipo_check")
    op.execute("ALTER TABLE operaciones_offline ADD CONSTRAINT operaciones_offline_tipo_check CHECK (tipo IN ('VENTA_CONTADO','RESERVA','COMPRA'))")
    op.execute("ALTER TABLE operaciones_offline ALTER COLUMN tipo TYPE VARCHAR(14)")

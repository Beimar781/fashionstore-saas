"""Fase Q: fusión idempotente del carrito descargado.

Revision ID: 0016
Revises: 0015
"""
from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE carritos ADD COLUMN IF NOT EXISTS ultima_fusion_id VARCHAR(36)")


def downgrade() -> None:
    op.execute("ALTER TABLE carritos DROP COLUMN IF EXISTS ultima_fusion_id")

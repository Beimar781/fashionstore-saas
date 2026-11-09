"""Prompt R (A4): guarda el desfase entre el reloj del dispositivo y el del servidor en cada operación offline.

Revision ID: 0018
Revises: 0017
"""
from alembic import op

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE operaciones_offline ADD COLUMN IF NOT EXISTS desfase_reloj_segundos INTEGER")


def downgrade() -> None:
    op.execute("ALTER TABLE operaciones_offline DROP COLUMN IF EXISTS desfase_reloj_segundos")

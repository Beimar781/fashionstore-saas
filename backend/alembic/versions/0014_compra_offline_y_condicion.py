"""Fase K · Compra del cliente sin conexión y condición de la prenda devuelta.

Revision ID: 0014
Revises: 0013
"""
from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None

SQL_UP = """
-- Regla 14: el tipo de operación offline gana «COMPRA» (pedido por pagar del cliente, armado sin conexión)
ALTER TABLE operaciones_offline DROP CONSTRAINT IF EXISTS operaciones_offline_tipo_check;
ALTER TABLE operaciones_offline ADD CONSTRAINT operaciones_offline_tipo_check CHECK (tipo IN ('VENTA_CONTADO','RESERVA','COMPRA'));

-- RN15: al devolver o cambiar se verifica que la prenda no tenga daños ni desgaste y conserve sus etiquetas (las notas anteriores se consideran verificadas)
ALTER TABLE devoluciones ADD COLUMN sin_danos BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE devoluciones ADD COLUMN sin_desgaste BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE devoluciones ADD COLUMN con_etiquetas BOOLEAN NOT NULL DEFAULT TRUE;
"""


def upgrade() -> None:
    op.execute(SQL_UP)


def downgrade() -> None:
    for columna in ("con_etiquetas", "sin_desgaste", "sin_danos"):
        op.execute(f"ALTER TABLE devoluciones DROP COLUMN IF EXISTS {columna}")
    op.execute("DELETE FROM operaciones_offline WHERE tipo = 'COMPRA'")
    op.execute("ALTER TABLE operaciones_offline DROP CONSTRAINT IF EXISTS operaciones_offline_tipo_check")
    op.execute("ALTER TABLE operaciones_offline ADD CONSTRAINT operaciones_offline_tipo_check CHECK (tipo IN ('VENTA_CONTADO','RESERVA'))")

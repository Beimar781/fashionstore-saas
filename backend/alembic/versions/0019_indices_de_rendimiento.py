"""Prompt R (A9): índices que faltaban en consultas críticas (existencias por sucursal, líneas de pedido, bitácora por usuario).

Revision ID: 0019
Revises: 0018
"""
from alembic import op

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE INDEX IF NOT EXISTS ix_existencias_sucursal ON existencias (empresa_id, sucursal_id, variante_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_pedido_items_pedido ON pedido_items (empresa_id, pedido_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_bitacora_usuario ON bitacora (empresa_id, usuario_id, creado_en DESC)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_bitacora_usuario")
    op.execute("DROP INDEX IF EXISTS ix_pedido_items_pedido")
    op.execute("DROP INDEX IF EXISTS ix_existencias_sucursal")

"""CU-02 · Recuperación de contraseña (enlace por correo de un solo uso).

Revision ID: 0002
Revises: 0001
"""
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE restablecimientos_password (
            id BIGSERIAL PRIMARY KEY,
            usuario_id BIGINT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
            token_hash VARCHAR(64) NOT NULL UNIQUE,
            expira_en TIMESTAMPTZ NOT NULL,
            usado BOOLEAN NOT NULL DEFAULT FALSE,
            creado_en TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX ix_restab_usuario ON restablecimientos_password (usuario_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS restablecimientos_password CASCADE")

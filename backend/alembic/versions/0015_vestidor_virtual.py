"""CU-06 · Vestidor virtual: la imagen PNG (con fondo transparente) de cada prenda superior por color, y sus puntos de anclaje.

Revision ID: 0015
Revises: 0014
"""
from alembic import op

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None

SQL_UP = """
-- Un recurso por producto y color (la talla solo cambia la escala). El PNG se guarda en la carpeta de imágenes de la empresa.
CREATE TABLE ar_assets (
    id BIGSERIAL PRIMARY KEY,
    empresa_id BIGINT NOT NULL REFERENCES empresas(id),
    producto_id BIGINT NOT NULL REFERENCES productos(id) ON DELETE CASCADE,
    color_id BIGINT NOT NULL REFERENCES colores(id),
    ruta VARCHAR(300) NOT NULL,
    ancho INTEGER NOT NULL,
    alto INTEGER NOT NULL,
    anclaje JSONB NOT NULL,
    actualizado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (empresa_id, producto_id, color_id)
);
CREATE INDEX ix_ar_assets_producto ON ar_assets (empresa_id, producto_id);
"""


def upgrade() -> None:
    op.execute(SQL_UP)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS ar_assets CASCADE")

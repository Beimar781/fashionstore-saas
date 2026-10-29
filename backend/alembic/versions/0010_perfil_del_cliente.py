"""Fase G (ajuste) · Perfil de gustos del cliente para el recomendador (CU-07): búsquedas, prendas vistas y preferencia de personalización.

Revision ID: 0010
Revises: 0009
"""
from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None

SQL_UP = """
-- lo que el cliente busca, mira o le pide al asistente: con esto se arma su perfil de gustos
CREATE TABLE interacciones_cliente (
    id BIGSERIAL PRIMARY KEY,
    empresa_id BIGINT NOT NULL REFERENCES empresas(id),
    cliente_id BIGINT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    tipo VARCHAR(10) NOT NULL CHECK (tipo IN ('BUSQUEDA','VISTA','ASISTENTE')),
    texto VARCHAR(120),
    producto_id BIGINT REFERENCES productos(id) ON DELETE CASCADE,
    categoria_id BIGINT REFERENCES categorias(id) ON DELETE SET NULL,
    color_id BIGINT REFERENCES colores(id) ON DELETE SET NULL,
    talla VARCHAR(8),
    precio_max NUMERIC(10,2),
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_interacciones_cliente ON interacciones_cliente (empresa_id, cliente_id, creado_en DESC);

-- el cliente decide si el sistema aprende de lo que hace (por defecto, sí) y puede borrar su historial
CREATE TABLE preferencias_cliente (
    cliente_id BIGINT PRIMARY KEY REFERENCES usuarios(id) ON DELETE CASCADE,
    empresa_id BIGINT NOT NULL REFERENCES empresas(id),
    personalizar BOOLEAN NOT NULL DEFAULT TRUE
);
"""


def upgrade() -> None:
    op.execute(SQL_UP)


def downgrade() -> None:
    for tabla in ("preferencias_cliente", "interacciones_cliente"):
        op.execute(f"DROP TABLE IF EXISTS {tabla} CASCADE")

"""Fase G · Reportes generativos (CU-23) y registro del uso de la IA (CU-07, CU-23, CU-42, CU-36).

Revision ID: 0009
Revises: 0008
"""
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None

SQL_UP = """
-- cada reporte generativo queda registrado: qué pidió el Administrador, cómo se interpretó y qué resultó
CREATE TABLE reportes_generados (
    id BIGSERIAL PRIMARY KEY,
    empresa_id BIGINT NOT NULL REFERENCES empresas(id),
    usuario_id BIGINT NOT NULL REFERENCES usuarios(id),
    prompt VARCHAR(500) NOT NULL,
    especificacion JSONB NOT NULL,
    resultado JSONB NOT NULL,
    origen VARCHAR(10) NOT NULL CHECK (origen IN ('IA','REGLAS')),   -- IA externa o modo de respaldo
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_reportes_generados_empresa ON reportes_generados (empresa_id, creado_en DESC);

-- uso de las funciones de IA por empresa (CU-36 lo muestra como consumo del plan)
CREATE TABLE uso_ia (
    id BIGSERIAL PRIMARY KEY,
    empresa_id BIGINT NOT NULL REFERENCES empresas(id),
    usuario_id BIGINT REFERENCES usuarios(id),
    funcion VARCHAR(12) NOT NULL CHECK (funcion IN ('REPORTE','ASISTENTE','ANALITICA')),
    origen VARCHAR(10) NOT NULL CHECK (origen IN ('IA','REGLAS')),
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_uso_ia_empresa ON uso_ia (empresa_id, creado_en DESC);
"""


def upgrade() -> None:
    op.execute(SQL_UP)


def downgrade() -> None:
    for tabla in ("uso_ia", "reportes_generados"):
        op.execute(f"DROP TABLE IF EXISTS {tabla} CASCADE")

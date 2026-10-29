"""Fase J · Bitácora del sistema: registro de inicios y cierres de sesión y de toda operación de escritura (función transversal, sin caso de uso).

Revision ID: 0012
Revises: 0011
"""
from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None

SQL_UP = """
-- Quién hizo qué y cuándo. empresa_id vacío = operación de la plataforma (SuperAdministrador) o intento de ingreso sin empresa conocida.
-- No lleva clave foránea a usuarios: el nombre se guarda tal como estaba en ese momento y el registro nunca cambia.
CREATE TABLE bitacora (
    id BIGSERIAL PRIMARY KEY,
    empresa_id BIGINT REFERENCES empresas(id),
    usuario_id BIGINT,
    usuario VARCHAR(150) NOT NULL,
    rol VARCHAR(30),
    accion VARCHAR(30) NOT NULL,
    entidad VARCHAR(40) NOT NULL,
    entidad_id BIGINT,
    detalle VARCHAR(400) NOT NULL,
    ip VARCHAR(45),
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_bitacora_empresa ON bitacora (empresa_id, creado_en DESC);
CREATE INDEX ix_bitacora_fecha ON bitacora (creado_en DESC);

-- La bitácora solo se agrega: ni la aplicación ni nadie con acceso a la tabla puede editar o borrar una fila.
CREATE FUNCTION bitacora_inmutable() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'La bitácora no se puede modificar ni borrar.';
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER bitacora_sin_cambios BEFORE UPDATE OR DELETE ON bitacora FOR EACH ROW EXECUTE FUNCTION bitacora_inmutable();
"""


def upgrade() -> None:
    op.execute(SQL_UP)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS bitacora CASCADE")
    op.execute("DROP FUNCTION IF EXISTS bitacora_inmutable()")

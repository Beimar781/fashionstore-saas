"""Fase K · Ajustes de la clase del 29/10: plan de prueba gratuita y avisos push (dispositivos y envíos).

Revision ID: 0013
Revises: 0012
"""
from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None

SQL_UP = """
-- Tercer plan: «Prueba gratuita» (un mes, una sola vez por empresa). Se reconoce por este campo, no por su nombre.
ALTER TABLE planes ADD COLUMN es_prueba BOOLEAN NOT NULL DEFAULT FALSE;

-- Dispositivos donde un usuario recibe avisos push: un navegador (suscripción Web Push) o un móvil (token de FCM o identificador local en modo simulado)
CREATE TABLE dispositivos (
    id BIGSERIAL PRIMARY KEY,
    empresa_id BIGINT NOT NULL REFERENCES empresas(id),
    usuario_id BIGINT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    canal VARCHAR(5) NOT NULL CHECK (canal IN ('WEB','MOVIL')),
    token TEXT NOT NULL,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (usuario_id, canal, token)
);
CREATE INDEX ix_dispositivos_usuario ON dispositivos (empresa_id, usuario_id) WHERE activo;

-- Qué pasó con cada intento de push (regla 17: un fallo se registra, nunca deshace la operación que lo originó)
CREATE TABLE push_envios (
    id BIGSERIAL PRIMARY KEY,
    empresa_id BIGINT NOT NULL REFERENCES empresas(id),
    usuario_id BIGINT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    dispositivo_id BIGINT REFERENCES dispositivos(id) ON DELETE SET NULL,
    canal VARCHAR(5) NOT NULL CHECK (canal IN ('WEB','MOVIL')),
    estado VARCHAR(10) NOT NULL CHECK (estado IN ('ENVIADO','SIMULADO','FALLIDO')),
    titulo VARCHAR(200) NOT NULL,
    error VARCHAR(300),
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_push_envios_usuario ON push_envios (empresa_id, usuario_id, creado_en DESC);
"""


def upgrade() -> None:
    op.execute(SQL_UP)


def downgrade() -> None:
    for tabla in ("push_envios", "dispositivos"):
        op.execute(f"DROP TABLE IF EXISTS {tabla} CASCADE")
    op.execute("ALTER TABLE planes DROP COLUMN IF EXISTS es_prueba")

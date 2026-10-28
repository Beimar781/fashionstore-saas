"""Fase C · Reservas del cliente (CU-09, CU-10), atención en la sucursal (CU-24, CU-25) y notificaciones (RF11).

Revision ID: 0005
Revises: 0004
"""
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

SQL_UP = """
CREATE TABLE reservas (
    id BIGSERIAL PRIMARY KEY,
    empresa_id BIGINT NOT NULL REFERENCES empresas(id),
    codigo VARCHAR(16) NOT NULL,                       -- código que el cliente presenta en el mostrador
    cliente_id BIGINT NOT NULL REFERENCES usuarios(id),
    sucursal_id BIGINT NOT NULL REFERENCES sucursales(id),
    programada_para TIMESTAMPTZ NOT NULL,              -- horario aproximado de visita
    vence_en TIMESTAMPTZ NOT NULL,
    estado VARCHAR(12) NOT NULL DEFAULT 'PENDIENTE'
        CHECK (estado IN ('PENDIENTE','PREPARADA','EN_PROBADOR','COMPLETADA','CANCELADA','EXPIRADA')),
    notas VARCHAR(300) NOT NULL DEFAULT '',
    preparada_por BIGINT REFERENCES usuarios(id),
    creada_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    actualizada_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (empresa_id, codigo),
    CHECK (vence_en > programada_para)
);
CREATE INDEX ix_reservas_sucursal ON reservas (empresa_id, sucursal_id, estado, programada_para);
CREATE INDEX ix_reservas_cliente ON reservas (empresa_id, cliente_id, creada_en DESC);
CREATE INDEX ix_reservas_vencimiento ON reservas (empresa_id, estado, vence_en);

CREATE TABLE reserva_items (
    id BIGSERIAL PRIMARY KEY,
    empresa_id BIGINT NOT NULL REFERENCES empresas(id),
    reserva_id BIGINT NOT NULL REFERENCES reservas(id) ON DELETE CASCADE,
    variante_id BIGINT NOT NULL REFERENCES variantes(id),
    cantidad INT NOT NULL CHECK (cantidad > 0),
    estado VARCHAR(14) NOT NULL DEFAULT 'RESERVADO'
        CHECK (estado IN ('RESERVADO','NO_ENCONTRADO','VENDIDO','LIBERADO')),
    UNIQUE (reserva_id, variante_id)
);

-- RF11: avisos para un usuario (cliente) o para toda una sucursal (usuario_id vacío)
CREATE TABLE notificaciones (
    id BIGSERIAL PRIMARY KEY,
    empresa_id BIGINT NOT NULL REFERENCES empresas(id),
    usuario_id BIGINT REFERENCES usuarios(id),
    sucursal_id BIGINT REFERENCES sucursales(id),
    tipo VARCHAR(30) NOT NULL,
    titulo VARCHAR(200) NOT NULL,
    mensaje TEXT NOT NULL,
    referencia_tipo VARCHAR(30) NOT NULL DEFAULT '',
    referencia_id BIGINT,
    leida BOOLEAN NOT NULL DEFAULT FALSE,
    creada_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (usuario_id IS NOT NULL OR sucursal_id IS NOT NULL)
);
CREATE INDEX ix_notif_usuario ON notificaciones (empresa_id, usuario_id, leida, creada_en DESC);
CREATE INDEX ix_notif_sucursal ON notificaciones (empresa_id, sucursal_id, leida, creada_en DESC);
"""


def upgrade() -> None:
    op.execute(SQL_UP)


def downgrade() -> None:
    for tabla in ("notificaciones", "reserva_items", "reservas"):
        op.execute(f"DROP TABLE IF EXISTS {tabla} CASCADE")

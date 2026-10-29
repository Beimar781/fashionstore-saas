"""Fase H · Operación offline y sincronización (CU-37 a CU-40): operaciones recibidas del web y del móvil, con su estado y su resolución.

Revision ID: 0011
Revises: 0010
"""
from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None

SQL_UP = """
-- RN11: toda operación offline trae un identificador único generado en el cliente y queda asociada a empresa, sucursal y usuario.
-- RN12 / RNF05: (empresa, identificador) es único: reenviar una operación ya procesada devuelve el resultado original sin duplicarla.
CREATE TABLE operaciones_offline (
    id BIGSERIAL PRIMARY KEY,
    empresa_id BIGINT NOT NULL REFERENCES empresas(id),
    operacion_id UUID NOT NULL,                       -- generado en el cliente
    usuario_id BIGINT NOT NULL REFERENCES usuarios(id),
    sucursal_id BIGINT NOT NULL REFERENCES sucursales(id),
    tipo VARCHAR(14) NOT NULL CHECK (tipo IN ('VENTA_CONTADO','RESERVA')),
    estado VARCHAR(12) NOT NULL CHECK (estado IN ('CONFIRMADA','RECHAZADA','EN_CONFLICTO')),
    payload JSONB NOT NULL,
    creada_en_cliente TIMESTAMPTZ NOT NULL,
    recibida_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    procesada_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    mensaje VARCHAR(400) NOT NULL DEFAULT '',
    referencia VARCHAR(30),                           -- código del pedido o de la reserva que se creó
    comprobante VARCHAR(30),
    detalle JSONB,                                    -- RN14: qué prendas no alcanzaron (solo en conflicto)
    pedido_id BIGINT REFERENCES pedidos(id),
    reserva_id BIGINT REFERENCES reservas(id),
    intentos INT NOT NULL DEFAULT 1,
    resolucion VARCHAR(12) CHECK (resolucion IN ('REINTENTADA','DESCARTADA')),
    resuelta_por BIGINT REFERENCES usuarios(id),
    resuelta_en TIMESTAMPTZ,
    motivo_resolucion VARCHAR(200),
    UNIQUE (empresa_id, operacion_id)
);
CREATE INDEX ix_operaciones_offline_usuario ON operaciones_offline (empresa_id, usuario_id, recibida_en DESC);
CREATE INDEX ix_operaciones_offline_conflicto ON operaciones_offline (empresa_id, sucursal_id) WHERE estado = 'EN_CONFLICTO';
"""


def upgrade() -> None:
    op.execute(SQL_UP)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS operaciones_offline CASCADE")

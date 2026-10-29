"""Fase E · Punto de venta: consultar productos en caja (CU-28), venta presencial (CU-29), cobro y comprobante (CU-30) y ventas de la sucursal (CU-27).

Revision ID: 0007
Revises: 0006
"""
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None

SQL_UP = """
-- la venta de caja puede nacer de una reserva (sus prendas pasan de reservadas a vendidas al cobrar)
ALTER TABLE pedidos ADD COLUMN reserva_id BIGINT REFERENCES reservas(id);
-- servicio de impuestos (CU-30): FACTURA autorizada o COMPROBANTE INTERNO TEMPORAL si el servicio no responde
ALTER TABLE pedidos ADD COLUMN comprobante_tipo VARCHAR(20)
    CHECK (comprobante_tipo IS NULL OR comprobante_tipo IN ('FACTURA','INTERNO_TEMPORAL'));
ALTER TABLE pedidos ADD COLUMN autorizacion_fiscal VARCHAR(40);
-- una reserva solo puede tener una venta abierta a la vez
CREATE UNIQUE INDEX ux_pedido_reserva_abierto ON pedidos (reserva_id)
    WHERE reserva_id IS NOT NULL AND estado IN ('PENDIENTE_PAGO','PENDIENTE_CONFIRMACION');
CREATE INDEX ix_pedidos_pagados ON pedidos (empresa_id, sucursal_id, canal, pagado_en) WHERE estado = 'PAGADO';

-- efectivo: lo recibido y el cambio entregado (para el arqueo de caja)
ALTER TABLE pagos ADD COLUMN monto_recibido NUMERIC(12,2);
ALTER TABLE pagos ADD COLUMN cambio NUMERIC(12,2);
-- el QR simple local se confirma en caja como el efectivo
ALTER TABLE pagos DROP CONSTRAINT pagos_metodo_check;
ALTER TABLE pagos ADD CONSTRAINT pagos_metodo_check CHECK (metodo IN ('TARJETA','EFECTIVO','QR'));
"""


def upgrade() -> None:
    op.execute(SQL_UP)


def downgrade() -> None:
    op.execute("DELETE FROM pagos WHERE metodo = 'QR'")
    op.execute("ALTER TABLE pagos DROP CONSTRAINT pagos_metodo_check")
    op.execute("ALTER TABLE pagos ADD CONSTRAINT pagos_metodo_check CHECK (metodo IN ('TARJETA','EFECTIVO'))")
    op.execute("ALTER TABLE pagos DROP COLUMN cambio")
    op.execute("ALTER TABLE pagos DROP COLUMN monto_recibido")
    op.execute("DROP INDEX IF EXISTS ix_pedidos_pagados")
    op.execute("DROP INDEX IF EXISTS ux_pedido_reserva_abierto")
    op.execute("ALTER TABLE pedidos DROP COLUMN autorizacion_fiscal")
    op.execute("ALTER TABLE pedidos DROP COLUMN comprobante_tipo")
    op.execute("ALTER TABLE pedidos DROP COLUMN reserva_id")

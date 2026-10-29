"""Fase F · Devoluciones y cambios de prendas (CU-41): notas de devolución, reembolsos y plazo configurable por empresa.

Revision ID: 0008
Revises: 0007
"""
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None

SQL_UP = """
-- RN15: el plazo para devolver o cambiar lo define cada empresa (por defecto, 15 días desde el pago)
CREATE TABLE configuracion_ventas (
    empresa_id BIGINT PRIMARY KEY REFERENCES empresas(id),
    plazo_devolucion_dias INT NOT NULL DEFAULT 15 CHECK (plazo_devolucion_dias BETWEEN 0 AND 365)
);

-- numeración de las notas de devolución por sucursal
CREATE TABLE secuencias_nota_devolucion (
    empresa_id BIGINT NOT NULL REFERENCES empresas(id),
    sucursal_id BIGINT NOT NULL REFERENCES sucursales(id),
    ultimo INT NOT NULL DEFAULT 0,
    PRIMARY KEY (empresa_id, sucursal_id)
);

-- una devolución (o cambio) es una nota que respalda lo que volvió al inventario y el dinero que se movió
CREATE TABLE devoluciones (
    id BIGSERIAL PRIMARY KEY,
    empresa_id BIGINT NOT NULL REFERENCES empresas(id),
    numero VARCHAR(30) NOT NULL,                          -- NDV-<sucursal>-<número>
    pedido_id BIGINT NOT NULL REFERENCES pedidos(id),
    sucursal_id BIGINT NOT NULL REFERENCES sucursales(id),
    tipo VARCHAR(10) NOT NULL CHECK (tipo IN ('DEVOLUCION','CAMBIO')),
    motivo VARCHAR(200) NOT NULL,
    monto_devuelto NUMERIC(12,2) NOT NULL CHECK (monto_devuelto >= 0),
    monto_nuevo NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (monto_nuevo >= 0),          -- prendas entregadas en un cambio
    reembolso NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (reembolso >= 0),              -- dinero que se devuelve al cliente
    cobro_adicional NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (cobro_adicional >= 0),  -- diferencia que paga el cliente en un cambio
    medio_reembolso VARCHAR(10) CHECK (medio_reembolso IN ('TARJETA','EFECTIVO')),
    referencia_reembolso VARCHAR(80),                     -- reembolso en la pasarela
    reembolso_pasarela INT,                               -- centavos reembolsados en la pasarela
    medio_cobro VARCHAR(10) CHECK (medio_cobro IN ('EFECTIVO','TARJETA')),
    monto_recibido NUMERIC(12,2),                         -- efectivo: lo que entregó el cliente
    cambio_entregado NUMERIC(12,2),
    referencia_cobro VARCHAR(80),                         -- diferencia pagada con tarjeta: referencia en la pasarela
    cobro_pasarela INT,                                   -- centavos cobrados en la pasarela
    proveedor_cobro VARCHAR(10),
    cobro_tarjeta_marca VARCHAR(20),
    cobro_tarjeta_ultimos4 VARCHAR(4),
    registrada_por BIGINT REFERENCES usuarios(id),
    creada_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (empresa_id, numero)
);
CREATE INDEX ix_devoluciones_pedido ON devoluciones (empresa_id, pedido_id);
CREATE INDEX ix_devoluciones_sucursal ON devoluciones (empresa_id, sucursal_id, creada_en DESC);

-- intento de cobro con tarjeta de la diferencia de un cambio: el monto lo fija el servidor y se verifica al registrar el cambio
CREATE TABLE intentos_diferencia (
    id BIGSERIAL PRIMARY KEY,
    empresa_id BIGINT NOT NULL REFERENCES empresas(id),
    pedido_id BIGINT NOT NULL REFERENCES pedidos(id),
    usuario_id BIGINT NOT NULL REFERENCES usuarios(id),
    monto NUMERIC(12,2) NOT NULL CHECK (monto > 0),
    proveedor VARCHAR(10) NOT NULL,
    referencia VARCHAR(80) NOT NULL,
    monto_pasarela INT NOT NULL,
    moneda_pasarela VARCHAR(3) NOT NULL,
    estado VARCHAR(12) NOT NULL DEFAULT 'PENDIENTE' CHECK (estado IN ('PENDIENTE','USADO','CANCELADO')),
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (empresa_id, referencia)
);

CREATE TABLE devolucion_items (
    id BIGSERIAL PRIMARY KEY,
    empresa_id BIGINT NOT NULL REFERENCES empresas(id),
    devolucion_id BIGINT NOT NULL REFERENCES devoluciones(id) ON DELETE CASCADE,
    sentido VARCHAR(10) NOT NULL CHECK (sentido IN ('DEVUELTA','ENTREGADA')),
    pedido_item_id BIGINT REFERENCES pedido_items(id),    -- solo en lo devuelto
    variante_id BIGINT NOT NULL REFERENCES variantes(id),
    sku VARCHAR(40) NOT NULL,
    producto VARCHAR(200) NOT NULL,
    talla VARCHAR(8) NOT NULL,
    color VARCHAR(50) NOT NULL,
    cantidad INT NOT NULL CHECK (cantidad > 0),
    precio_final NUMERIC(10,2) NOT NULL,
    subtotal NUMERIC(12,2) NOT NULL
);
CREATE INDEX ix_devolucion_items_pedido_item ON devolucion_items (pedido_item_id) WHERE pedido_item_id IS NOT NULL;
"""


def upgrade() -> None:
    op.execute(SQL_UP)


def downgrade() -> None:
    for tabla in ("intentos_diferencia", "devolucion_items", "devoluciones", "secuencias_nota_devolucion", "configuracion_ventas"):
        op.execute(f"DROP TABLE IF EXISTS {tabla} CASCADE")

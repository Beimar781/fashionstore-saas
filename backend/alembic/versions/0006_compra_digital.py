"""Fase D · Carrito (CU-08), compra digital (CU-11), historial (CU-12) y pago electrónico (CU-32).

Revision ID: 0006
Revises: 0005
"""
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

SQL_UP = """
-- la bitácora de inventario también referencia pedidos (la venta digital descuenta stock al aprobarse el pago)
ALTER TABLE movimientos_inventario DROP CONSTRAINT movimientos_inventario_referencia_tipo_check;
ALTER TABLE movimientos_inventario ADD CONSTRAINT movimientos_inventario_referencia_tipo_check
    CHECK (referencia_tipo IN ('MANUAL','RECEPCION','RESERVA','VENTA','PEDIDO','DEVOLUCION'));

-- CU-08: un carrito por cliente y empresa; la sucursal es de dónde se compra y se descuenta el stock
CREATE TABLE carritos (
    id BIGSERIAL PRIMARY KEY,
    empresa_id BIGINT NOT NULL REFERENCES empresas(id),
    cliente_id BIGINT NOT NULL REFERENCES usuarios(id),
    sucursal_id BIGINT REFERENCES sucursales(id),
    actualizado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (empresa_id, cliente_id)
);

CREATE TABLE carrito_items (
    id BIGSERIAL PRIMARY KEY,
    empresa_id BIGINT NOT NULL REFERENCES empresas(id),
    carrito_id BIGINT NOT NULL REFERENCES carritos(id) ON DELETE CASCADE,
    variante_id BIGINT NOT NULL REFERENCES variantes(id),
    cantidad INT NOT NULL CHECK (cantidad > 0),
    UNIQUE (carrito_id, variante_id)
);

-- CU-11 / CU-12: pedido único para todos los canales (la venta presencial, CU-29, usará el mismo)
CREATE TABLE pedidos (
    id BIGSERIAL PRIMARY KEY,
    empresa_id BIGINT NOT NULL REFERENCES empresas(id),
    codigo VARCHAR(16) NOT NULL,
    cliente_id BIGINT REFERENCES usuarios(id),              -- vacío en una venta de mostrador sin cliente
    sucursal_id BIGINT NOT NULL REFERENCES sucursales(id),  -- sucursal que vende, retira o despacha
    canal VARCHAR(10) NOT NULL DEFAULT 'DIGITAL' CHECK (canal IN ('DIGITAL','PRESENCIAL')),
    tipo_entrega VARCHAR(10) NOT NULL CHECK (tipo_entrega IN ('DELIVERY','RETIRO','EN_TIENDA')),
    direccion_entrega VARCHAR(300) NOT NULL DEFAULT '',
    nit_ci VARCHAR(20) NOT NULL DEFAULT '',
    razon_social VARCHAR(120) NOT NULL DEFAULT '',
    estado VARCHAR(24) NOT NULL DEFAULT 'PENDIENTE_PAGO'
        CHECK (estado IN ('PENDIENTE_PAGO','PENDIENTE_CONFIRMACION','PAGADO','CANCELADO')),
    subtotal NUMERIC(12,2) NOT NULL CHECK (subtotal >= 0),
    descuento NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (descuento >= 0),
    iva_incluido NUMERIC(12,2) NOT NULL DEFAULT 0,
    total NUMERIC(12,2) NOT NULL CHECK (total >= 0),
    moneda VARCHAR(3) NOT NULL DEFAULT 'BOB',
    motivo_cancelacion VARCHAR(200) NOT NULL DEFAULT '',
    comprobante_numero VARCHAR(30),
    creado_por BIGINT REFERENCES usuarios(id),
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    pagado_en TIMESTAMPTZ,
    UNIQUE (empresa_id, codigo)
);
CREATE UNIQUE INDEX ux_pedidos_comprobante ON pedidos (empresa_id, comprobante_numero) WHERE comprobante_numero IS NOT NULL;
CREATE INDEX ix_pedidos_cliente ON pedidos (empresa_id, cliente_id, creado_en DESC);
CREATE INDEX ix_pedidos_sucursal ON pedidos (empresa_id, sucursal_id, estado, creado_en DESC);

-- los precios y nombres se congelan al crear el pedido: es un documento que no debe cambiar
CREATE TABLE pedido_items (
    id BIGSERIAL PRIMARY KEY,
    empresa_id BIGINT NOT NULL REFERENCES empresas(id),
    pedido_id BIGINT NOT NULL REFERENCES pedidos(id) ON DELETE CASCADE,
    variante_id BIGINT NOT NULL REFERENCES variantes(id),
    sku VARCHAR(40) NOT NULL,
    producto VARCHAR(200) NOT NULL,
    talla VARCHAR(8) NOT NULL,
    color VARCHAR(50) NOT NULL,
    cantidad INT NOT NULL CHECK (cantidad > 0),
    precio_unitario NUMERIC(10,2) NOT NULL,
    precio_final NUMERIC(10,2) NOT NULL,                    -- con la promoción aplicada
    subtotal NUMERIC(12,2) NOT NULL,
    UNIQUE (pedido_id, variante_id)
);

-- CU-32: cada intento de pago queda registrado (aprobado o no) para los reportes de pago
CREATE TABLE pagos (
    id BIGSERIAL PRIMARY KEY,
    empresa_id BIGINT NOT NULL REFERENCES empresas(id),
    pedido_id BIGINT NOT NULL REFERENCES pedidos(id),
    metodo VARCHAR(10) NOT NULL CHECK (metodo IN ('TARJETA','EFECTIVO')),
    proveedor VARCHAR(10) NOT NULL CHECK (proveedor IN ('STRIPE','SIMULADO','CAJA')),
    estado VARCHAR(24) NOT NULL DEFAULT 'PENDIENTE'
        CHECK (estado IN ('PENDIENTE','AUTORIZADO','APROBADO','RECHAZADO','PENDIENTE_CONFIRMACION','CANCELADO')),
    monto NUMERIC(12,2) NOT NULL CHECK (monto >= 0),
    moneda VARCHAR(3) NOT NULL DEFAULT 'BOB',
    monto_pasarela INT,                                     -- centavos cobrados en la pasarela (Stripe no opera en bolivianos)
    moneda_pasarela VARCHAR(3),
    referencia_externa VARCHAR(80),                         -- PaymentIntent de Stripe o intento simulado
    metodo_pago_ref VARCHAR(80),                            -- método de pago de la pasarela (tarjeta guardada o usada)
    guardar_tarjeta BOOLEAN NOT NULL DEFAULT FALSE,
    tarjeta_marca VARCHAR(20) NOT NULL DEFAULT '',
    tarjeta_ultimos4 VARCHAR(4) NOT NULL DEFAULT '',        -- nunca se guarda el número completo ni el CVC
    mensaje VARCHAR(300) NOT NULL DEFAULT '',
    motivo VARCHAR(200) NOT NULL DEFAULT '',
    usuario_id BIGINT REFERENCES usuarios(id),
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    actualizado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (empresa_id, referencia_externa)
);
CREATE INDEX ix_pagos_pedido ON pagos (empresa_id, pedido_id, creado_en DESC);
CREATE INDEX ix_pagos_estado ON pagos (empresa_id, estado, creado_en DESC);

CREATE TABLE clientes_pasarela (
    id BIGSERIAL PRIMARY KEY,
    empresa_id BIGINT NOT NULL REFERENCES empresas(id),
    cliente_id BIGINT NOT NULL REFERENCES usuarios(id),
    referencia VARCHAR(80) NOT NULL,                        -- Customer de Stripe
    UNIQUE (empresa_id, cliente_id)
);

CREATE TABLE tarjetas_guardadas (
    id BIGSERIAL PRIMARY KEY,
    empresa_id BIGINT NOT NULL REFERENCES empresas(id),
    cliente_id BIGINT NOT NULL REFERENCES usuarios(id),
    proveedor VARCHAR(10) NOT NULL CHECK (proveedor IN ('STRIPE','SIMULADO')),
    referencia VARCHAR(80) NOT NULL,
    marca VARCHAR(20) NOT NULL,
    ultimos4 VARCHAR(4) NOT NULL,
    exp_mes INT NOT NULL,
    exp_anio INT NOT NULL,
    escenario VARCHAR(30) NOT NULL DEFAULT '',              -- solo simulación: cómo responde esa tarjeta de prueba
    creada_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (empresa_id, cliente_id, referencia)
);

-- numeración de comprobantes por sucursal (la usarán también las ventas de caja, CU-30)
CREATE TABLE secuencias_comprobante (
    empresa_id BIGINT NOT NULL REFERENCES empresas(id),
    sucursal_id BIGINT NOT NULL REFERENCES sucursales(id),
    ultimo INT NOT NULL DEFAULT 0,
    PRIMARY KEY (empresa_id, sucursal_id)
);
"""


def upgrade() -> None:
    op.execute(SQL_UP)


def downgrade() -> None:
    op.execute("DELETE FROM movimientos_inventario WHERE referencia_tipo = 'PEDIDO'")
    op.execute("ALTER TABLE movimientos_inventario DROP CONSTRAINT movimientos_inventario_referencia_tipo_check")
    op.execute("ALTER TABLE movimientos_inventario ADD CONSTRAINT movimientos_inventario_referencia_tipo_check "
               "CHECK (referencia_tipo IN ('MANUAL','RECEPCION','RESERVA','VENTA','DEVOLUCION'))")
    for tabla in ("secuencias_comprobante", "tarjetas_guardadas", "clientes_pasarela", "pagos", "pedido_items", "pedidos", "carrito_items", "carritos"):
        op.execute(f"DROP TABLE IF EXISTS {tabla} CASCADE")

"""Fase B · Proveedores y abastecimiento (CU-15, CU-31) e inventario por sucursal (CU-05, CU-20, CU-26).

Revision ID: 0004
Revises: 0003
"""
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

SQL_UP = """
-- el proveedor es un actor con cuenta propia (portal de proveedores)
INSERT INTO roles (nombre, descripcion) VALUES ('Proveedor', 'Envía avisos de remisión y propuestas de producto');

CREATE TABLE proveedores (
    id BIGSERIAL PRIMARY KEY,
    empresa_id BIGINT NOT NULL REFERENCES empresas(id),
    usuario_id BIGINT UNIQUE REFERENCES usuarios(id),          -- cuenta del portal (opcional)
    razon_social VARCHAR(200) NOT NULL,
    nombre_comercial VARCHAR(200) NOT NULL DEFAULT '',
    nit VARCHAR(50),
    email VARCHAR(120),
    telefono VARCHAR(20),
    direccion VARCHAR(300) NOT NULL DEFAULT '',
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (email IS NOT NULL OR telefono IS NOT NULL)
);
CREATE UNIQUE INDEX ux_proveedores_nit ON proveedores (empresa_id, nit) WHERE nit IS NOT NULL;
CREATE INDEX ix_proveedores_empresa ON proveedores (empresa_id, activo);

-- CU-17: una colección puede venir de un proveedor
ALTER TABLE colecciones ADD CONSTRAINT fk_colecciones_proveedor FOREIGN KEY (proveedor_id) REFERENCES proveedores(id);

-- CU-31: aviso de remisión (lote en tránsito) y sus ítems
CREATE TABLE lotes_abastecimiento (
    id BIGSERIAL PRIMARY KEY,
    empresa_id BIGINT NOT NULL REFERENCES empresas(id),
    proveedor_id BIGINT NOT NULL REFERENCES proveedores(id),
    sucursal_id BIGINT NOT NULL REFERENCES sucursales(id),     -- sucursal que recibirá la mercadería
    codigo VARCHAR(20) NOT NULL,
    estado VARCHAR(12) NOT NULL DEFAULT 'EN_TRANSITO' CHECK (estado IN ('EN_TRANSITO','RECIBIDO','CANCELADO')),
    referencia VARCHAR(100) NOT NULL DEFAULT '',                -- número de remisión o factura
    notas VARCHAR(300) NOT NULL DEFAULT '',
    creado_por BIGINT REFERENCES usuarios(id),
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    cerrado_por BIGINT REFERENCES usuarios(id),
    cerrado_en TIMESTAMPTZ,
    UNIQUE (empresa_id, codigo)
);
CREATE INDEX ix_lotes_empresa ON lotes_abastecimiento (empresa_id, estado, sucursal_id);

CREATE TABLE lote_items (
    id BIGSERIAL PRIMARY KEY,
    empresa_id BIGINT NOT NULL REFERENCES empresas(id),
    lote_id BIGINT NOT NULL REFERENCES lotes_abastecimiento(id) ON DELETE CASCADE,
    variante_id BIGINT NOT NULL REFERENCES variantes(id),
    cantidad INT NOT NULL CHECK (cantidad > 0),                 -- lo que el proveedor despachó
    cantidad_recibida INT CHECK (cantidad_recibida >= 0),       -- lo que se contó al recibir
    costo_unitario NUMERIC(10,2) CHECK (costo_unitario >= 0),
    UNIQUE (lote_id, variante_id)
);
CREATE INDEX ix_lote_items_variante ON lote_items (empresa_id, variante_id);

CREATE TABLE propuestas_producto (
    id BIGSERIAL PRIMARY KEY,
    empresa_id BIGINT NOT NULL REFERENCES empresas(id),
    proveedor_id BIGINT NOT NULL REFERENCES proveedores(id),
    coleccion_id BIGINT NOT NULL REFERENCES colecciones(id),
    nombre VARCHAR(200) NOT NULL,
    descripcion TEXT NOT NULL DEFAULT '',
    genero VARCHAR(10) NOT NULL CHECK (genero IN ('MASCULINO','FEMENINO','UNISEX','NINOS')),
    precio_base NUMERIC(10,2) NOT NULL CHECK (precio_base >= 0),
    material VARCHAR(200) NOT NULL DEFAULT '',
    estado VARCHAR(10) NOT NULL DEFAULT 'PENDIENTE' CHECK (estado IN ('PENDIENTE','APROBADA','RECHAZADA')),
    notas_revision VARCHAR(500) NOT NULL DEFAULT '',
    revisado_por BIGINT REFERENCES usuarios(id),
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_propuestas_empresa ON propuestas_producto (empresa_id, estado);

-- Inventario: umbral de reposición y bitácora de movimientos (solo se agregan filas, nunca se editan)
ALTER TABLE existencias ADD COLUMN umbral_minimo INT NOT NULL DEFAULT 0 CHECK (umbral_minimo >= 0);

CREATE TABLE movimientos_inventario (
    id BIGSERIAL PRIMARY KEY,
    empresa_id BIGINT NOT NULL REFERENCES empresas(id),
    sucursal_id BIGINT NOT NULL REFERENCES sucursales(id),
    variante_id BIGINT NOT NULL REFERENCES variantes(id),
    tipo VARCHAR(20) NOT NULL CHECK (tipo IN (
        'ENTRADA_RECEPCION','AJUSTE_ENTRADA','AJUSTE_SALIDA','RESERVA','LIBERA_RESERVA','VENTA','VENTA_RESERVA','DEVOLUCION')),
    cantidad INT NOT NULL CHECK (cantidad > 0),                 -- siempre positiva: el signo lo da el tipo
    referencia_tipo VARCHAR(20) NOT NULL CHECK (referencia_tipo IN ('MANUAL','RECEPCION','RESERVA','VENTA','DEVOLUCION')),
    referencia_id BIGINT,
    usuario_id BIGINT REFERENCES usuarios(id),
    nota VARCHAR(200) NOT NULL DEFAULT '',
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_movimientos_sucursal ON movimientos_inventario (empresa_id, sucursal_id, creado_en DESC);
CREATE INDEX ix_movimientos_variante ON movimientos_inventario (empresa_id, variante_id, creado_en DESC);
"""


def upgrade() -> None:
    op.execute(SQL_UP)


def downgrade() -> None:
    for tabla in ("movimientos_inventario", "propuestas_producto", "lote_items", "lotes_abastecimiento"):
        op.execute(f"DROP TABLE IF EXISTS {tabla} CASCADE")
    op.execute("ALTER TABLE existencias DROP COLUMN IF EXISTS umbral_minimo")
    op.execute("ALTER TABLE colecciones DROP CONSTRAINT IF EXISTS fk_colecciones_proveedor")
    op.execute("DROP TABLE IF EXISTS proveedores CASCADE")
    op.execute("DELETE FROM usuarios WHERE rol_id IN (SELECT id FROM roles WHERE nombre = 'Proveedor')")
    op.execute("DELETE FROM roles WHERE nombre = 'Proveedor'")

"""Fase A · Catálogo por empresa (CU-16 a CU-19), existencias por sucursal (base de CU-05) y promociones.

Revision ID: 0003
Revises: 0002
"""
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

SQL_UP = """
CREATE TABLE grupos_talla (
    id BIGSERIAL PRIMARY KEY,
    empresa_id BIGINT NOT NULL REFERENCES empresas(id),
    nombre VARCHAR(50) NOT NULL,
    descripcion VARCHAR(200),
    UNIQUE (empresa_id, nombre)
);

CREATE TABLE tallas (
    id BIGSERIAL PRIMARY KEY,
    empresa_id BIGINT NOT NULL REFERENCES empresas(id),
    grupo_id BIGINT NOT NULL REFERENCES grupos_talla(id),
    codigo VARCHAR(8) NOT NULL,
    orden INT NOT NULL DEFAULT 0,
    UNIQUE (grupo_id, codigo)
);
CREATE INDEX ix_tallas_empresa ON tallas (empresa_id, grupo_id, orden);

CREATE TABLE categorias (
    id BIGSERIAL PRIMARY KEY,
    empresa_id BIGINT NOT NULL REFERENCES empresas(id),
    padre_id BIGINT REFERENCES categorias(id),
    grupo_talla_id BIGINT REFERENCES grupos_talla(id),
    nombre VARCHAR(100) NOT NULL,
    slug VARCHAR(120) NOT NULL,
    orden INT NOT NULL DEFAULT 0,
    activa BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE (empresa_id, slug)
);
CREATE INDEX ix_categorias_empresa ON categorias (empresa_id, activa);

CREATE TABLE marcas (
    id BIGSERIAL PRIMARY KEY,
    empresa_id BIGINT NOT NULL REFERENCES empresas(id),
    nombre VARCHAR(100) NOT NULL,
    slug VARCHAR(120) NOT NULL,
    UNIQUE (empresa_id, nombre),
    UNIQUE (empresa_id, slug)
);

CREATE TABLE colores (
    id BIGSERIAL PRIMARY KEY,
    empresa_id BIGINT NOT NULL REFERENCES empresas(id),
    nombre VARCHAR(50) NOT NULL,
    slug VARCHAR(60) NOT NULL,
    codigo VARCHAR(6) NOT NULL,                      -- código corto para el SKU
    codigo_hex VARCHAR(7) NOT NULL CHECK (codigo_hex ~ '^#[0-9A-Fa-f]{6}$'),
    UNIQUE (empresa_id, nombre),
    UNIQUE (empresa_id, slug),
    UNIQUE (empresa_id, codigo)
);

CREATE TABLE temporadas (
    id BIGSERIAL PRIMARY KEY,
    empresa_id BIGINT NOT NULL REFERENCES empresas(id),
    nombre VARCHAR(100) NOT NULL,
    codigo VARCHAR(20) NOT NULL,
    tipo VARCHAR(20) NOT NULL
        CHECK (tipo IN ('PRIMAVERA_VERANO','OTONO_INVIERNO','ESCOLAR','PROMOCIONAL','NUEVA_COLECCION')),
    inicio DATE NOT NULL,
    fin DATE NOT NULL,
    activa BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE (empresa_id, codigo),
    CHECK (fin > inicio)
);

CREATE TABLE colecciones (
    id BIGSERIAL PRIMARY KEY,
    empresa_id BIGINT NOT NULL REFERENCES empresas(id),
    temporada_id BIGINT NOT NULL REFERENCES temporadas(id),
    proveedor_id BIGINT,                             -- la FK a proveedores se agrega en la Fase B (CU-15)
    nombre VARCHAR(120) NOT NULL,
    slug VARCHAR(140) NOT NULL,
    fecha_lanzamiento DATE,
    activa BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE (empresa_id, slug)
);

CREATE TABLE productos (
    id BIGSERIAL PRIMARY KEY,
    empresa_id BIGINT NOT NULL REFERENCES empresas(id),
    publico_id UUID NOT NULL UNIQUE,
    categoria_id BIGINT NOT NULL REFERENCES categorias(id),
    marca_id BIGINT REFERENCES marcas(id),
    coleccion_id BIGINT NOT NULL REFERENCES colecciones(id),
    nombre VARCHAR(200) NOT NULL,
    slug VARCHAR(220) NOT NULL,
    descripcion TEXT NOT NULL DEFAULT '',
    genero VARCHAR(10) NOT NULL CHECK (genero IN ('MASCULINO','FEMENINO','UNISEX','NINOS')),
    precio_base NUMERIC(10,2) NOT NULL CHECK (precio_base >= 0),
    material VARCHAR(200) NOT NULL DEFAULT '',
    cuidado VARCHAR(500) NOT NULL DEFAULT '',
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (empresa_id, slug)
);
CREATE INDEX ix_productos_empresa ON productos (empresa_id, activo, categoria_id);
CREATE INDEX ix_productos_coleccion ON productos (coleccion_id);

CREATE TABLE variantes (
    id BIGSERIAL PRIMARY KEY,
    empresa_id BIGINT NOT NULL REFERENCES empresas(id),
    producto_id BIGINT NOT NULL REFERENCES productos(id) ON DELETE CASCADE,
    talla_id BIGINT NOT NULL REFERENCES tallas(id),
    color_id BIGINT NOT NULL REFERENCES colores(id),
    sku VARCHAR(40) NOT NULL,
    codigo_barras VARCHAR(32),
    precio_especifico NUMERIC(10,2) CHECK (precio_especifico >= 0),
    activa BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE (producto_id, talla_id, color_id),
    UNIQUE (empresa_id, sku)
);
CREATE UNIQUE INDEX ux_variantes_barras ON variantes (empresa_id, codigo_barras) WHERE codigo_barras IS NOT NULL;
CREATE INDEX ix_variantes_producto ON variantes (producto_id, activa);

CREATE TABLE imagenes_producto (
    id BIGSERIAL PRIMARY KEY,
    empresa_id BIGINT NOT NULL REFERENCES empresas(id),
    producto_id BIGINT NOT NULL REFERENCES productos(id) ON DELETE CASCADE,
    color_id BIGINT REFERENCES colores(id),          -- NULL: sirve para todos los colores
    ruta VARCHAR(300) NOT NULL,
    texto_alt VARCHAR(200) NOT NULL DEFAULT '',
    principal BOOLEAN NOT NULL DEFAULT FALSE,
    orden INT NOT NULL DEFAULT 0
);
CREATE INDEX ix_imagenes_producto ON imagenes_producto (producto_id, principal DESC, orden);

CREATE TABLE promociones (
    id BIGSERIAL PRIMARY KEY,
    empresa_id BIGINT NOT NULL REFERENCES empresas(id),
    nombre VARCHAR(200) NOT NULL,
    codigo VARCHAR(50),                              -- NULL: promoción automática; con valor: cupón
    tipo_descuento VARCHAR(10) NOT NULL CHECK (tipo_descuento IN ('PORCENTAJE','MONTO')),
    valor NUMERIC(10,2) NOT NULL CHECK (valor > 0),
    inicia DATE NOT NULL,
    termina DATE NOT NULL,
    monto_minimo NUMERIC(10,2) NOT NULL DEFAULT 0,
    usos_maximos INT,
    usos INT NOT NULL DEFAULT 0,
    activa BOOLEAN NOT NULL DEFAULT TRUE,
    CHECK (termina > inicia)
);
CREATE UNIQUE INDEX ux_promociones_codigo ON promociones (empresa_id, upper(codigo)) WHERE codigo IS NOT NULL;
CREATE INDEX ix_promociones_empresa ON promociones (empresa_id, activa, inicia, termina);

CREATE TABLE promocion_categorias (
    promocion_id BIGINT NOT NULL REFERENCES promociones(id) ON DELETE CASCADE,
    categoria_id BIGINT NOT NULL REFERENCES categorias(id),
    PRIMARY KEY (promocion_id, categoria_id)
);
CREATE TABLE promocion_colecciones (
    promocion_id BIGINT NOT NULL REFERENCES promociones(id) ON DELETE CASCADE,
    coleccion_id BIGINT NOT NULL REFERENCES colecciones(id),
    PRIMARY KEY (promocion_id, coleccion_id)
);
CREATE TABLE promocion_productos (
    promocion_id BIGINT NOT NULL REFERENCES promociones(id) ON DELETE CASCADE,
    producto_id BIGINT NOT NULL REFERENCES productos(id),
    PRIMARY KEY (promocion_id, producto_id)
);

-- Existencias por sucursal: base de CU-05 (disponibilidad). La Fase B la amplía con movimientos (CU-26).
CREATE TABLE existencias (
    id BIGSERIAL PRIMARY KEY,
    empresa_id BIGINT NOT NULL REFERENCES empresas(id),
    sucursal_id BIGINT NOT NULL REFERENCES sucursales(id),
    variante_id BIGINT NOT NULL REFERENCES variantes(id) ON DELETE CASCADE,
    disponible INT NOT NULL DEFAULT 0 CHECK (disponible >= 0),
    reservada INT NOT NULL DEFAULT 0 CHECK (reservada >= 0),
    vendida INT NOT NULL DEFAULT 0 CHECK (vendida >= 0),
    UNIQUE (sucursal_id, variante_id)
);
CREATE INDEX ix_existencias_variante ON existencias (empresa_id, variante_id);
"""

TABLAS = [
    "existencias", "promocion_productos", "promocion_colecciones", "promocion_categorias", "promociones",
    "imagenes_producto", "variantes", "productos", "colecciones", "temporadas", "colores", "marcas",
    "categorias", "tallas", "grupos_talla",
]


def upgrade() -> None:
    op.execute(SQL_UP)


def downgrade() -> None:
    for tabla in TABLAS:
        op.execute(f"DROP TABLE IF EXISTS {tabla} CASCADE")

"""Esquema inicial multitenant (Lote 1): script físico 3.5.4 del documento.

Revision ID: 0001
Revises:
"""
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

SQL_UP = """
CREATE TABLE planes (
    id BIGSERIAL PRIMARY KEY,
    nombre VARCHAR(50) NOT NULL UNIQUE,
    descripcion TEXT,
    precio NUMERIC(10,2) NOT NULL CHECK (precio >= 0),
    periodicidad VARCHAR(20) NOT NULL DEFAULT 'mensual',
    max_sucursales INT NOT NULL CHECK (max_sucursales > 0),
    reportes_ia BOOLEAN NOT NULL DEFAULT FALSE,
    offline BOOLEAN NOT NULL DEFAULT TRUE,
    reportes_convencionales BOOLEAN NOT NULL DEFAULT TRUE,
    activo BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE empresas (
    id BIGSERIAL PRIMARY KEY,
    codigo VARCHAR(30) NOT NULL UNIQUE,
    razon_social VARCHAR(120) NOT NULL,
    nit VARCHAR(20) NOT NULL UNIQUE,
    email_contacto VARCHAR(120),
    telefono VARCHAR(20),
    estado VARCHAR(15) NOT NULL DEFAULT 'ACTIVA'
        CHECK (estado IN ('ACTIVA','SUSPENDIDA','CANCELADA')),
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE suscripciones (
    id BIGSERIAL PRIMARY KEY,
    empresa_id BIGINT NOT NULL REFERENCES empresas(id),
    plan_id BIGINT NOT NULL REFERENCES planes(id),
    fecha_inicio DATE NOT NULL,
    fecha_vencimiento DATE NOT NULL,
    estado VARCHAR(15) NOT NULL DEFAULT 'ACTIVA'
        CHECK (estado IN ('ACTIVA','VENCIDA','SUSPENDIDA','CANCELADA')),
    forma_pago VARCHAR(20),
    monto NUMERIC(10,2),
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (fecha_vencimiento > fecha_inicio)
);
-- una sola suscripción vigente por empresa
CREATE UNIQUE INDEX ux_suscripcion_activa ON suscripciones (empresa_id) WHERE estado = 'ACTIVA';

CREATE TABLE ciudades (
    id BIGSERIAL PRIMARY KEY,
    empresa_id BIGINT NOT NULL REFERENCES empresas(id),
    nombre VARCHAR(80) NOT NULL,
    departamento VARCHAR(80),
    UNIQUE (empresa_id, nombre)
);

CREATE TABLE sucursales (
    id BIGSERIAL PRIMARY KEY,
    empresa_id BIGINT NOT NULL REFERENCES empresas(id),
    ciudad_id BIGINT NOT NULL REFERENCES ciudades(id),
    nombre VARCHAR(100) NOT NULL,
    direccion VARCHAR(200),
    telefono VARCHAR(20),
    horario VARCHAR(100),
    activa BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (empresa_id, nombre)
);
CREATE INDEX ix_sucursales_empresa ON sucursales (empresa_id, activa);

CREATE TABLE roles (
    id BIGSERIAL PRIMARY KEY,
    nombre VARCHAR(30) NOT NULL UNIQUE,
    descripcion VARCHAR(120)
);

CREATE TABLE usuarios (
    id BIGSERIAL PRIMARY KEY,
    empresa_id BIGINT REFERENCES empresas(id),      -- NULL: SuperAdministrador
    sucursal_id BIGINT REFERENCES sucursales(id),
    rol_id BIGINT NOT NULL REFERENCES roles(id),
    nombre VARCHAR(80) NOT NULL,
    apellidos VARCHAR(80) NOT NULL,
    email VARCHAR(120) NOT NULL,
    password_hash VARCHAR(128) NOT NULL,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    ultimo_acceso TIMESTAMPTZ,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (empresa_id, email)
);
CREATE INDEX ix_usuarios_empresa ON usuarios (empresa_id, rol_id);

INSERT INTO roles (nombre, descripcion) VALUES
    ('SuperAdministrador','Administra la plataforma'),
    ('Administrador','Administra una empresa'),
    ('Encargado','Gestiona una sucursal'),
    ('Cajero','Registra ventas en una sucursal'),
    ('Cliente','Usuario final de una empresa');
"""


def upgrade() -> None:
    for sentencia in [s.strip() for s in SQL_UP.split(";\n") if s.strip()]:
        op.execute(sentencia)


def downgrade() -> None:
    for tabla in ("usuarios", "roles", "sucursales", "ciudades", "suscripciones", "empresas", "planes"):
        op.execute(f"DROP TABLE IF EXISTS {tabla} CASCADE")

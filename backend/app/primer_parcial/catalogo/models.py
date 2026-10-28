"""P4 · Catálogo (primer parcial, CU-16 a CU-19) — todo con empresa_id (RN01)."""
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger, Boolean, Column, Date, DateTime, ForeignKey, Integer, Numeric, String, Table, Text, UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class GrupoTalla(Base):
    __tablename__ = "grupos_talla"
    __table_args__ = (UniqueConstraint("empresa_id", "nombre"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("empresas.id"))
    nombre: Mapped[str] = mapped_column(String(50))
    descripcion: Mapped[str | None] = mapped_column(String(200))


class Talla(Base):
    __tablename__ = "tallas"
    __table_args__ = (UniqueConstraint("grupo_id", "codigo"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("empresas.id"))
    grupo_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("grupos_talla.id"))
    codigo: Mapped[str] = mapped_column(String(8))
    orden: Mapped[int] = mapped_column(Integer, default=0)

    grupo: Mapped[GrupoTalla] = relationship(lazy="joined")


class Categoria(Base):
    __tablename__ = "categorias"
    __table_args__ = (UniqueConstraint("empresa_id", "slug"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("empresas.id"))
    padre_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("categorias.id"))
    grupo_talla_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("grupos_talla.id"))
    nombre: Mapped[str] = mapped_column(String(100))
    slug: Mapped[str] = mapped_column(String(120))
    orden: Mapped[int] = mapped_column(Integer, default=0)
    activa: Mapped[bool] = mapped_column(Boolean, default=True)


class Marca(Base):
    __tablename__ = "marcas"
    __table_args__ = (UniqueConstraint("empresa_id", "nombre"), UniqueConstraint("empresa_id", "slug"))

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("empresas.id"))
    nombre: Mapped[str] = mapped_column(String(100))
    slug: Mapped[str] = mapped_column(String(120))


class Color(Base):
    __tablename__ = "colores"
    __table_args__ = (
        UniqueConstraint("empresa_id", "nombre"), UniqueConstraint("empresa_id", "slug"), UniqueConstraint("empresa_id", "codigo"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("empresas.id"))
    nombre: Mapped[str] = mapped_column(String(50))
    slug: Mapped[str] = mapped_column(String(60))
    codigo: Mapped[str] = mapped_column(String(6))  # código corto fijo: lo usa el SKU
    codigo_hex: Mapped[str] = mapped_column(String(7))


class Temporada(Base):
    __tablename__ = "temporadas"
    __table_args__ = (UniqueConstraint("empresa_id", "codigo"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("empresas.id"))
    nombre: Mapped[str] = mapped_column(String(100))
    codigo: Mapped[str] = mapped_column(String(20))
    tipo: Mapped[str] = mapped_column(String(20))
    inicio: Mapped[date] = mapped_column(Date)
    fin: Mapped[date] = mapped_column(Date)
    activa: Mapped[bool] = mapped_column(Boolean, default=True)


class Coleccion(Base):
    __tablename__ = "colecciones"
    __table_args__ = (UniqueConstraint("empresa_id", "slug"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("empresas.id"))
    temporada_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("temporadas.id"))
    proveedor_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("proveedores.id"))
    nombre: Mapped[str] = mapped_column(String(120))
    slug: Mapped[str] = mapped_column(String(140))
    fecha_lanzamiento: Mapped[date | None] = mapped_column(Date)
    activa: Mapped[bool] = mapped_column(Boolean, default=True)

    temporada: Mapped[Temporada] = relationship(lazy="joined")


class Producto(Base):
    __tablename__ = "productos"
    __table_args__ = (UniqueConstraint("empresa_id", "slug"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("empresas.id"))
    publico_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), default=uuid.uuid4, unique=True)
    categoria_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("categorias.id"))
    marca_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("marcas.id"))
    coleccion_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("colecciones.id"))
    nombre: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(220))
    descripcion: Mapped[str] = mapped_column(Text, default="")
    genero: Mapped[str] = mapped_column(String(10))
    precio_base: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    material: Mapped[str] = mapped_column(String(200), default="")
    cuidado: Mapped[str] = mapped_column(String(500), default="")
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    categoria: Mapped[Categoria] = relationship(lazy="joined")
    marca: Mapped[Marca | None] = relationship(lazy="joined")
    coleccion: Mapped[Coleccion] = relationship(lazy="joined")
    variantes: Mapped[list["Variante"]] = relationship(back_populates="producto", cascade="all, delete-orphan")
    imagenes: Mapped[list["ImagenProducto"]] = relationship(back_populates="producto", cascade="all, delete-orphan")


class Variante(Base):
    """Producto × talla × color = SKU: es la unidad del inventario."""

    __tablename__ = "variantes"
    __table_args__ = (UniqueConstraint("producto_id", "talla_id", "color_id"), UniqueConstraint("empresa_id", "sku"))

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("empresas.id"))
    producto_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("productos.id", ondelete="CASCADE"))
    talla_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("tallas.id"))
    color_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("colores.id"))
    sku: Mapped[str] = mapped_column(String(40))
    codigo_barras: Mapped[str | None] = mapped_column(String(32))
    precio_especifico: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    activa: Mapped[bool] = mapped_column(Boolean, default=True)

    producto: Mapped[Producto] = relationship(back_populates="variantes")
    talla: Mapped[Talla] = relationship(lazy="joined")
    color: Mapped[Color] = relationship(lazy="joined")

    @property
    def precio(self) -> Decimal:
        return self.precio_especifico if self.precio_especifico is not None else self.producto.precio_base


class ImagenProducto(Base):
    __tablename__ = "imagenes_producto"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("empresas.id"))
    producto_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("productos.id", ondelete="CASCADE"))
    color_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("colores.id"))
    ruta: Mapped[str] = mapped_column(String(300))
    texto_alt: Mapped[str] = mapped_column(String(200), default="")
    principal: Mapped[bool] = mapped_column(Boolean, default=False)
    orden: Mapped[int] = mapped_column(Integer, default=0)

    producto: Mapped[Producto] = relationship(back_populates="imagenes")


# Tablas de unión de las promociones (alcance: categorías, colecciones o productos; vacío = todo)
promocion_categorias = Table(
    "promocion_categorias", Base.metadata,
    Column("promocion_id", BigInteger, ForeignKey("promociones.id", ondelete="CASCADE"), primary_key=True),
    Column("categoria_id", BigInteger, ForeignKey("categorias.id"), primary_key=True),
)
promocion_colecciones = Table(
    "promocion_colecciones", Base.metadata,
    Column("promocion_id", BigInteger, ForeignKey("promociones.id", ondelete="CASCADE"), primary_key=True),
    Column("coleccion_id", BigInteger, ForeignKey("colecciones.id"), primary_key=True),
)
promocion_productos = Table(
    "promocion_productos", Base.metadata,
    Column("promocion_id", BigInteger, ForeignKey("promociones.id", ondelete="CASCADE"), primary_key=True),
    Column("producto_id", BigInteger, ForeignKey("productos.id"), primary_key=True),
)


class Promocion(Base):
    __tablename__ = "promociones"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("empresas.id"))
    nombre: Mapped[str] = mapped_column(String(200))
    codigo: Mapped[str | None] = mapped_column(String(50))
    tipo_descuento: Mapped[str] = mapped_column(String(10))
    valor: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    inicia: Mapped[date] = mapped_column(Date)
    termina: Mapped[date] = mapped_column(Date)
    monto_minimo: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    usos_maximos: Mapped[int | None] = mapped_column(Integer)
    usos: Mapped[int] = mapped_column(Integer, default=0)
    activa: Mapped[bool] = mapped_column(Boolean, default=True)

    categorias: Mapped[list[Categoria]] = relationship(secondary=promocion_categorias, lazy="selectin")
    colecciones: Mapped[list[Coleccion]] = relationship(secondary=promocion_colecciones, lazy="selectin")
    productos: Mapped[list[Producto]] = relationship(secondary=promocion_productos, lazy="selectin")

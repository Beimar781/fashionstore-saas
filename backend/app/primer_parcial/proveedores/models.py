"""P3 · Proveedores y abastecimiento (primer parcial, CU-15 y CU-31) — todo con empresa_id."""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Proveedor(Base):
    __tablename__ = "proveedores"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("empresas.id"))
    usuario_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("usuarios.id"), unique=True)
    razon_social: Mapped[str] = mapped_column(String(200))
    nombre_comercial: Mapped[str] = mapped_column(String(200), default="")
    nit: Mapped[str | None] = mapped_column(String(50))
    email: Mapped[str | None] = mapped_column(String(120))
    telefono: Mapped[str | None] = mapped_column(String(20))
    direccion: Mapped[str] = mapped_column(String(300), default="")
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Lote(Base):
    """Aviso de remisión: mercadería despachada por un proveedor hacia una sucursal (EN_TRANSITO → RECIBIDO | CANCELADO)."""

    __tablename__ = "lotes_abastecimiento"
    __table_args__ = (UniqueConstraint("empresa_id", "codigo"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("empresas.id"))
    proveedor_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("proveedores.id"))
    sucursal_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("sucursales.id"))
    codigo: Mapped[str] = mapped_column(String(20))
    estado: Mapped[str] = mapped_column(String(12), default="EN_TRANSITO")
    referencia: Mapped[str] = mapped_column(String(100), default="")
    notas: Mapped[str] = mapped_column(String(300), default="")
    creado_por: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("usuarios.id"))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    cerrado_por: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("usuarios.id"))
    cerrado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    proveedor: Mapped[Proveedor] = relationship(lazy="joined")
    items: Mapped[list["LoteItem"]] = relationship(back_populates="lote", cascade="all, delete-orphan", order_by="LoteItem.id")


class LoteItem(Base):
    __tablename__ = "lote_items"
    __table_args__ = (UniqueConstraint("lote_id", "variante_id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("empresas.id"))
    lote_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("lotes_abastecimiento.id", ondelete="CASCADE"))
    variante_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("variantes.id"))
    cantidad: Mapped[int] = mapped_column(Integer)
    cantidad_recibida: Mapped[int | None] = mapped_column(Integer)
    costo_unitario: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))

    lote: Mapped[Lote] = relationship(back_populates="items")


class Propuesta(Base):
    """El proveedor propone un producto nuevo; el Administrador lo aprueba o rechaza (PENDIENTE → APROBADA | RECHAZADA)."""

    __tablename__ = "propuestas_producto"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("empresas.id"))
    proveedor_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("proveedores.id"))
    coleccion_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("colecciones.id"))
    nombre: Mapped[str] = mapped_column(String(200))
    descripcion: Mapped[str] = mapped_column(Text, default="")
    genero: Mapped[str] = mapped_column(String(10))
    precio_base: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    material: Mapped[str] = mapped_column(String(200), default="")
    estado: Mapped[str] = mapped_column(String(10), default="PENDIENTE")
    notas_revision: Mapped[str] = mapped_column(String(500), default="")
    revisado_por: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("usuarios.id"))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    proveedor: Mapped[Proveedor] = relationship(lazy="joined")

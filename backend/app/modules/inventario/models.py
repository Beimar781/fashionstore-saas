"""P5 · Inventario — existencias de cada variante por sucursal y bitácora de movimientos."""
from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Existencia(Base):
    """Unidades de una variante en una sucursal: disponibles para vender, reservadas y vendidas (netas de devoluciones)."""

    __tablename__ = "existencias"
    __table_args__ = (UniqueConstraint("sucursal_id", "variante_id"), CheckConstraint("disponible >= 0"))

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("empresas.id"))
    sucursal_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("sucursales.id"))
    variante_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("variantes.id", ondelete="CASCADE"))
    disponible: Mapped[int] = mapped_column(Integer, default=0)
    reservada: Mapped[int] = mapped_column(Integer, default=0)
    vendida: Mapped[int] = mapped_column(Integer, default=0)
    umbral_minimo: Mapped[int] = mapped_column(Integer, default=0)  # aviso de reposición


class MovimientoInventario(Base):
    """Bitácora: cada cambio de existencias deja una fila con tipo, referencia y usuario. Nunca se edita ni se borra."""

    __tablename__ = "movimientos_inventario"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("empresas.id"))
    sucursal_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("sucursales.id"))
    variante_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("variantes.id"))
    tipo: Mapped[str] = mapped_column(String(20))
    cantidad: Mapped[int] = mapped_column(Integer)
    referencia_tipo: Mapped[str] = mapped_column(String(20))
    referencia_id: Mapped[int | None] = mapped_column(BigInteger)
    usuario_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("usuarios.id"))
    nota: Mapped[str] = mapped_column(String(200), default="")
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

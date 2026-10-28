"""P6 · Reservas — reservas del cliente (CU-09, CU-10), su atención en la sucursal (CU-24, CU-25) y notificaciones (RF11)."""
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Reserva(Base):
    """Estados: PENDIENTE → PREPARADA → EN_PROBADOR → COMPLETADA; desde los tres primeros también CANCELADA o EXPIRADA."""

    __tablename__ = "reservas"
    __table_args__ = (UniqueConstraint("empresa_id", "codigo"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("empresas.id"))
    codigo: Mapped[str] = mapped_column(String(16))
    cliente_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("usuarios.id"))
    sucursal_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("sucursales.id"))
    programada_para: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    vence_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    estado: Mapped[str] = mapped_column(String(12), default="PENDIENTE")
    notas: Mapped[str] = mapped_column(String(300), default="")
    preparada_por: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("usuarios.id"))
    creada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    actualizada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    items: Mapped[list["ReservaItem"]] = relationship(back_populates="reserva", cascade="all, delete-orphan", order_by="ReservaItem.id")


class ReservaItem(Base):
    """Estados del ítem: RESERVADO (el stock está apartado), NO_ENCONTRADO, VENDIDO o LIBERADO (el stock volvió a disponible)."""

    __tablename__ = "reserva_items"
    __table_args__ = (UniqueConstraint("reserva_id", "variante_id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("empresas.id"))
    reserva_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("reservas.id", ondelete="CASCADE"))
    variante_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("variantes.id"))
    cantidad: Mapped[int] = mapped_column(Integer)
    estado: Mapped[str] = mapped_column(String(14), default="RESERVADO")

    reserva: Mapped[Reserva] = relationship(back_populates="items")


class Notificacion(Base):
    """Aviso para un usuario (usuario_id) o para toda una sucursal (usuario_id vacío)."""

    __tablename__ = "notificaciones"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("empresas.id"))
    usuario_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("usuarios.id"))
    sucursal_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("sucursales.id"))
    tipo: Mapped[str] = mapped_column(String(30))
    titulo: Mapped[str] = mapped_column(String(200))
    mensaje: Mapped[str] = mapped_column(Text)
    referencia_tipo: Mapped[str] = mapped_column(String(30), default="")
    referencia_id: Mapped[int | None] = mapped_column(BigInteger)
    leida: Mapped[bool] = mapped_column(Boolean, default=False)
    creada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

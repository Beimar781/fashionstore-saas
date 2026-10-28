"""P6 · Reservas — carrito (CU-08) del primer parcial, ahora por cliente y por empresa."""
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Carrito(Base):
    """Un carrito por cliente y empresa. `sucursal_id` es la sucursal de la que compra (de ahí sale el stock)."""

    __tablename__ = "carritos"
    __table_args__ = (UniqueConstraint("empresa_id", "cliente_id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("empresas.id"))
    cliente_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("usuarios.id"))
    sucursal_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("sucursales.id"))
    actualizado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    items: Mapped[list["CarritoItem"]] = relationship(back_populates="carrito", cascade="all, delete-orphan", order_by="CarritoItem.id")


class CarritoItem(Base):
    """El precio no se guarda: el carrito siempre muestra el precio vigente; se congela al crear el pedido."""

    __tablename__ = "carrito_items"
    __table_args__ = (UniqueConstraint("carrito_id", "variante_id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("empresas.id"))
    carrito_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("carritos.id", ondelete="CASCADE"))
    variante_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("variantes.id"))
    cantidad: Mapped[int] = mapped_column(Integer)

    carrito: Mapped[Carrito] = relationship(back_populates="items")

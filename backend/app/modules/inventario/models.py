"""P5 · Inventario — existencias de cada variante por sucursal (base de CU-05; la Fase B agrega movimientos)."""
from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Existencia(Base):
    __tablename__ = "existencias"
    __table_args__ = (UniqueConstraint("sucursal_id", "variante_id"), CheckConstraint("disponible >= 0"))

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("empresas.id"))
    sucursal_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("sucursales.id"))
    variante_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("variantes.id", ondelete="CASCADE"))
    disponible: Mapped[int] = mapped_column(Integer, default=0)
    reservada: Mapped[int] = mapped_column(Integer, default=0)
    vendida: Mapped[int] = mapped_column(Integer, default=0)

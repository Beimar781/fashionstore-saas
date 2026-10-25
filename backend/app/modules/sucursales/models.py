"""P3 · Sucursales y proveedores — ciudades y sucursales de cada empresa (tenant)."""
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Ciudad(Base):
    __tablename__ = "ciudades"
    __table_args__ = (UniqueConstraint("empresa_id", "nombre"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("empresas.id"))
    nombre: Mapped[str] = mapped_column(String(80))
    departamento: Mapped[str | None] = mapped_column(String(80))


class Sucursal(Base):
    __tablename__ = "sucursales"
    __table_args__ = (
        UniqueConstraint("empresa_id", "nombre"),
        Index("ix_sucursales_empresa", "empresa_id", "activa"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("empresas.id"))
    ciudad_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("ciudades.id"))
    nombre: Mapped[str] = mapped_column(String(100))
    direccion: Mapped[str | None] = mapped_column(String(200))
    telefono: Mapped[str | None] = mapped_column(String(20))
    horario: Mapped[str | None] = mapped_column(String(100))
    activa: Mapped[bool] = mapped_column(Boolean, default=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    ciudad: Mapped[Ciudad] = relationship(lazy="joined")

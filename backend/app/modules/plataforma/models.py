"""P1 · Plataforma SaaS — entidades globales de la plataforma (no pertenecen a un tenant)."""
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constantes import EMPRESA_ACTIVA, SUS_ACTIVA
from app.core.database import Base


class Plan(Base):
    __tablename__ = "planes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(50), unique=True)
    descripcion: Mapped[str | None] = mapped_column(Text)
    precio: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    periodicidad: Mapped[str] = mapped_column(String(20), default="mensual")
    max_sucursales: Mapped[int] = mapped_column(Integer)
    reportes_ia: Mapped[bool] = mapped_column(Boolean, default=False)
    offline: Mapped[bool] = mapped_column(Boolean, default=True)
    reportes_convencionales: Mapped[bool] = mapped_column(Boolean, default=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)


class Empresa(Base):
    """Tenant. Su `id` es el `empresa_id` del resto de tablas."""

    __tablename__ = "empresas"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    codigo: Mapped[str] = mapped_column(String(30), unique=True)
    razon_social: Mapped[str] = mapped_column(String(120))
    nit: Mapped[str] = mapped_column(String(20), unique=True)
    email_contacto: Mapped[str | None] = mapped_column(String(120))
    telefono: Mapped[str | None] = mapped_column(String(20))
    estado: Mapped[str] = mapped_column(String(15), default=EMPRESA_ACTIVA)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Suscripcion(Base):
    __tablename__ = "suscripciones"
    __table_args__ = (
        Index("ux_suscripcion_activa", "empresa_id", unique=True, postgresql_where=text("estado = 'ACTIVA'")),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("empresas.id"))
    plan_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("planes.id"))
    fecha_inicio: Mapped[date] = mapped_column(Date)
    fecha_vencimiento: Mapped[date] = mapped_column(Date)
    estado: Mapped[str] = mapped_column(String(15), default=SUS_ACTIVA)
    forma_pago: Mapped[str | None] = mapped_column(String(20))
    monto: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    plan: Mapped[Plan] = relationship(lazy="joined")

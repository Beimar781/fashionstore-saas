"""P9 · Ia — vestidor virtual y asistente (CU-06, CU-07): perfil de gustos del cliente."""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class InteraccionCliente(Base):
    """Algo que el cliente hizo y revela lo que le gusta: una búsqueda, una prenda que miró o lo que le pidió al asistente."""

    __tablename__ = "interacciones_cliente"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("empresas.id"))
    cliente_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("usuarios.id", ondelete="CASCADE"))
    tipo: Mapped[str] = mapped_column(String(10))  # BUSQUEDA | VISTA | ASISTENTE
    texto: Mapped[str | None] = mapped_column(String(120))
    producto_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("productos.id", ondelete="CASCADE"))
    categoria_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("categorias.id", ondelete="SET NULL"))
    color_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("colores.id", ondelete="SET NULL"))
    talla: Mapped[str | None] = mapped_column(String(8))
    precio_max: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PreferenciaCliente(Base):
    """El cliente decide si el sistema aprende de lo que hace. Sin fila, se aprende (valor por defecto)."""

    __tablename__ = "preferencias_cliente"

    cliente_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("usuarios.id", ondelete="CASCADE"), primary_key=True)
    empresa_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("empresas.id"))
    personalizar: Mapped[bool] = mapped_column(Boolean, default=True)

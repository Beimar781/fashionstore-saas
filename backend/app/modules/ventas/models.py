"""P7 · Ventas (SaaS) — devoluciones y cambios de prendas (CU-41) y configuración de ventas de la empresa."""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, BigInteger, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ConfiguracionVentas(Base):
    """Plazo (en días desde el pago) dentro del cual se acepta una devolución o cambio (RN15). Una fila por empresa."""

    __tablename__ = "configuracion_ventas"

    empresa_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("empresas.id"), primary_key=True)
    plazo_devolucion_dias: Mapped[int] = mapped_column(Integer, default=15)


class SecuenciaNotaDevolucion(Base):
    __tablename__ = "secuencias_nota_devolucion"

    empresa_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("empresas.id"), primary_key=True)
    sucursal_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("sucursales.id"), primary_key=True)
    ultimo: Mapped[int] = mapped_column(Integer, default=0)


class Devolucion(Base):
    """Nota de devolución: qué prendas volvieron al inventario, cuáles se entregaron en un cambio y qué dinero se movió."""

    __tablename__ = "devoluciones"
    __table_args__ = (UniqueConstraint("empresa_id", "numero"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("empresas.id"))
    numero: Mapped[str] = mapped_column(String(30))
    pedido_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("pedidos.id"))
    sucursal_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("sucursales.id"))
    tipo: Mapped[str] = mapped_column(String(10))
    motivo: Mapped[str] = mapped_column(String(200))
    monto_devuelto: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    monto_nuevo: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    reembolso: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    cobro_adicional: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    medio_reembolso: Mapped[str | None] = mapped_column(String(10))
    referencia_reembolso: Mapped[str | None] = mapped_column(String(80))
    reembolso_pasarela: Mapped[int | None] = mapped_column(Integer)
    medio_cobro: Mapped[str | None] = mapped_column(String(10))
    monto_recibido: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    cambio_entregado: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    referencia_cobro: Mapped[str | None] = mapped_column(String(80))
    cobro_pasarela: Mapped[int | None] = mapped_column(Integer)
    proveedor_cobro: Mapped[str | None] = mapped_column(String(10))
    cobro_tarjeta_marca: Mapped[str | None] = mapped_column(String(20))
    cobro_tarjeta_ultimos4: Mapped[str | None] = mapped_column(String(4))
    sin_danos: Mapped[bool] = mapped_column(Boolean, default=True)  # RN15: condición de la prenda verificada al recibirla
    sin_desgaste: Mapped[bool] = mapped_column(Boolean, default=True)
    con_etiquetas: Mapped[bool] = mapped_column(Boolean, default=True)
    registrada_por: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("usuarios.id"))
    creada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    items: Mapped[list["DevolucionItem"]] = relationship(back_populates="devolucion", cascade="all, delete-orphan", order_by="DevolucionItem.id")


class IntentoDiferencia(Base):
    """Cobro con tarjeta de la diferencia de un cambio: PENDIENTE → USADO (al registrarse el cambio) o CANCELADO."""

    __tablename__ = "intentos_diferencia"
    __table_args__ = (UniqueConstraint("empresa_id", "referencia"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("empresas.id"))
    pedido_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("pedidos.id"))
    usuario_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("usuarios.id"))
    monto: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    proveedor: Mapped[str] = mapped_column(String(10))
    referencia: Mapped[str] = mapped_column(String(80))
    monto_pasarela: Mapped[int] = mapped_column(Integer)
    moneda_pasarela: Mapped[str] = mapped_column(String(3))
    estado: Mapped[str] = mapped_column(String(12), default="PENDIENTE")
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DevolucionItem(Base):
    __tablename__ = "devolucion_items"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("empresas.id"))
    devolucion_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("devoluciones.id", ondelete="CASCADE"))
    sentido: Mapped[str] = mapped_column(String(10))  # DEVUELTA (vuelve al inventario) o ENTREGADA (prenda nueva de un cambio)
    pedido_item_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("pedido_items.id"))
    variante_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("variantes.id"))
    sku: Mapped[str] = mapped_column(String(40))
    producto: Mapped[str] = mapped_column(String(200))
    talla: Mapped[str] = mapped_column(String(8))
    color: Mapped[str] = mapped_column(String(50))
    cantidad: Mapped[int] = mapped_column(Integer)
    precio_final: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2))

    devolucion: Mapped[Devolucion] = relationship(back_populates="items")

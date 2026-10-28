"""P7 · Ventas — pedidos, pagos, tarjetas guardadas y comprobantes (primer parcial: CU-11, CU-12, CU-32; los usarán CU-29 y CU-30)."""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Pedido(Base):
    """Estados: PENDIENTE_PAGO → PAGADO; con un pago que no se pudo confirmar: PENDIENTE_CONFIRMACION; o CANCELADO."""

    __tablename__ = "pedidos"
    __table_args__ = (UniqueConstraint("empresa_id", "codigo"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("empresas.id"))
    codigo: Mapped[str] = mapped_column(String(16))
    cliente_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("usuarios.id"))
    sucursal_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("sucursales.id"))
    canal: Mapped[str] = mapped_column(String(10), default="DIGITAL")
    tipo_entrega: Mapped[str] = mapped_column(String(10))
    direccion_entrega: Mapped[str] = mapped_column(String(300), default="")
    nit_ci: Mapped[str] = mapped_column(String(20), default="")
    razon_social: Mapped[str] = mapped_column(String(120), default="")
    estado: Mapped[str] = mapped_column(String(24), default="PENDIENTE_PAGO")
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    descuento: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    iva_incluido: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    moneda: Mapped[str] = mapped_column(String(3), default="BOB")
    motivo_cancelacion: Mapped[str] = mapped_column(String(200), default="")
    comprobante_numero: Mapped[str | None] = mapped_column(String(30))
    creado_por: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("usuarios.id"))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    pagado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    items: Mapped[list["PedidoItem"]] = relationship(back_populates="pedido", cascade="all, delete-orphan", order_by="PedidoItem.id")


class PedidoItem(Base):
    __tablename__ = "pedido_items"
    __table_args__ = (UniqueConstraint("pedido_id", "variante_id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("empresas.id"))
    pedido_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("pedidos.id", ondelete="CASCADE"))
    variante_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("variantes.id"))
    sku: Mapped[str] = mapped_column(String(40))
    producto: Mapped[str] = mapped_column(String(200))
    talla: Mapped[str] = mapped_column(String(8))
    color: Mapped[str] = mapped_column(String(50))
    cantidad: Mapped[int] = mapped_column(Integer)
    precio_unitario: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    precio_final: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2))

    pedido: Mapped[Pedido] = relationship(back_populates="items")


class Pago(Base):
    """Estados: PENDIENTE → AUTORIZADO → APROBADO; o RECHAZADO, PENDIENTE_CONFIRMACION (la pasarela no respondió) o CANCELADO."""

    __tablename__ = "pagos"
    __table_args__ = (UniqueConstraint("empresa_id", "referencia_externa"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("empresas.id"))
    pedido_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("pedidos.id"))
    metodo: Mapped[str] = mapped_column(String(10))
    proveedor: Mapped[str] = mapped_column(String(10))
    estado: Mapped[str] = mapped_column(String(24), default="PENDIENTE")
    monto: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    moneda: Mapped[str] = mapped_column(String(3), default="BOB")
    monto_pasarela: Mapped[int | None] = mapped_column(Integer)
    moneda_pasarela: Mapped[str | None] = mapped_column(String(3))
    referencia_externa: Mapped[str | None] = mapped_column(String(80))
    metodo_pago_ref: Mapped[str | None] = mapped_column(String(80))
    guardar_tarjeta: Mapped[bool] = mapped_column(Boolean, default=False)
    tarjeta_marca: Mapped[str] = mapped_column(String(20), default="")
    tarjeta_ultimos4: Mapped[str] = mapped_column(String(4), default="")
    mensaje: Mapped[str] = mapped_column(String(300), default="")
    motivo: Mapped[str] = mapped_column(String(200), default="")
    usuario_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("usuarios.id"))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    actualizado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ClientePasarela(Base):
    """Cliente del cliente en la pasarela (Customer de Stripe), para reutilizar sus tarjetas guardadas."""

    __tablename__ = "clientes_pasarela"
    __table_args__ = (UniqueConstraint("empresa_id", "cliente_id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("empresas.id"))
    cliente_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("usuarios.id"))
    referencia: Mapped[str] = mapped_column(String(80))


class TarjetaGuardada(Base):
    """Solo marca, últimos 4 dígitos y vencimiento: el número completo y el CVC nunca llegan a nuestra base."""

    __tablename__ = "tarjetas_guardadas"
    __table_args__ = (UniqueConstraint("empresa_id", "cliente_id", "referencia"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("empresas.id"))
    cliente_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("usuarios.id"))
    proveedor: Mapped[str] = mapped_column(String(10))
    referencia: Mapped[str] = mapped_column(String(80))
    marca: Mapped[str] = mapped_column(String(20))
    ultimos4: Mapped[str] = mapped_column(String(4))
    exp_mes: Mapped[int] = mapped_column(Integer)
    exp_anio: Mapped[int] = mapped_column(Integer)
    escenario: Mapped[str] = mapped_column(String(30), default="")
    creada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SecuenciaComprobante(Base):
    """Último número de comprobante emitido por sucursal."""

    __tablename__ = "secuencias_comprobante"

    empresa_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("empresas.id"), primary_key=True)
    sucursal_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("sucursales.id"), primary_key=True)
    ultimo: Mapped[int] = mapped_column(Integer, default=0)

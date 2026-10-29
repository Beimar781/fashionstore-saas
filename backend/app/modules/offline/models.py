"""P8 · Offline — operaciones recibidas de los clientes sin conexión (CU-37 a CU-40)."""
import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class OperacionOffline(Base):
    """Una operación hecha sin conexión y ya procesada por el servidor. Estados: CONFIRMADA, RECHAZADA o EN_CONFLICTO (RN11, RN14).
    Los estados REGISTRADA_LOCAL y ENVIADA existen solo en el cliente, mientras la operación no llega al servidor."""

    __tablename__ = "operaciones_offline"
    __table_args__ = (UniqueConstraint("empresa_id", "operacion_id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("empresas.id"))
    operacion_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))  # lo genera el cliente
    usuario_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("usuarios.id"))
    sucursal_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("sucursales.id"))
    tipo: Mapped[str] = mapped_column(String(14))  # VENTA_CONTADO | RESERVA
    estado: Mapped[str] = mapped_column(String(12))
    payload: Mapped[dict] = mapped_column(JSONB)
    creada_en_cliente: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    recibida_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    procesada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    mensaje: Mapped[str] = mapped_column(String(400), default="")
    referencia: Mapped[str | None] = mapped_column(String(30))
    comprobante: Mapped[str | None] = mapped_column(String(30))
    detalle: Mapped[dict | None] = mapped_column(JSONB)
    pedido_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("pedidos.id"))
    reserva_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("reservas.id"))
    intentos: Mapped[int] = mapped_column(Integer, default=1)
    resolucion: Mapped[str | None] = mapped_column(String(12))  # REINTENTADA | DESCARTADA
    resuelta_por: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("usuarios.id"))
    resuelta_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    motivo_resolucion: Mapped[str | None] = mapped_column(String(200))

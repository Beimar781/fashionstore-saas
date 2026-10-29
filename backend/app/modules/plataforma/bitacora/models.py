"""Bitácora del sistema (Fase J): función transversal, no un caso de uso. Solo se agrega: no hay forma de editar ni borrar un registro."""
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Bitacora(Base):
    __tablename__ = "bitacora"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    empresa_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("empresas.id"))  # vacío: operación de la plataforma
    usuario_id: Mapped[int | None] = mapped_column(BigInteger)
    usuario: Mapped[str] = mapped_column(String(150))  # nombre guardado en ese momento (o el correo de un intento fallido)
    rol: Mapped[str | None] = mapped_column(String(30))
    accion: Mapped[str] = mapped_column(String(30))
    entidad: Mapped[str] = mapped_column(String(40))
    entidad_id: Mapped[int | None] = mapped_column(BigInteger)
    detalle: Mapped[str] = mapped_column(String(400))
    ip: Mapped[str | None] = mapped_column(String(45))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

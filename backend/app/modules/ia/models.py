"""P9 · Ia — reportes generativos y analítica con ML (CU-23, CU-42) y registro del uso de la IA."""
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ReporteGenerado(Base):
    """Un reporte pedido en lenguaje natural: lo que se pidió, cómo se interpretó y lo que resultó."""

    __tablename__ = "reportes_generados"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("empresas.id"))
    usuario_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("usuarios.id"))
    prompt: Mapped[str] = mapped_column(String(500))
    especificacion: Mapped[dict] = mapped_column(JSONB)
    resultado: Mapped[dict] = mapped_column(JSONB)
    origen: Mapped[str] = mapped_column(String(10))  # IA (API externa) o REGLAS (modo de respaldo)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class UsoIA(Base):
    """Una consulta a una función de IA (reporte, asistente o analítica): sirve para mostrar el consumo del plan (CU-36)."""

    __tablename__ = "uso_ia"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("empresas.id"))
    usuario_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("usuarios.id"))
    funcion: Mapped[str] = mapped_column(String(12))
    origen: Mapped[str] = mapped_column(String(10))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

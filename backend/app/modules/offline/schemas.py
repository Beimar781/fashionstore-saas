"""Esquemas compartidos del paquete offline (CU-37 a CU-40)."""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

TIPOS = ("VENTA_CONTADO", "RESERVA")


class LineaOfflineIn(BaseModel):
    variante_id: int
    cantidad: int = Field(ge=1, le=50)


class VentaOfflineIn(BaseModel):
    """Venta de contado registrada sin conexión (RN13): lo que se llevó el cliente y el efectivo que se recibió."""

    items: list[LineaOfflineIn] = Field(min_length=1, max_length=60)
    monto_recibido: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    cliente_email: str | None = Field(default=None, max_length=120)
    nit_ci: str = Field(default="0", max_length=20)
    razon_social: str = Field(default="Sin nombre", max_length=120)


class OperacionIn(BaseModel):
    id: uuid.UUID  # RN11: lo genera el cliente al registrar la operación
    tipo: Literal["VENTA_CONTADO", "RESERVA"]
    creada_en: datetime  # cuándo se registró en el dispositivo
    sucursal_id: int | None = None
    payload: dict


class SincronizarIn(BaseModel):
    operaciones: list[OperacionIn] = Field(min_length=1, max_length=100)


class ResultadoOperacionOut(BaseModel):
    id: uuid.UUID
    estado: Literal["CONFIRMADA", "RECHAZADA", "EN_CONFLICTO", "ERROR"]  # ERROR: el servidor no pudo procesarla ahora; el cliente la reenvía
    mensaje: str
    referencia: str | None  # código del pedido o de la reserva que se creó
    comprobante: str | None
    detalle: dict | None  # en conflicto: qué prendas no alcanzaron
    ya_procesada: bool  # True si era un reenvío: se devuelve el resultado original (RN12)


class SincronizacionOut(BaseModel):
    resultados: list[ResultadoOperacionOut]
    sincronizado_en: datetime  # RN16


class OperacionOut(BaseModel):
    id: uuid.UUID
    tipo: str
    estado: str
    mensaje: str
    referencia: str | None
    comprobante: str | None
    detalle: dict | None
    sucursal_id: int
    sucursal: str
    usuario: str
    creada_en: datetime
    procesada_en: datetime
    intentos: int
    resolucion: str | None
    motivo_resolucion: str | None

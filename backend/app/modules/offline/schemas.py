"""Esquemas compartidos del paquete offline (CU-37 a CU-40)."""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, model_validator

TIPOS = ("VENTA_CONTADO", "RESERVA", "COMPRA", "CANCELAR_RESERVA")


class LineaOfflineIn(BaseModel):
    variante_id: int
    cantidad: int = Field(ge=1, le=50)
    precio_unitario: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)  # precio con que se registró sin conexión (§7.2)


class VentaOfflineIn(BaseModel):
    """Venta de contado registrada sin conexión (RN13): lo que se llevó el cliente y el efectivo que se recibió."""

    items: list[LineaOfflineIn] = Field(min_length=1, max_length=60)
    monto_recibido: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    forma_pago: Literal["EFECTIVO"] = "EFECTIVO"  # RN13: de contado; el campo queda preparado para otras formas de pago
    cliente_email: str | None = Field(default=None, max_length=120)
    nit_ci: str = Field(default="0", max_length=20)
    razon_social: str = Field(default="Sin nombre", max_length=120)


class CompraOfflineIn(BaseModel):
    """Compra del cliente armada sin conexión: un pedido por pagar; la tarjeta se cobra en línea cuando sincroniza (no se guardan datos de tarjeta)."""

    sucursal_id: int
    tipo_entrega: Literal["DELIVERY", "RETIRO"] = "RETIRO"
    direccion_entrega: str = Field(default="", max_length=300)
    items: list[LineaOfflineIn] = Field(min_length=1, max_length=60)
    nit_ci: str = Field(default="0", max_length=20)
    razon_social: str = Field(default="Sin nombre", max_length=120)

    @model_validator(mode="after")
    def validar_entrega(self):
        if self.tipo_entrega == "DELIVERY" and not self.direccion_entrega.strip():
            raise ValueError("Ingrese la dirección de entrega.")
        return self


class OperacionIn(BaseModel):
    id: uuid.UUID  # RN11: lo genera el cliente al registrar la operación
    tipo: Literal["VENTA_CONTADO", "RESERVA", "COMPRA", "CANCELAR_RESERVA"]
    creada_en: datetime  # cuándo se registró en el dispositivo
    sucursal_id: int | None = None
    payload: dict


class SincronizarIn(BaseModel):
    operaciones: list[OperacionIn] = Field(min_length=1, max_length=100)
    hora_dispositivo: datetime | None = None  # la hora del dispositivo al enviar: sirve para detectar un reloj mal puesto (§7.2)


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
    desfase_reloj_segundos: int | None = None  # hora del dispositivo menos hora del servidor, si el cliente la envió
    aviso_reloj: str | None = None  # presente si la diferencia supera los 5 minutos


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

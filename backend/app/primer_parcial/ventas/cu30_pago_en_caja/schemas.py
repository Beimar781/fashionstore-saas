from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from app.core.tipos import Dinero
from app.primer_parcial.ventas.cu11_compra_digital.schemas import PagoResumenOut, PedidoOut


class CobroIn(BaseModel):
    """Efectivo y QR se confirman en caja. El pago con tarjeta usa la pasarela de CU-32 (`/api/pagos/...`)."""

    metodo: Literal["EFECTIVO", "QR"]
    monto_recibido: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)


class CobroOut(BaseModel):
    pedido: PedidoOut
    pago: PagoResumenOut
    cambio: Dinero  # lo que se devuelve al cliente (solo efectivo)
    aviso: str | None  # «Falla de red con el servicio de impuestos…» cuando el comprobante es interno temporal

from datetime import datetime

from pydantic import BaseModel

from app.core.tipos import Dinero
from app.primer_parcial.ventas.cu11_compra_digital.schemas import PedidoOut  # noqa: F401  (detalle de un pedido)


class CompraResumenOut(BaseModel):
    id: int
    codigo: str
    fecha: datetime
    sucursal: str
    canal: str
    estado: str
    total: Dinero
    total_unidades: int
    comprobante_numero: str | None


class HistorialOut(BaseModel):
    compras: list[CompraResumenOut]
    mensaje: str | None  # «Aún no has realizado ninguna compra en nuestras tiendas.» cuando no hay registros

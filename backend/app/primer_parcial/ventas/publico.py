"""Interfaz pública del paquete P7 ventas (primer parcial) para otros paquetes.

La venta presencial (CU-29, SaaS), las devoluciones (CU-41) y los reportes usan los pedidos solo desde aquí.
"""
from app.primer_parcial.ventas.cu11_compra_digital.schemas import PagoResumenOut, PedidoOut  # noqa: F401
from app.primer_parcial.ventas.cu11_compra_digital.service import Linea, CompraService, SinStock  # noqa: F401
from app.primer_parcial.ventas.cu28_productos_en_caja.service import sucursal_de_caja  # noqa: F401
from app.primer_parcial.ventas.models import Pago, Pedido, PedidoItem  # noqa: F401  (entidades de solo lectura para los reportes)

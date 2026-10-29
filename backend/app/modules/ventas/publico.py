"""Interfaz pública del paquete P7 ventas (SaaS) para otros paquetes."""
from app.modules.ventas.models import Devolucion, DevolucionItem  # noqa: F401  (entidades de solo lectura para los reportes)
from app.modules.ventas.cu29_venta_presencial.schemas import LineaIn, VentaIn  # noqa: F401,E402  (la venta de contado offline usa la venta de caja)
from app.modules.ventas.cu29_venta_presencial.service import VentaPresencialService  # noqa: F401,E402
from app.modules.ventas.cu29_venta_presencial.repository import VarianteVentaRepository  # noqa: F401,E402  (la compra offline del cliente arma su pedido con las prendas vendibles)
from app.modules.ventas.cu41_devoluciones.schemas import CondicionIn, DevolucionIn, DevolucionOut, ItemDevueltoIn  # noqa: F401,E402  (CU-40 devuelve el dinero de una venta descartada)
from app.modules.ventas.cu41_devoluciones.service import DevolucionService  # noqa: F401,E402

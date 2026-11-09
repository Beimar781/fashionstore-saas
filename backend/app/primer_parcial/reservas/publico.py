"""Interfaz pública del paquete P6 reservas (primer parcial) para otros paquetes.

La compra digital (ventas) lee el carrito del cliente y lo vacía al cobrar solo desde aquí.
"""
from app.primer_parcial.reservas.cu08_carrito.schemas import CarritoOut, ItemCarritoOut  # noqa: F401
from app.primer_parcial.reservas.cu08_carrito.service import CarritoService  # noqa: F401
from app.primer_parcial.reservas.cu24_gestionar_reservas_sucursal.service import ReservasSucursalService  # noqa: F401  (la cola offline atiende reservas con él)
from app.primer_parcial.reservas.cu25_confirmar_atencion.schemas import CompletarIn  # noqa: F401
from app.primer_parcial.reservas.cu25_confirmar_atencion.service import AtencionService  # noqa: F401

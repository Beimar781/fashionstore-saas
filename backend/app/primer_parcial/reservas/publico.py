"""Interfaz pública del paquete P6 reservas (primer parcial) para otros paquetes.

La compra digital (ventas) lee el carrito del cliente y lo vacía al cobrar solo desde aquí.
"""
from app.primer_parcial.reservas.cu08_carrito.schemas import CarritoOut, ItemCarritoOut  # noqa: F401
from app.primer_parcial.reservas.cu08_carrito.service import CarritoService  # noqa: F401

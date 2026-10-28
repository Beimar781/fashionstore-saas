"""Interfaz pública del paquete P4 catálogo (primer parcial) para otros paquetes.

Los demás paquetes (consulta del catálogo, inventario, ventas...) leen el catálogo y calculan precios solo desde aquí.
"""
from app.primer_parcial.catalogo.cu19_promociones.service import Descuentos, aplicar_descuento, descuentos_vigentes
from app.primer_parcial.catalogo.models import (  # noqa: F401  (entidades de solo lectura para las consultas)
    Categoria, Coleccion, Color, ImagenProducto, Marca, Producto, Talla, Temporada, Variante,
)

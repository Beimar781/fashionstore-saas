"""Interfaz pública del paquete P4 catálogo (primer parcial) para otros paquetes.

Los demás paquetes (consulta del catálogo, inventario, ventas...) leen el catálogo y calculan precios solo desde aquí.
"""
from app.primer_parcial.catalogo.cu17_temporadas_colecciones.schemas import ColeccionOut  # noqa: F401
from app.primer_parcial.catalogo.cu17_temporadas_colecciones.service import TemporadaService
from app.primer_parcial.catalogo.cu19_promociones.service import Descuentos, aplicar_descuento, descuentos_vigentes
from app.primer_parcial.catalogo.models import (  # noqa: F401  (entidades de solo lectura para las consultas)
    Categoria, Coleccion, Color, ImagenProducto, Marca, Producto, Talla, Temporada, Variante,
)


def asignar_proveedor_a_coleccion(db, empresa_id: int, coleccion_id: int, proveedor_id: int | None):
    return TemporadaService(db, empresa_id).asignar_proveedor(coleccion_id, proveedor_id)


def _productos_activos(db, empresa_id: int) -> int:
    from sqlalchemy import func, select

    return db.scalar(select(func.count(Producto.id)).where(Producto.empresa_id == empresa_id, Producto.activo.is_(True))) or 0


from app.modules.plataforma.publico import registrar_medidor  # noqa: E402

registrar_medidor("productos", "Productos activos", _productos_activos)

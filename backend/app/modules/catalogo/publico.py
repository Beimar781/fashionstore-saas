"""Interfaz pública del paquete P4 catalogo (SaaS) para otros paquetes: el asistente (CU-07) busca prendas con la misma búsqueda del cliente (CU-04)."""
from app.modules.catalogo.cu03_consultar_catalogo.schemas import PrendaOut  # noqa: F401
from app.modules.catalogo.cu04_buscar_filtrar.schemas import FiltrosBusqueda  # noqa: F401
from app.modules.catalogo.cu04_buscar_filtrar.service import BusquedaService  # noqa: F401

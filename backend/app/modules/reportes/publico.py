"""Interfaz pública del paquete P10 reportes para otros paquetes: el reporte generativo y la analítica con ML (P9 ia) reutilizan sus consultas."""
from app.modules.reportes.base import ReportesBase, hoy_local, inicio_del_dia  # noqa: F401
from app.modules.reportes.repository import CERO, ReportesRepository  # noqa: F401

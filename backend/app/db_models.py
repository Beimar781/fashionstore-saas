"""Importa todos los modelos para que SQLAlchemy y Alembic conozcan el esquema completo.
Al agregar un paquete nuevo (catálogo, inventario, ...) se agrega aquí su `models`.
Dos zonas: `modules` (SaaS) y `primer_parcial` (casos de uso conservados del Anexo B)."""
# SaaS
from app.modules.acceso import models as _acceso  # noqa: F401
from app.modules.plataforma import models as _plataforma  # noqa: F401
from app.modules.plataforma.bitacora import models as _bitacora  # noqa: F401
from app.modules.sucursales import models as _sucursales  # noqa: F401
from app.modules.catalogo import models as _catalogo  # noqa: F401
from app.modules.inventario import models as _inventario  # noqa: F401
from app.modules.reservas import models as _reservas  # noqa: F401
from app.modules.ventas import models as _ventas  # noqa: F401
from app.modules.offline import models as _offline  # noqa: F401
from app.modules.ia import models as _ia  # noqa: F401
from app.modules.reportes import models as _reportes  # noqa: F401

# Primer parcial (Anexo B)
from app.primer_parcial.proveedores import models as _pp_proveedores  # noqa: F401
from app.primer_parcial.catalogo import models as _pp_catalogo  # noqa: F401
from app.primer_parcial.reservas import models as _pp_reservas  # noqa: F401
from app.primer_parcial.ventas import models as _pp_ventas  # noqa: F401
from app.primer_parcial.reportes import models as _pp_reportes  # noqa: F401
from app.primer_parcial.ia import models as _pp_ia  # noqa: F401

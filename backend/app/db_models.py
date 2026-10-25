"""Importa todos los modelos para que SQLAlchemy y Alembic conozcan el esquema completo.
Al agregar un paquete nuevo (catálogo, inventario, ...) se agrega aquí su `models`."""
from app.modules.acceso import models as _acceso  # noqa: F401
from app.modules.plataforma import models as _plataforma  # noqa: F401
from app.modules.sucursales import models as _sucursales  # noqa: F401

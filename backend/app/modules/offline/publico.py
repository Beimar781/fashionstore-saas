"""Interfaz pública del paquete P8 offline para otros paquetes."""
from app.modules.offline.repository import OperacionRepository  # noqa: E402
from app.modules.sucursales.publico import registrar_verificador_de_pendientes  # noqa: E402


def _operaciones_sin_resolver(db, empresa_id: int, sucursal_id: int) -> bool:
    return OperacionRepository(db, empresa_id).hay_conflictos(sucursal_id)


registrar_verificador_de_pendientes(_operaciones_sin_resolver)

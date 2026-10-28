"""Interfaz pública del paquete P6 reservas (SaaS) para otros paquetes.

La atención en la sucursal (CU-24, CU-25) y la venta presencial desde una reserva (CU-29) cambian el estado de la reserva y
liberan su stock solo a través de `ReservaService`; las notificaciones se envían con `notificar`.
"""
from app.modules.reservas.cu09_reservar.schemas import ReservaOut  # noqa: F401
from app.modules.reservas.cu09_reservar.service import TEXTO_ESTADO, ReservaService  # noqa: F401
from app.modules.reservas.models import Reserva, ReservaItem  # noqa: F401
from app.modules.reservas.rf11_notificaciones.service import notificar  # noqa: F401

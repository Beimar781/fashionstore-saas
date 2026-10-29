"""Tipos compartidos de los esquemas."""
from decimal import Decimal
from typing import Annotated

from pydantic import AfterValidator

# Importe con dos decimales siempre («99.00»), sin importar cómo llegó el valor.
Dinero = Annotated[Decimal, AfterValidator(lambda v: v.quantize(Decimal("0.01")))]


def iva_incluido(total: Decimal) -> Decimal:
    """Cuánto del total es IVA, cuando el precio ya lo incluye (porcentaje configurable, 13 % en Bolivia)."""
    from app.core.config import get_settings

    porcentaje = get_settings().iva_porcentaje
    return (total * porcentaje / (100 + porcentaje)).quantize(Decimal("0.01"), rounding="ROUND_HALF_UP")

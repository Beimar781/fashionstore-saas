"""Tipos compartidos de los esquemas."""
from decimal import Decimal
from typing import Annotated

from pydantic import AfterValidator

# Importe con dos decimales siempre («99.00»), sin importar cómo llegó el valor.
Dinero = Annotated[Decimal, AfterValidator(lambda v: v.quantize(Decimal("0.01")))]

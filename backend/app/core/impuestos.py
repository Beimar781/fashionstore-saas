"""Servicio de impuestos (facturación) de CU-30: adaptador con modo simulado (regla 12).

Todavía no hay un servicio real configurado, así que siempre se usa el simulado: autoriza el comprobante con un código de prueba.
Con `IMPUESTOS_SIMULAR_FALLA=true` en el .env simula que el servicio no responde, para ver el comprobante interno temporal de la ficha.
"""
import secrets
from dataclasses import dataclass
from decimal import Decimal

from app.core.config import get_settings

MSG_FALLA_IMPUESTOS = "Falla de red con el servicio de impuestos, se generará un comprobante interno temporal."  # excepción de la ficha CU-30


class ServicioImpuestosNoDisponible(Exception):
    pass


@dataclass
class Emision:
    tipo: str  # FACTURA | INTERNO_TEMPORAL
    autorizacion: str | None


class ImpuestosSimulado:
    def __init__(self, falla: bool = False):
        self.falla = falla

    def autorizar(self, nit_empresa: str, numero: str, total: Decimal) -> str:
        if self.falla:
            raise ServicioImpuestosNoDisponible("sin respuesta")
        return f"SIM-{secrets.token_hex(8).upper()}"


def emitir_comprobante(servicio, nit_empresa: str, numero: str, total: Decimal) -> Emision:
    """Pide la autorización fiscal; si el servicio no responde, la venta no se pierde: queda un comprobante interno temporal."""
    try:
        return Emision("FACTURA", servicio.autorizar(nit_empresa, numero, total))
    except ServicioImpuestosNoDisponible:
        return Emision("INTERNO_TEMPORAL", None)


def obtener_servicio_impuestos():
    return ImpuestosSimulado(falla=get_settings().impuestos_simular_falla)

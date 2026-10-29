"""Pasarela de pago de CU-32: Stripe en modo prueba, o una pasarela simulada cuando no hay claves en el .env.

Las dos hablan igual con el servicio. Con la simulada solo se aceptan tarjetas de prueba: ningún número real se procesa ni se guarda.
En ambas el pago se AUTORIZA primero y se COBRA (captura) recién cuando el stock está confirmado, así que si las prendas se agotan
mientras el cliente paga, la autorización se anula y no se cobra nada.
"""
import secrets
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.core.config import get_settings
from app.core.errors import DatosInvalidos

MOTIVO_BANCO = "Transacción denegada por su banco"  # mensaje de la ficha CU-32 (fondos insuficientes)
MOTIVOS = {
    "FONDOS_INSUFICIENTES": MOTIVO_BANCO,
    "RECHAZADA": MOTIVO_BANCO,
    "VENCIDA": "Su tarjeta está vencida.",
    "CVC_INCORRECTO": "El código de seguridad (CVC) es incorrecto.",
    "NO_ADMITIDA": "Este entorno solo admite tarjetas de prueba.",
}

# Tarjetas de prueba de la pasarela simulada (las mismas que usa Stripe en modo prueba, salvo la de tiempo de espera)
TARJETAS_PRUEBA = [
    {"numero": "4242 4242 4242 4242", "marca": "Visa", "escenario": "APROBADA", "resultado": "Pago aprobado"},
    {"numero": "5555 5555 5555 4444", "marca": "Mastercard", "escenario": "APROBADA", "resultado": "Pago aprobado"},
    {"numero": "4000 0000 0000 9995", "marca": "Visa", "escenario": "FONDOS_INSUFICIENTES", "resultado": "Rechazada: fondos insuficientes"},
    {"numero": "4000 0000 0000 0002", "marca": "Visa", "escenario": "RECHAZADA", "resultado": "Rechazada por el banco"},
    {"numero": "4000 0000 0000 0069", "marca": "Visa", "escenario": "VENCIDA", "resultado": "Rechazada: tarjeta vencida"},
    {"numero": "4000 0000 0000 0127", "marca": "Visa", "escenario": "CVC_INCORRECTO", "resultado": "Rechazada: CVC incorrecto"},
    {"numero": "4000 0000 0000 0119", "marca": "Visa", "escenario": "TIMEOUT", "resultado": "La pasarela no responde: queda pendiente de confirmación"},
]
_ESCENARIO_DE = {t["numero"].replace(" ", ""): t["escenario"] for t in TARJETAS_PRUEBA}


@dataclass
class Tarjeta:
    """Datos de la tarjeta que llegan solo a la pasarela simulada (con Stripe nunca pasan por nuestro servidor)."""

    numero: str
    mes: int
    anio: int
    cvc: str
    titular: str = ""


@dataclass
class Intento:
    referencia: str
    client_secret: str | None
    monto_pasarela: int  # centavos
    moneda_pasarela: str


@dataclass
class Reembolso:
    referencia: str
    centavos: int


@dataclass
class Resultado:
    estado: str  # AUTORIZADO | RECHAZADO | PENDIENTE_CONFIRMACION
    motivo: str = ""
    marca: str = ""
    ultimos4: str = ""
    metodo_ref: str = ""
    exp_mes: int = 0
    exp_anio: int = 0
    escenario: str = ""


def marca_de(numero: str) -> str:
    if numero.startswith("4"):
        return "Visa"
    if numero[:2] in {"51", "52", "53", "54", "55"} or 2221 <= int(numero[:4] or 0) <= 2720:
        return "Mastercard"
    if numero[:2] in {"34", "37"}:
        return "Amex"
    return "Tarjeta"


def _luhn(numero: str) -> bool:
    suma = 0
    for i, d in enumerate(reversed(numero)):
        n = int(d)
        if i % 2:
            n = n * 2 - 9 if n > 4 else n * 2
        suma += n
    return suma % 10 == 0


def centavos_a_reembolsar(monto_bob: Decimal, restante_bob: Decimal, restante_centavos: int) -> int:
    """Centavos de la pasarela que corresponden a un reembolso; el último reembolso de un pago devuelve exactamente lo que quede (sin descuadres por redondeo)."""
    if monto_bob >= restante_bob:
        return restante_centavos
    return min(max(int((monto_bob / Decimal(str(get_settings().tasa_bob_por_usd)) * 100).to_integral_value()), 1), restante_centavos)


def centavos_pasarela(monto_bob: Decimal) -> int:
    """Stripe no cobra en bolivianos: se cobra el equivalente en dólares (mínimo US$ 0,50)."""
    return max(int((monto_bob / Decimal(str(get_settings().tasa_bob_por_usd)) * 100).to_integral_value()), 50)


class PasarelaSimulada:
    proveedor = "SIMULADO"
    modo = "simulado"
    publishable_key = None

    def asegurar_cliente(self, email: str, nombre: str, previa: str | None) -> str:
        return previa or ""

    def crear_intento(self, *, monto_bob, descripcion, metadata, cliente_ref, metodo_ref, guardar) -> Intento:
        return Intento(f"sim_pi_{secrets.token_hex(10)}", None, centavos_pasarela(monto_bob), "usd")

    def confirmar(self, *, referencia: str, tarjeta: Tarjeta | None, escenario_guardado: str | None) -> Resultado:
        """Decide como lo haría el banco, según la tarjeta de prueba. Con una tarjeta guardada se repite el escenario con que se guardó."""
        if escenario_guardado:
            return self._resultado(escenario_guardado, "", "", 0, 0, f"sim_pm_{secrets.token_hex(6)}")
        if tarjeta is None:
            raise DatosInvalidos("Ingrese los datos de la tarjeta.")
        numero = "".join(c for c in tarjeta.numero if c.isdigit())
        if not (13 <= len(numero) <= 19) or not _luhn(numero):
            raise DatosInvalidos("El número de la tarjeta no es válido.")
        if not (3 <= len(tarjeta.cvc) <= 4 and tarjeta.cvc.isdigit()):
            raise DatosInvalidos("El código de seguridad (CVC) debe tener 3 o 4 dígitos.")
        if not (1 <= tarjeta.mes <= 12):
            raise DatosInvalidos("El mes de vencimiento no es válido.")
        hoy = date.today()
        anio = tarjeta.anio + 2000 if tarjeta.anio < 100 else tarjeta.anio
        escenario = _ESCENARIO_DE.get(numero, "NO_ADMITIDA")  # un número real jamás se procesa
        if (anio, tarjeta.mes) < (hoy.year, hoy.month):
            escenario = "VENCIDA"
        return self._resultado(escenario, marca_de(numero), numero[-4:], tarjeta.mes, anio, f"sim_pm_{secrets.token_hex(6)}")

    def consultar(self, referencia: str) -> Resultado:
        """Conciliación de un pago que no respondió: el banco terminó confirmándolo."""
        return Resultado("AUTORIZADO")

    def capturar(self, referencia: str) -> None:
        return None

    def cancelar(self, referencia: str) -> None:
        return None

    def reembolsar(self, referencia: str, monto_bob: Decimal, restante_bob: Decimal, restante_centavos: int) -> Reembolso:
        """Devolución del dinero de una compra con tarjeta: en la simulación el reembolso se marca como hecho."""
        return Reembolso(f"sim_re_{secrets.token_hex(8)}", centavos_a_reembolsar(monto_bob, restante_bob, restante_centavos))

    def eliminar_metodo(self, metodo_ref: str) -> None:
        return None

    @staticmethod
    def _resultado(escenario: str, marca: str, ultimos4: str, mes: int, anio: int, metodo_ref: str) -> Resultado:
        base = dict(marca=marca, ultimos4=ultimos4, exp_mes=mes, exp_anio=anio, metodo_ref=metodo_ref, escenario=escenario)
        if escenario == "APROBADA":
            return Resultado("AUTORIZADO", **base)
        if escenario == "TIMEOUT":
            return Resultado("PENDIENTE_CONFIRMACION", **base)
        return Resultado("RECHAZADO", motivo=MOTIVOS.get(escenario, MOTIVO_BANCO), **base)


class PasarelaStripe:
    """Stripe con claves de prueba. El número de la tarjeta lo captura Stripe.js en el navegador: aquí solo viaja el PaymentIntent."""

    proveedor = "STRIPE"
    modo = "stripe"

    def __init__(self, clave_secreta: str, clave_publica: str, sdk=None):
        if sdk is None:
            import stripe as sdk  # se importa aquí para que el sistema funcione aunque Stripe no esté configurado
        self.sdk = sdk
        self.clave = clave_secreta
        self.publishable_key = clave_publica

    def asegurar_cliente(self, email: str, nombre: str, previa: str | None) -> str:
        if previa:
            return previa
        return self.sdk.Customer.create(api_key=self.clave, email=email, name=nombre).id

    def crear_intento(self, *, monto_bob, descripcion, metadata, cliente_ref, metodo_ref, guardar) -> Intento:
        centavos = centavos_pasarela(monto_bob)
        params = dict(
            amount=centavos, currency="usd", capture_method="manual", payment_method_types=["card"],
            description=descripcion, metadata=metadata,
        )
        if cliente_ref:
            params["customer"] = cliente_ref
        if metodo_ref:
            params["payment_method"] = metodo_ref  # tarjeta guardada: el navegador solo confirma el pago
        elif guardar and cliente_ref:
            params["setup_future_usage"] = "on_session"  # Stripe guarda la tarjeta para las próximas compras
        pi = self.sdk.PaymentIntent.create(api_key=self.clave, **params)
        return Intento(pi.id, pi.client_secret, centavos, "usd")

    def confirmar(self, *, referencia: str, tarjeta=None, escenario_guardado=None) -> Resultado:
        """Consulta a Stripe cómo quedó el pago que el navegador confirmó."""
        try:
            pi = self.sdk.PaymentIntent.retrieve(referencia, api_key=self.clave, expand=["payment_method"])
        except self.sdk.APIConnectionError:
            return Resultado("PENDIENTE_CONFIRMACION")
        return self._resultado(pi)

    def consultar(self, referencia: str) -> Resultado:
        return self.confirmar(referencia=referencia)

    def capturar(self, referencia: str) -> None:
        pi = self.sdk.PaymentIntent.retrieve(referencia, api_key=self.clave)
        if pi.status == "requires_capture":
            self.sdk.PaymentIntent.capture(referencia, api_key=self.clave)

    def cancelar(self, referencia: str) -> None:
        try:
            self.sdk.PaymentIntent.cancel(referencia, api_key=self.clave)
        except self.sdk.StripeError:
            pass  # si ya estaba anulado o cobrado, no hay nada más que hacer

    def reembolsar(self, referencia: str, monto_bob: Decimal, restante_bob: Decimal, restante_centavos: int) -> Reembolso:
        """Reembolso (de prueba) del cobro en Stripe: devuelve el dinero a la misma tarjeta."""
        centavos = centavos_a_reembolsar(monto_bob, restante_bob, restante_centavos)
        r = self.sdk.Refund.create(api_key=self.clave, payment_intent=referencia, amount=centavos)
        return Reembolso(r.id, centavos)

    def eliminar_metodo(self, metodo_ref: str) -> None:
        try:
            self.sdk.PaymentMethod.detach(metodo_ref, api_key=self.clave)
        except self.sdk.StripeError:
            pass

    def _resultado(self, pi) -> Resultado:
        tarjeta = {}
        pm = getattr(pi, "payment_method", None)
        card = getattr(pm, "card", None) if pm is not None and not isinstance(pm, str) else None
        if card is not None:
            tarjeta = dict(marca=str(card.brand).capitalize(), ultimos4=card.last4, exp_mes=card.exp_month, exp_anio=card.exp_year, metodo_ref=pm.id)
        if pi.status in ("requires_capture", "succeeded"):
            return Resultado("AUTORIZADO", **tarjeta)
        if pi.status == "processing":
            return Resultado("PENDIENTE_CONFIRMACION", **tarjeta)
        if pi.status == "requires_payment_method":
            error = getattr(pi, "last_payment_error", None)
            codigo = (getattr(error, "decline_code", None) or getattr(error, "code", None) or "") if error else ""
            if not error:
                return Resultado("RECHAZADO", "El pago no fue completado.", **tarjeta)
            motivo = {"expired_card": MOTIVOS["VENCIDA"], "incorrect_cvc": MOTIVOS["CVC_INCORRECTO"]}.get(codigo, MOTIVO_BANCO)
            return Resultado("RECHAZADO", motivo, **tarjeta)
        if pi.status == "canceled":
            return Resultado("RECHAZADO", "El pago fue cancelado.", **tarjeta)
        return Resultado("RECHAZADO", "El pago requiere una verificación adicional que no se completó.", **tarjeta)


def obtener_pasarela():
    """Stripe si hay claves de prueba en el .env; si no, la pasarela simulada."""
    cfg = get_settings()
    if cfg.stripe_activo:
        return PasarelaStripe(cfg.stripe_secret_key, cfg.stripe_publishable_key)
    return PasarelaSimulada()


def pasarela_para(proveedor: str):
    """La pasarela con la que se cobró un pago (para reembolsarlo). None si se cobró con Stripe y Stripe ya no está configurado."""
    actual = obtener_pasarela()
    if actual.proveedor == proveedor:
        return actual
    return PasarelaSimulada() if proveedor == "SIMULADO" else None

"""Stripe simulado en memoria para las pruebas: imita lo mínimo del SDK y guarda las llamadas para comprobarlas."""
from types import SimpleNamespace


class ErrorStripe(Exception):
    pass


class ErrorDeRed(ErrorStripe):
    pass


class StripeFalso:
    """Imita lo mínimo del SDK de Stripe que usa PasarelaStripe y guarda las llamadas para comprobarlas."""

    StripeError = ErrorStripe
    APIConnectionError = ErrorDeRed

    def __init__(self):
        self.llamadas: list[tuple] = []
        self.intentos: dict[str, SimpleNamespace] = {}
        self.sin_red = False
        self.Customer = SimpleNamespace(create=self._cliente)
        self.PaymentIntent = SimpleNamespace(create=self._crear, retrieve=self._consultar, capture=self._capturar, cancel=self._cancelar)
        self.PaymentMethod = SimpleNamespace(detach=lambda ref, **kw: self.llamadas.append(("detach", ref)))
        self.Refund = SimpleNamespace(create=self._reembolsar)

    def _cliente(self, **kw):
        self.llamadas.append(("cliente", kw["email"]))
        return SimpleNamespace(id="cus_prueba")

    def _crear(self, **kw):
        pi = SimpleNamespace(id=f"pi_{len(self.intentos) + 1}", client_secret=f"pi_{len(self.intentos) + 1}_secret", status="requires_payment_method",
                             payment_method=None, last_payment_error=None, params=kw)
        self.intentos[pi.id] = pi
        self.llamadas.append(("crear", kw))
        return pi

    def _consultar(self, ref, **kw):
        if self.sin_red:
            raise ErrorDeRed("sin conexión")
        return self.intentos[ref]

    def _capturar(self, ref, **kw):
        self.llamadas.append(("capturar", ref))
        self.intentos[ref].status = "succeeded"

    def _cancelar(self, ref, **kw):
        self.llamadas.append(("cancelar", ref))
        self.intentos[ref].status = "canceled"

    def _reembolsar(self, **kw):
        self.llamadas.append(("reembolsar", kw))
        return SimpleNamespace(id=f"re_{len(self.hizo('reembolsar'))}")

    def autorizar(self, ref, marca="visa", ultimos4="4242"):
        """Lo que ocurre cuando Stripe.js confirma la tarjeta en el navegador."""
        pi = self.intentos[ref]
        pi.status = "requires_capture"
        pi.payment_method = SimpleNamespace(id="pm_prueba", card=SimpleNamespace(brand=marca, last4=ultimos4, exp_month=12, exp_year=2099))

    def rechazar(self, ref, decline_code):
        pi = self.intentos[ref]
        pi.status = "requires_payment_method"
        pi.last_payment_error = SimpleNamespace(decline_code=decline_code, code="card_declined")

    def hizo(self, nombre):
        return [c for c in self.llamadas if c[0] == nombre]

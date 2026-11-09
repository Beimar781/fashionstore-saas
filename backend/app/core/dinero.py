"""Dinero de FashionStore: todo se cobra, se registra y se muestra en bolivianos (BOB), sin conversión de moneda."""
from decimal import ROUND_HALF_UP, Decimal

MONEDA_PAGO = "bob"  # moneda del PaymentIntent de Stripe (único lugar donde se define)
MINIMO_PAGO_BS = Decimal("3.50")  # mínimo para cobrar con tarjeta, equivalente aproximado al mínimo de Stripe (US$ 0,50)


def bs_a_centavos(monto) -> int:
    """Bolivianos a centavos (total × 100, redondeado al centavo más cercano)."""
    return int((Decimal(str(monto)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def formato_bs(valor) -> str:
    """Formato único del dinero: «Bs 1.250,50»."""
    texto = f"{Decimal(str(valor)):,.2f}"  # 1,250.50
    return "Bs " + texto.replace(",", "_").replace(".", ",").replace("_", ".")


def precio_plan_texto(precio, periodicidad: str) -> str:
    """Precio de un plan para mostrar: «Bs 150 / mes» (sin decimales si es un monto entero)."""
    valor = Decimal(str(precio))
    texto = f"Bs {int(valor):,}".replace(",", ".") if valor == valor.to_integral_value() else formato_bs(valor)
    return f"{texto} / {'año' if periodicidad == 'anual' else 'mes'}"

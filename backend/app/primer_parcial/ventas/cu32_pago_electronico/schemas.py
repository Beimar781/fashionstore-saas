from pydantic import BaseModel, ConfigDict, Field

from app.core.tipos import Dinero
from app.primer_parcial.ventas.cu11_compra_digital.schemas import PagoResumenOut, PedidoOut


class TarjetaPruebaOut(BaseModel):
    numero: str
    marca: str
    resultado: str


class ConfigPagoOut(BaseModel):
    modo: str  # «stripe» (claves de prueba en el .env) o «simulado»
    publishable_key: str | None
    tarjetas_prueba: list[TarjetaPruebaOut]  # solo en modo simulado: sirven para ver cómo aprueba o rechaza el sistema
    moneda_pasarela: str
    tasa_bob_por_usd: float


class TarjetaGuardadaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    marca: str
    ultimos4: str
    exp_mes: int
    exp_anio: int


class IniciarIn(BaseModel):
    tarjeta_guardada_id: int | None = None
    guardar_tarjeta: bool = False  # guardar la tarjeta que se use ahora para próximas compras


class IniciarOut(BaseModel):
    pago_id: int
    modo: str
    publishable_key: str | None
    client_secret: str | None  # solo con Stripe: lo usa Stripe.js en el navegador para confirmar el pago
    monto: Dinero
    moneda: str
    monto_pasarela: float  # lo que se cobra en la pasarela (dólares)
    moneda_pasarela: str
    tarjeta_guardada: TarjetaGuardadaOut | None


class TarjetaIn(BaseModel):
    """Solo la pasarela simulada recibe estos datos; con Stripe nunca pasan por el servidor."""

    numero: str = Field(min_length=1, max_length=25)
    mes: int
    anio: int
    cvc: str = Field(max_length=6)
    titular: str = Field(default="", max_length=80)


class ConfirmarIn(BaseModel):
    tarjeta: TarjetaIn | None = None


class ResultadoPagoOut(BaseModel):
    aprobado: bool
    pendiente: bool  # pendiente de confirmación: la pasarela no respondió
    mensaje: str
    pago: PagoResumenOut
    pedido: PedidoOut

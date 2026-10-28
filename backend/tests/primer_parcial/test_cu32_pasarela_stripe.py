"""CU-32 con Stripe: el adaptador y el flujo completo contra un Stripe simulado en memoria (las pruebas nunca llaman a Stripe)."""
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.modules.acceso.dependencias import Contexto
from app.modules.acceso.models import Usuario
from app.primer_parcial.ventas.cu11_compra_digital.service import SinStock
from app.primer_parcial.ventas.cu32_pago_electronico import schemas
from app.primer_parcial.ventas.cu32_pago_electronico.pasarela import MOTIVO_BANCO, PasarelaStripe
from app.primer_parcial.ventas.cu32_pago_electronico.service import PagoRechazado, PagoService
from app.primer_parcial.ventas.models import ClientePasarela, Pago, Pedido, TarjetaGuardada
from tests.compras_util import agregar_ok, checkout_ok, existencias, stock_listo


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


@pytest.fixture
def stripe_falso():
    return StripeFalso()


@pytest.fixture
def pasarela(stripe_falso):
    return PasarelaStripe("sk_test_falsa", "pk_test_falsa", sdk=stripe_falso)


def _servicio(db, mundo, pasarela):
    cliente = db.query(Usuario).filter_by(empresa_id=mundo.a.id, email="cliente@tienda.com").one()
    return PagoService(db, Contexto(cliente, "Cliente", mundo.a.id, None), pasarela)


def _pedido(inv, mundo, client, cantidad=2):
    stock_listo(inv, mundo)
    agregar_ok(client, inv.h_cliente, inv.v_sm_rojo, inv.centro, cantidad)
    return checkout_ok(client, inv.h_cliente)


# ---- el adaptador ----
def test_01_crear_el_intento_cobra_en_dolares_con_captura_manual(pasarela, stripe_falso):
    i = pasarela.crear_intento(monto_bob=Decimal("200.00"), descripcion="Pedido X", metadata={"pedido": "X"}, cliente_ref="cus_1", metodo_ref=None, guardar=True)
    p = stripe_falso.intentos[i.referencia].params
    assert (p["amount"], p["currency"], p["capture_method"], p["customer"], p["setup_future_usage"]) == (2874, "usd", "manual", "cus_1", "on_session")
    assert i.client_secret == f"{i.referencia}_secret" and i.monto_pasarela == 2874 and i.moneda_pasarela == "usd"
    guardada = pasarela.crear_intento(monto_bob=Decimal("10"), descripcion="", metadata={}, cliente_ref="cus_1", metodo_ref="pm_guardado", guardar=False)
    p2 = stripe_falso.intentos[guardada.referencia].params
    assert p2["payment_method"] == "pm_guardado" and "setup_future_usage" not in p2
    assert guardada.monto_pasarela == 144  # 10 / 6,96 → US$ 1,44


def test_02_el_monto_minimo_de_stripe(pasarela):
    assert pasarela.crear_intento(monto_bob=Decimal("1.00"), descripcion="", metadata={}, cliente_ref=None, metodo_ref=None, guardar=False).monto_pasarela == 50


def test_03_leer_la_respuesta_de_stripe(pasarela, stripe_falso):
    ref = pasarela.crear_intento(monto_bob=Decimal("100"), descripcion="", metadata={}, cliente_ref=None, metodo_ref=None, guardar=False).referencia
    stripe_falso.autorizar(ref)
    r = pasarela.confirmar(referencia=ref)
    assert (r.estado, r.marca, r.ultimos4, r.metodo_ref, r.exp_mes, r.exp_anio) == ("AUTORIZADO", "Visa", "4242", "pm_prueba", 12, 2099)
    for decline, motivo in (("insufficient_funds", MOTIVO_BANCO), ("generic_decline", MOTIVO_BANCO), ("expired_card", "Su tarjeta está vencida."),
                            ("incorrect_cvc", "El código de seguridad (CVC) es incorrecto.")):
        stripe_falso.rechazar(ref, decline)
        r = pasarela.confirmar(referencia=ref)
        assert (r.estado, r.motivo) == ("RECHAZADO", motivo)
    stripe_falso.intentos[ref].last_payment_error = None
    assert pasarela.confirmar(referencia=ref).motivo == "El pago no fue completado."
    stripe_falso.intentos[ref].status = "processing"
    assert pasarela.confirmar(referencia=ref).estado == "PENDIENTE_CONFIRMACION"
    stripe_falso.sin_red = True
    assert pasarela.confirmar(referencia=ref).estado == "PENDIENTE_CONFIRMACION"  # timeout: queda por conciliar


def test_04_capturar_solo_si_esta_autorizado_y_cancelar_sin_fallar(pasarela, stripe_falso):
    ref = pasarela.crear_intento(monto_bob=Decimal("100"), descripcion="", metadata={}, cliente_ref=None, metodo_ref=None, guardar=False).referencia
    pasarela.capturar(ref)
    assert stripe_falso.hizo("capturar") == []  # todavía no estaba autorizado
    stripe_falso.autorizar(ref)
    pasarela.capturar(ref)
    assert stripe_falso.hizo("capturar") == [("capturar", ref)]
    stripe_falso.PaymentIntent.cancel = lambda *a, **k: (_ for _ in ()).throw(ErrorStripe("ya cobrado"))
    pasarela.cancelar(ref)  # un error al cancelar no rompe el flujo
    pasarela.eliminar_metodo("pm_x")


# ---- el flujo completo con Stripe ----
def test_05_pago_aprobado_con_stripe_guarda_la_tarjeta(inv, mundo, client, db, pasarela, stripe_falso):
    p = _pedido(inv, mundo, client)
    servicio = _servicio(db, mundo, pasarela)
    i = servicio.iniciar(p["id"], schemas.IniciarIn(guardar_tarjeta=True))
    assert i.modo == "stripe" and i.publishable_key == "pk_test_falsa" and i.client_secret and i.monto_pasarela == 28.74
    assert db.query(ClientePasarela).filter_by(empresa_id=mundo.a.id).one().referencia == "cus_prueba"  # Customer creado una sola vez
    assert stripe_falso.intentos[db.get(Pago, i.pago_id).referencia_externa].params["setup_future_usage"] == "on_session"
    stripe_falso.autorizar(db.get(Pago, i.pago_id).referencia_externa)  # el navegador confirmó la tarjeta con Stripe.js
    r = servicio.confirmar(i.pago_id, schemas.ConfirmarIn())
    assert r.aprobado and r.pedido.estado == "PAGADO" and r.pago.tarjeta_ultimos4 == "4242"
    assert len(stripe_falso.hizo("capturar")) == 1  # se cobró una vez, después de descontar el stock
    f = existencias(client, inv.h_enc_centro, inv.v_sm_rojo)
    assert (f["disponible"], f["vendida"]) == (8, 2)
    t = db.query(TarjetaGuardada).filter_by(empresa_id=mundo.a.id).one()
    assert (t.proveedor, t.referencia, t.marca, t.ultimos4) == ("STRIPE", "pm_prueba", "Visa", "4242")
    # siguiente compra con la tarjeta guardada: el intento lleva su método de pago y el mismo Customer
    agregar_ok(client, inv.h_cliente, inv.v_sm_rojo, inv.centro, 1)
    p2 = checkout_ok(client, inv.h_cliente)
    i2 = servicio.iniciar(p2["id"], schemas.IniciarIn(tarjeta_guardada_id=t.id))
    params = stripe_falso.intentos[db.get(Pago, i2.pago_id).referencia_externa].params
    assert params["payment_method"] == "pm_prueba" and params["customer"] == "cus_prueba"
    assert len(stripe_falso.hizo("cliente")) == 1


def test_06_tarjeta_rechazada_en_stripe(inv, mundo, client, db, pasarela, stripe_falso):
    p = _pedido(inv, mundo, client)
    servicio = _servicio(db, mundo, pasarela)
    i = servicio.iniciar(p["id"], schemas.IniciarIn())
    stripe_falso.rechazar(db.get(Pago, i.pago_id).referencia_externa, "insufficient_funds")
    with pytest.raises(PagoRechazado) as e:
        servicio.confirmar(i.pago_id, schemas.ConfirmarIn())
    assert e.value.extra["motivo"] == "Transacción denegada por su banco"
    assert stripe_falso.hizo("capturar") == [] and db.get(Pedido, p["id"]).estado == "PENDIENTE_PAGO"


def test_07_si_el_stock_se_agota_se_anula_la_autorizacion_y_no_se_cobra(inv, mundo, client, db, pasarela, stripe_falso):
    p = _pedido(inv, mundo, client, cantidad=5)
    servicio = _servicio(db, mundo, pasarela)
    i = servicio.iniciar(p["id"], schemas.IniciarIn())
    ref = db.get(Pago, i.pago_id).referencia_externa
    stripe_falso.autorizar(ref)  # la tarjeta quedó autorizada en el navegador…
    client.post("/api/inventario/sucursal/movimientos", json={"variante_id": inv.v_sm_rojo["id"], "tipo": "AJUSTE_SALIDA", "cantidad": 8, "nota": "Merma"}, headers=inv.h_enc_centro)
    with pytest.raises(SinStock):  # …y mientras tanto el stock se agotó
        servicio.confirmar(i.pago_id, schemas.ConfirmarIn())
    assert stripe_falso.hizo("capturar") == [] and stripe_falso.hizo("cancelar") == [("cancelar", ref)]  # se anula: no se cobra
    db.expire_all()
    assert (db.get(Pago, i.pago_id).estado, db.get(Pedido, p["id"]).estado) == ("CANCELADO", "CANCELADO")
    assert existencias(client, inv.h_enc_centro, inv.v_sm_rojo)["vendida"] == 0


def test_08_si_stripe_no_responde_queda_pendiente_de_confirmacion(inv, mundo, client, db, pasarela, stripe_falso):
    p = _pedido(inv, mundo, client)
    servicio = _servicio(db, mundo, pasarela)
    i = servicio.iniciar(p["id"], schemas.IniciarIn())
    stripe_falso.sin_red = True
    r = servicio.confirmar(i.pago_id, schemas.ConfirmarIn())
    assert r.pendiente and r.pedido.estado == "PENDIENTE_CONFIRMACION" and existencias(client, inv.h_enc_centro, inv.v_sm_rojo)["vendida"] == 0
    stripe_falso.sin_red = False
    stripe_falso.autorizar(db.get(Pago, i.pago_id).referencia_externa)
    r = servicio.reconciliar(i.pago_id)
    assert r.aprobado and r.pedido.estado == "PAGADO"


def test_09_si_stripe_falla_al_crear_el_intento(inv, mundo, client, db, pasarela, stripe_falso):
    from app.primer_parcial.ventas.cu32_pago_electronico.service import PasarelaNoDisponible

    p = _pedido(inv, mundo, client)
    stripe_falso.PaymentIntent.create = lambda **kw: (_ for _ in ()).throw(ErrorDeRed("sin conexión"))
    with pytest.raises(PasarelaNoDisponible) as e:
        _servicio(db, mundo, pasarela).iniciar(p["id"], schemas.IniciarIn())
    assert e.value.message == "No se pudo comunicar con la pasarela de pago. Intente nuevamente." and e.value.status_code == 502


def test_10_las_tarjetas_de_otra_pasarela_no_se_usan(inv, mundo, client, db, pasarela):
    p = _pedido(inv, mundo, client)
    cliente = db.query(Usuario).filter_by(empresa_id=mundo.a.id, email="cliente@tienda.com").one()
    t = TarjetaGuardada(empresa_id=mundo.a.id, cliente_id=cliente.id, proveedor="SIMULADO", referencia="sim_pm_x", marca="Visa", ultimos4="4242", exp_mes=12, exp_anio=2099)
    db.add(t)
    db.commit()
    servicio = _servicio(db, mundo, pasarela)
    assert servicio.listar_tarjetas() == []  # con Stripe activo no se muestran las tarjetas de la simulación
    from app.core.errors import NoEncontrado

    with pytest.raises(NoEncontrado):
        servicio.iniciar(p["id"], schemas.IniciarIn(tarjeta_guardada_id=t.id))

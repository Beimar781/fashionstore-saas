"""Datos de ejemplo de la compra digital (Fase D): el cliente demo de cada empresa ya tiene una compra pagada y un carrito. Idempotente."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.constantes import CLIENTE
from app.modules.acceso.dependencias import Contexto
from app.modules.acceso.models import Usuario
from app.modules.inventario.models import Existencia
from app.modules.sucursales.models import Sucursal
from app.primer_parcial.reservas.cu08_carrito.schemas import ItemIn
from app.primer_parcial.reservas.cu08_carrito.service import CarritoService
from app.primer_parcial.ventas.cu11_compra_digital.schemas import CheckoutIn
from app.primer_parcial.ventas.cu11_compra_digital.service import CompraService
from app.primer_parcial.ventas.cu32_pago_electronico import schemas
from app.primer_parcial.ventas.cu32_pago_electronico.pasarela import PasarelaSimulada
from app.primer_parcial.ventas.cu32_pago_electronico.service import PagoService
from app.primer_parcial.ventas.models import Pedido


def cargar(db: Session, empresa) -> None:
    cliente = db.scalar(select(Usuario).where(Usuario.empresa_id == empresa.id, Usuario.email == f"cliente@{empresa.codigo.lower()}.com"))
    sucursal = db.scalar(select(Sucursal).where(Sucursal.empresa_id == empresa.id, Sucursal.activa.is_(True)).order_by(Sucursal.id).limit(1))
    if cliente is None or sucursal is None or db.scalar(select(Pedido.id).where(Pedido.empresa_id == empresa.id, Pedido.cliente_id == cliente.id).limit(1)):
        return
    variantes = list(db.scalars(
        select(Existencia.variante_id).where(Existencia.sucursal_id == sucursal.id, Existencia.disponible >= 4).order_by(Existencia.variante_id.desc()).limit(2)
    ))
    if len(variantes) < 2:
        return
    ctx = Contexto(cliente, CLIENTE, empresa.id, None)
    carrito = CarritoService(db, empresa.id)
    carrito.agregar(cliente.id, ItemIn(variante_id=variantes[0], cantidad=2, sucursal_id=sucursal.id))
    pedido = CompraService(db, ctx).checkout(CheckoutIn(tipo_entrega="RETIRO", nit_ci="1234567", razon_social="Cliente Demo"))
    pagos = PagoService(db, ctx, PasarelaSimulada())  # el seed siempre usa la pasarela simulada, aunque haya claves de Stripe
    intento = pagos.iniciar(pedido.id, schemas.IniciarIn(guardar_tarjeta=True))
    pagos.confirmar(intento.pago_id, schemas.ConfirmarIn(tarjeta=schemas.TarjetaIn(numero="4242 4242 4242 4242", mes=12, anio=2099, cvc="123", titular="Cliente Demo")))
    carrito.agregar(cliente.id, ItemIn(variante_id=variantes[1], cantidad=1, sucursal_id=sucursal.id))  # carrito listo para probar el pago

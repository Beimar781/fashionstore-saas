"""Datos de ejemplo de ventas: compra digital del cliente demo (Fase D), ventas de caja (Fase E) y una devolución (Fase F). Idempotente."""
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.constantes import CAJERO, CLIENTE, ENCARGADO
from app.modules.acceso.dependencias import Contexto
from app.modules.acceso.models import Rol, Usuario
from app.modules.inventario.models import Existencia
from app.modules.sucursales.models import Sucursal
from app.modules.ventas.cu41_devoluciones.schemas import DevolucionIn, ItemDevueltoIn
from app.modules.ventas.cu41_devoluciones.service import DevolucionService
from app.modules.ventas.publico import Devolucion
from app.modules.ventas.cu29_venta_presencial.schemas import LineaIn, VentaIn
from app.modules.ventas.cu29_venta_presencial.service import VentaPresencialService
from app.primer_parcial.reservas.cu08_carrito.schemas import ItemIn
from app.primer_parcial.reservas.cu08_carrito.service import CarritoService
from app.primer_parcial.ventas.cu11_compra_digital.schemas import CheckoutIn
from app.primer_parcial.ventas.cu11_compra_digital.service import CompraService
from app.primer_parcial.ventas.cu30_pago_en_caja.schemas import CobroIn
from app.primer_parcial.ventas.cu30_pago_en_caja.service import CobroCajaService
from app.primer_parcial.ventas.cu32_pago_electronico import schemas
from app.primer_parcial.ventas.cu32_pago_electronico.pasarela import PasarelaSimulada
from app.primer_parcial.ventas.cu32_pago_electronico.service import PagoService
from app.primer_parcial.ventas.models import Pago, Pedido


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


def cargar_caja(db: Session, empresa) -> None:
    """Ventas de caja de ejemplo (Fase E): el Cajero y el Encargado de cada empresa venden en su sucursal (efectivo y tarjeta)."""
    if db.scalar(select(Pedido.id).where(Pedido.empresa_id == empresa.id, Pedido.canal == "PRESENCIAL").limit(1)):
        return
    for rol, medios in ((CAJERO, ("EFECTIVO", "EFECTIVO")), (ENCARGADO, ("EFECTIVO",))):
        empleado = db.scalar(select(Usuario).join(Usuario.rol).where(Usuario.empresa_id == empresa.id, Rol.nombre == rol, Usuario.sucursal_id.is_not(None)).order_by(Usuario.id).limit(1))
        if empleado is None:
            continue
        variantes = list(db.scalars(
            select(Existencia.variante_id).where(Existencia.sucursal_id == empleado.sucursal_id, Existencia.disponible >= 4).order_by(Existencia.variante_id).offset(4).limit(len(medios))
        ))
        ctx = Contexto(empleado, rol, empresa.id, empleado.sucursal_id)
        for variante_id, metodo in zip(variantes, medios):
            pedido = VentaPresencialService(db, ctx).crear(VentaIn(items=[LineaIn(variante_id=variante_id, cantidad=1)]))
            recibido = (Decimal(pedido.total) / 10).to_integral_value(rounding="ROUND_CEILING") * 10 if metodo == "EFECTIVO" else None
            CobroCajaService(db, ctx).cobrar(pedido.id, CobroIn(metodo=metodo, monto_recibido=recibido))


def cargar_devoluciones(db: Session, empresa) -> None:
    """Una devolución de ejemplo (Fase F): el Cajero devuelve una prenda de su primera venta en efectivo."""
    if db.scalar(select(Devolucion.id).where(Devolucion.empresa_id == empresa.id).limit(1)):
        return
    cajero = db.scalar(select(Usuario).join(Usuario.rol).where(Usuario.empresa_id == empresa.id, Rol.nombre == CAJERO, Usuario.sucursal_id.is_not(None)).order_by(Usuario.id).limit(1))
    if cajero is None:
        return
    venta = db.scalar(
        select(Pedido).join(Pago, Pago.pedido_id == Pedido.id)
        .where(Pedido.empresa_id == empresa.id, Pedido.canal == "PRESENCIAL", Pedido.estado == "PAGADO", Pedido.sucursal_id == cajero.sucursal_id, Pago.metodo == "EFECTIVO")
        .order_by(Pedido.id).limit(1)
    )
    if venta is None or not venta.items:
        return
    ctx = Contexto(cajero, CAJERO, empresa.id, cajero.sucursal_id)
    DevolucionService(db, ctx).registrar(DevolucionIn(
        comprobante=venta.comprobante_numero, motivo="Le quedó pequeña", items=[ItemDevueltoIn(pedido_item_id=venta.items[0].id, cantidad=1)],
    ))

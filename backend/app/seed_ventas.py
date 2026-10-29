"""Datos de ejemplo de ventas: compra digital del cliente demo (Fase D), ventas de caja (Fase E) y una devolución (Fase F). Idempotente."""
import uuid
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.constantes import CAJERO, CLIENTE, ENCARGADO
from app.modules.acceso.dependencias import Contexto
from app.modules.acceso.models import Rol, Usuario
from app.modules.inventario.models import Existencia
from app.modules.sucursales.models import Sucursal
from app.modules.offline.cu38_sincronizar.service import SincronizacionService
from app.modules.offline.schemas import OperacionIn, SincronizarIn
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
from app.core.tiempo import ahora
from app.primer_parcial.catalogo.publico import Producto, Variante
from app.primer_parcial.ia.models import InteraccionCliente
from app.primer_parcial.ventas.models import Pago, Pedido, PedidoItem


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


def cargar_historial(db: Session, empresa) -> None:
    """Ventas de las últimas 10 semanas (Fase G) para que los reportes, los indicadores y el pronóstico con ML tengan datos. Son datos de demostración."""
    if db.scalar(select(Pedido.id).where(Pedido.empresa_id == empresa.id, Pedido.codigo.like("HIST-%")).limit(1)):
        return
    sucursal = db.scalar(select(Sucursal).where(Sucursal.empresa_id == empresa.id, Sucursal.activa.is_(True)).order_by(Sucursal.id).limit(1))
    if sucursal is None:
        return
    filas = db.execute(
        select(Variante, Producto).join(Producto, Producto.id == Variante.producto_id).join(Existencia, Existencia.variante_id == Variante.id)
        .where(Variante.empresa_id == empresa.id, Existencia.sucursal_id == sucursal.id).order_by(Producto.id, Variante.id)
    ).all()
    variantes: dict[int, tuple] = {}
    for variante, producto in filas:
        variantes.setdefault(producto.id, (variante, producto))  # una variante por producto
    productos = list(variantes.values())[:4]
    if not productos:
        return
    semanas, numero = 10, 0
    for semana in range(semanas, 0, -1):  # de la más antigua a la más reciente
        for canal, subconjunto in (("PRESENCIAL", productos), ("DIGITAL", productos[:2])):
            lineas = []
            for indice, (variante, producto) in enumerate(subconjunto):
                base, tendencia = (2, 0.9) if indice == 0 else (6, 0.0) if indice == 1 else (5, -0.4) if indice == 2 else (1, 0.1)
                unidades = max(1, round(base + tendencia * (semanas - semana)) + (semana * 3 + indice) % 3 - 1)
                lineas.append((variante, producto, unidades, Decimal(variante.precio_especifico or producto.precio_base)))
            total = sum((precio * unidades for _, _, unidades, precio in lineas), Decimal("0.00"))
            momento = ahora() - timedelta(days=semana * 7 - (2 if canal == "PRESENCIAL" else 4), hours=3)
            numero += 1
            pedido = Pedido(
                empresa_id=empresa.id, codigo=f"HIST-{numero:04d}", sucursal_id=sucursal.id, canal=canal, tipo_entrega="EN_TIENDA" if canal == "PRESENCIAL" else "RETIRO",
                estado="PAGADO", subtotal=total, total=total, iva_incluido=(total * 13 / 113).quantize(Decimal("0.01")), pagado_en=momento,
            )
            for variante, producto, unidades, precio in lineas:
                pedido.items.append(PedidoItem(
                    empresa_id=empresa.id, variante_id=variante.id, sku=variante.sku, producto=producto.nombre, talla=variante.talla.codigo, color=variante.color.nombre,
                    cantidad=unidades, precio_unitario=precio, precio_final=precio, subtotal=precio * unidades,
                ))
            db.add(pedido)
            db.flush()
            db.add(Pago(
                empresa_id=empresa.id, pedido_id=pedido.id, metodo="EFECTIVO" if canal == "PRESENCIAL" else "TARJETA", proveedor="CAJA" if canal == "PRESENCIAL" else "SIMULADO",
                estado="APROBADO", monto=total, creado_en=momento, referencia_externa=None if canal == "PRESENCIAL" else f"sim_hist_{empresa.id}_{numero}",
                tarjeta_marca="" if canal == "PRESENCIAL" else "Visa", tarjeta_ultimos4="" if canal == "PRESENCIAL" else "4242", mensaje="Pago aprobado.",
            ))


def cargar_perfil_cliente(db: Session, empresa) -> None:
    """Fase G: el cliente demo ya buscó y miró prendas, para que el recomendador muestre recomendaciones personalizadas desde el primer día."""
    cliente = db.scalar(select(Usuario).where(Usuario.empresa_id == empresa.id, Usuario.email == f"cliente@{empresa.codigo.lower()}.com"))
    if cliente is None or db.scalar(select(InteraccionCliente.id).where(InteraccionCliente.empresa_id == empresa.id).limit(1)):
        return
    filas = db.execute(
        select(Variante, Producto).join(Producto, Producto.id == Variante.producto_id).where(Variante.empresa_id == empresa.id).order_by(Producto.id, Variante.id)
    ).all()
    por_producto: dict[int, tuple] = {}
    for variante, producto in filas:
        por_producto.setdefault(producto.id, (variante, producto))
    elegidos = list(por_producto.values())[:2]
    if not elegidos:
        return
    variante, producto = elegidos[0]
    db.add(InteraccionCliente(empresa_id=empresa.id, cliente_id=cliente.id, tipo="BUSQUEDA", texto=producto.nombre.lower()[:120], categoria_id=producto.categoria_id, color_id=variante.color_id))
    for _, otro in elegidos:
        db.add(InteraccionCliente(empresa_id=empresa.id, cliente_id=cliente.id, tipo="VISTA", producto_id=otro.id, categoria_id=otro.categoria_id))


def cargar_conflicto_offline(db: Session, empresa) -> None:
    """Fase H: una venta de contado hecha sin conexión por el Cajero que no alcanzó en el inventario, para que el Encargado la resuelva en «Conflictos de sincronización»."""
    cajero = db.scalar(select(Usuario).join(Usuario.rol).where(Usuario.empresa_id == empresa.id, Rol.nombre == CAJERO, Usuario.sucursal_id.is_not(None)).order_by(Usuario.id).limit(1))
    if cajero is None:
        return
    existencia = db.scalar(select(Existencia).where(Existencia.empresa_id == empresa.id, Existencia.sucursal_id == cajero.sucursal_id, Existencia.disponible > 0).order_by(Existencia.disponible, Existencia.variante_id).limit(1))
    if existencia is None or existencia.disponible >= 50:  # el máximo por línea es 50: con tanto stock no habría conflicto
        return
    ctx = Contexto(cajero, CAJERO, empresa.id, cajero.sucursal_id)
    SincronizacionService(db, ctx).sincronizar(SincronizarIn(operaciones=[OperacionIn(
        id=uuid.uuid5(uuid.NAMESPACE_URL, f"fashionstore-demo-conflicto-{empresa.codigo}"), tipo="VENTA_CONTADO", creada_en=ahora(),
        payload={"items": [{"variante_id": existencia.variante_id, "cantidad": existencia.disponible + 1}], "monto_recibido": "99999.00"},
    )]))

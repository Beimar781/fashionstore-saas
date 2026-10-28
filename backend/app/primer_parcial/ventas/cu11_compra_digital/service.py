"""CU-11 · Realizar compra digital, checkout (RN01, RN02). Capa de negocio.

El checkout congela el carrito en un pedido PENDIENTE_PAGO (precios y nombres no cambian después). El pago lo procesa CU-32; cuando
la pasarela aprueba, CU-32 llama a `finalizar`: descuenta el stock de la sucursal elegida, numera el comprobante y vacía el carrito.
"""
import secrets
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.errors import Conflicto, DatosInvalidos
from app.core.tiempo import ahora
from app.modules.acceso.dependencias import Contexto
from app.modules.inventario.publico import aplicar_movimientos, disponible_por_variante
from app.modules.reservas.publico import notificar
from app.modules.sucursales.publico import nombres_de_sucursales
from app.primer_parcial.reservas.publico import CarritoService
from app.primer_parcial.ventas.cu11_compra_digital import schemas
from app.primer_parcial.ventas.cu11_compra_digital.repository import PedidoRepository
from app.primer_parcial.ventas.models import Pedido

ALFABETO = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
MSG_CARRITO_VACIO = "Su carrito está vacío."
MSG_RECHAZO = "La transacción no pudo ser procesada, verifique su método de pago o saldo disponible."  # excepción de la ficha CU-11


class SinStock(Conflicto):
    """El stock cambió entre el carrito y el pago: no se cobra."""


class CompraService:
    def __init__(self, db: Session, ctx: Contexto):
        self.db = db
        self.ctx = ctx
        self.empresa_id = ctx.empresa_id
        self.pedidos = PedidoRepository(db, ctx.empresa_id)
        self.carrito = CarritoService(db, ctx.empresa_id)

    # ---- pasos 1 a 3: del carrito al pedido ----
    def checkout(self, datos: schemas.CheckoutIn) -> schemas.PedidoOut:
        carrito = self.carrito.obtener(self.ctx.usuario.id)
        if not carrito.items:
            raise DatosInvalidos(MSG_CARRITO_VACIO)
        if not carrito.puede_pagar:  # el stock se vuelve a verificar aquí, y otra vez al cobrar
            raise Conflicto("Hay prendas sin stock suficiente o retiradas del catálogo. Ajuste su carrito antes de pagar. " + " ".join(carrito.avisos))

        for anterior in self.pedidos.pendientes_de_pago(self.ctx.usuario.id):  # un solo pedido por pagar a la vez
            self.cancelar(anterior, "Reemplazado por un nuevo pedido.")
        pedido = self.pedidos.agregar(Pedido(
            codigo=self._codigo_libre(), cliente_id=self.ctx.usuario.id, sucursal_id=carrito.sucursal_id, canal="DIGITAL",
            tipo_entrega=datos.tipo_entrega, direccion_entrega=datos.direccion_entrega.strip() if datos.tipo_entrega == "DELIVERY" else "",
            nit_ci=datos.nit_ci.strip(), razon_social=datos.razon_social.strip(), subtotal=carrito.subtotal, descuento=carrito.descuento,
            iva_incluido=carrito.iva_incluido, total=carrito.total, creado_por=self.ctx.usuario.id,
        ))
        for item in carrito.items:
            self.pedidos.agregar_item(
                pedido, variante_id=item.variante_id, sku=item.sku, producto=item.producto, talla=item.talla, color=item.color,
                cantidad=item.cantidad, precio_unitario=item.precio, precio_final=item.precio_final, subtotal=item.subtotal,
            )
        self.db.commit()
        return self.salida([pedido])[0]

    # ---- paso 5: tras el pago aprobado (lo llama CU-32, que confirma la transacción) ----
    def finalizar(self, pedido: Pedido) -> None:
        """Descuenta el stock de la sucursal, numera el comprobante, marca el pedido como pagado y vacía el carrito.
        Si ya no hay stock lanza SinStock sin haber cambiado nada: quien llama debe anular el cobro."""
        faltantes = self._faltantes(pedido)
        if faltantes:
            raise SinStock(self._mensaje_sin_stock(faltantes))
        lineas = [(i.variante_id, i.cantidad) for i in pedido.items]
        try:
            aplicar_movimientos(self.db, self.empresa_id, pedido.sucursal_id, lineas, "VENTA", "PEDIDO", pedido.id, pedido.cliente_id, f"Venta {pedido.codigo}")
        except Conflicto as e:  # otro cliente compró lo mismo justo ahora
            raise SinStock(self._mensaje_sin_stock([])) from e
        pedido.comprobante_numero = self.pedidos.siguiente_comprobante(pedido.sucursal_id)
        pedido.estado, pedido.pagado_en = "PAGADO", ahora()
        if pedido.cliente_id is not None:
            self.carrito.vaciar(pedido.cliente_id, confirmar=False)
        entrega = "retiro en la sucursal" if pedido.tipo_entrega == "RETIRO" else "entrega a domicilio"
        notificar(  # RF11: la sucursal se entera de que debe preparar el pedido
            self.db, self.empresa_id, "PEDIDO_NUEVO", f"Nuevo pedido {pedido.codigo}",
            f"Compra digital pagada: {sum(i.cantidad for i in pedido.items)} prenda(s), {entrega}. Prepare el pedido.",
            sucursal_id=pedido.sucursal_id, referencia_tipo="PEDIDO", referencia_id=pedido.id,
        )

    def cancelar(self, pedido: Pedido, motivo: str) -> None:
        pedido.estado, pedido.motivo_cancelacion = "CANCELADO", motivo
        for pago in self.pedidos.pagos_de([pedido.id])[pedido.id]:
            if pago.estado in ("PENDIENTE", "AUTORIZADO", "PENDIENTE_CONFIRMACION"):
                pago.estado = "CANCELADO"

    def faltantes_ahora(self, pedido: Pedido) -> str | None:
        """Mensaje con las prendas que ya no alcanzan, o None si todo sigue disponible (CU-32 lo usa antes de pedir el pago)."""
        faltantes = self._faltantes(pedido)
        return self._mensaje_sin_stock(faltantes, aviso_previo=True) if faltantes else None

    # ---- salida ----
    def salida(self, pedidos: list[Pedido]) -> list[schemas.PedidoOut]:
        sucursales = nombres_de_sucursales(self.db, self.empresa_id)
        pagos = self.pedidos.pagos_de([p.id for p in pedidos])
        return [
            schemas.PedidoOut(
                id=p.id, codigo=p.codigo, estado=p.estado, canal=p.canal, tipo_entrega=p.tipo_entrega, direccion_entrega=p.direccion_entrega,
                nit_ci=p.nit_ci, razon_social=p.razon_social, sucursal_id=p.sucursal_id, sucursal=sucursales.get(p.sucursal_id, ""),
                subtotal=p.subtotal, descuento=p.descuento, iva_incluido=p.iva_incluido, total=p.total, moneda=p.moneda,
                total_unidades=sum(i.cantidad for i in p.items), comprobante_numero=p.comprobante_numero, creado_en=p.creado_en,
                pagado_en=p.pagado_en, items=[schemas.ItemPedidoOut.model_validate(i, from_attributes=True) for i in p.items],
                pagos=[schemas.PagoResumenOut.model_validate(g, from_attributes=True) for g in pagos[p.id]],
            )
            for p in pedidos
        ]

    # ---- auxiliares ----
    def _faltantes(self, pedido: Pedido) -> list[tuple[str, int, int]]:
        disponibles = disponible_por_variante(self.db, self.empresa_id, [i.variante_id for i in pedido.items], pedido.sucursal_id)
        return [
            (f"{i.producto} ({i.talla}, {i.color})", disponibles.get(i.variante_id, 0), i.cantidad)
            for i in pedido.items if disponibles.get(i.variante_id, 0) < i.cantidad
        ]

    @staticmethod
    def _mensaje_sin_stock(faltantes: list[tuple[str, int, int]], aviso_previo: bool = False) -> str:
        detalle = "; ".join(f"{nombre}: quedan {hay}, necesita {pide}" for nombre, hay, pide in faltantes)
        causa = f"Algunas prendas se agotaron{'' if aviso_previo else ' mientras pagaba'}" + (f": {detalle}" if detalle else "")
        return f"{causa}. No se realizó ningún cobro. Ajuste su carrito e intente de nuevo."

    def _codigo_libre(self) -> str:
        while True:
            codigo = "PED-" + "".join(secrets.choice(ALFABETO) for _ in range(8))
            if not self.pedidos.existe_codigo(codigo):
                return codigo

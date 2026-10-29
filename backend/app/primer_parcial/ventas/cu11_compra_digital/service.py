"""CU-11 · Realizar compra digital, checkout (RN01, RN02). Capa de negocio.

El checkout congela el carrito en un pedido PENDIENTE_PAGO (precios y nombres no cambian después). El pago lo procesa CU-32; cuando
la pasarela aprueba, CU-32 llama a `finalizar`: descuenta el stock de la sucursal elegida, numera el comprobante y vacía el carrito.
Los pedidos de caja (CU-29) usan el mismo pedido y el mismo `finalizar` (regla 15: no se duplica).
"""
import secrets
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.errors import Conflicto, DatosInvalidos, NoEncontrado
from app.core.impuestos import MSG_FALLA_IMPUESTOS, emitir_comprobante, obtener_servicio_impuestos
from app.core.tiempo import ahora
from app.core.tipos import iva_incluido
from app.modules.acceso.dependencias import Contexto
from app.modules.acceso.publico import nombres_de_usuarios
from app.modules.inventario.publico import aplicar_movimientos, disponible_por_variante
from app.modules.plataforma.publico import datos_de_empresa
from app.modules.reservas.publico import ReservaService, notificar
from app.modules.sucursales.publico import nombres_de_sucursales
from app.primer_parcial.reservas.publico import CarritoService
from app.primer_parcial.ventas.cu11_compra_digital import schemas
from app.primer_parcial.ventas.cu11_compra_digital.repository import PedidoRepository
from app.primer_parcial.ventas.models import Pedido

ALFABETO = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
MSG_CARRITO_VACIO = "Su carrito está vacío."
MSG_RECHAZO = "La transacción no pudo ser procesada, verifique su método de pago o saldo disponible."  # excepción de la ficha CU-11


class SinStock(Conflicto):
    """El stock cambió entre el carrito (o la caja) y el pago: no se cobra."""


@dataclass
class Linea:
    """Una prenda del pedido con su precio ya calculado (con la promoción vigente)."""

    variante_id: int
    sku: str
    producto: str
    talla: str
    color: str
    cantidad: int
    precio: Decimal
    precio_final: Decimal


class CompraService:
    def __init__(self, db: Session, ctx: Contexto, impuestos=None):
        self.db = db
        self.ctx = ctx
        self.empresa_id = ctx.empresa_id
        self.pedidos = PedidoRepository(db, ctx.empresa_id)
        self.carrito = CarritoService(db, ctx.empresa_id)
        self.impuestos = impuestos or obtener_servicio_impuestos()

    # ---- pasos 1 a 3: del carrito al pedido ----
    def checkout(self, datos: schemas.CheckoutIn) -> schemas.PedidoOut:
        carrito = self.carrito.obtener(self.ctx.usuario.id)
        if not carrito.items:
            raise DatosInvalidos(MSG_CARRITO_VACIO)
        if not carrito.puede_pagar:  # el stock se vuelve a verificar aquí, y otra vez al cobrar
            raise Conflicto("Hay prendas sin stock suficiente o retiradas del catálogo. Ajuste su carrito antes de pagar. " + " ".join(carrito.avisos))

        for anterior in self.pedidos.pendientes_de_pago(self.ctx.usuario.id):  # un solo pedido por pagar a la vez
            self.cancelar(anterior, "Reemplazado por un nuevo pedido.")
        lineas = [Linea(i.variante_id, i.sku, i.producto, i.talla, i.color, i.cantidad, i.precio, i.precio_final) for i in carrito.items]
        pedido = self.crear_pedido(
            sucursal_id=carrito.sucursal_id, canal="DIGITAL", tipo_entrega=datos.tipo_entrega, lineas=lineas, cliente_id=self.ctx.usuario.id,
            nit_ci=datos.nit_ci, razon_social=datos.razon_social, direccion=datos.direccion_entrega if datos.tipo_entrega == "DELIVERY" else "",
        )
        self.db.commit()
        return self.salida([pedido])[0]

    def crear_pedido(
        self, *, sucursal_id: int, canal: str, tipo_entrega: str, lineas: list[Linea], cliente_id: int | None, nit_ci: str, razon_social: str,
        direccion: str = "", reserva_id: int | None = None,
    ) -> Pedido:
        """Congela las líneas en un pedido por pagar. Lo usan el checkout (CU-11) y la venta de caja (CU-29). No hace commit."""
        subtotal = sum((l.precio * l.cantidad for l in lineas), Decimal(0))
        total = sum((l.precio_final * l.cantidad for l in lineas), Decimal(0))
        pedido = self.pedidos.agregar(Pedido(
            codigo=self._codigo_libre(), cliente_id=cliente_id, sucursal_id=sucursal_id, canal=canal, tipo_entrega=tipo_entrega,
            direccion_entrega=direccion.strip(), nit_ci=nit_ci.strip(), razon_social=razon_social.strip(), subtotal=subtotal,
            descuento=subtotal - total, iva_incluido=iva_incluido(total), total=total, creado_por=self.ctx.usuario.id, reserva_id=reserva_id,
        ))
        for l in lineas:
            self.pedidos.agregar_item(
                pedido, variante_id=l.variante_id, sku=l.sku, producto=l.producto, talla=l.talla, color=l.color, cantidad=l.cantidad,
                precio_unitario=l.precio, precio_final=l.precio_final, subtotal=l.precio_final * l.cantidad,
            )
        return pedido

    # ---- paso 5: tras el pago aprobado (lo llama CU-32 o CU-30, que confirman la transacción) ----
    def finalizar(self, pedido: Pedido) -> None:
        """Descuenta el stock de la sucursal, numera el comprobante, marca el pedido como pagado y lo deja listo para entregar.
        Si ya no hay stock lanza SinStock sin haber cambiado nada: quien llama debe anular el cobro."""
        if pedido.reserva_id is not None:
            self._descontar_de_la_reserva(pedido)
        else:
            self._descontar_del_stock(pedido)
        pedido.comprobante_numero = self.pedidos.siguiente_comprobante(pedido.sucursal_id)
        emision = emitir_comprobante(self.impuestos, datos_de_empresa(self.db, self.empresa_id)["nit"], pedido.comprobante_numero, pedido.total)
        pedido.comprobante_tipo, pedido.autorizacion_fiscal = emision.tipo, emision.autorizacion
        pedido.estado, pedido.pagado_en = "PAGADO", ahora()
        if pedido.canal == "DIGITAL":
            if pedido.cliente_id is not None:
                self.carrito.vaciar(pedido.cliente_id, confirmar=False)
            entrega = "retiro en la sucursal" if pedido.tipo_entrega == "RETIRO" else "entrega a domicilio"
            notificar(  # RF11: la sucursal se entera de que debe preparar el pedido
                self.db, self.empresa_id, "PEDIDO_NUEVO", f"Nuevo pedido {pedido.codigo}",
                f"Compra digital pagada: {sum(i.cantidad for i in pedido.items)} prenda(s), {entrega}. Prepare el pedido.",
                sucursal_id=pedido.sucursal_id, referencia_tipo="PEDIDO", referencia_id=pedido.id,
            )

    def _descontar_del_stock(self, pedido: Pedido) -> None:
        faltantes = self._faltantes(pedido)
        if faltantes:
            raise SinStock(self._mensaje_sin_stock(faltantes, canal=pedido.canal))
        lineas = [(i.variante_id, i.cantidad) for i in pedido.items]
        referencia = "VENTA" if pedido.canal == "PRESENCIAL" else "PEDIDO"
        try:
            aplicar_movimientos(self.db, self.empresa_id, pedido.sucursal_id, lineas, "VENTA", referencia, pedido.id, self.ctx.usuario.id, f"Venta {pedido.codigo}")
        except Conflicto as e:  # otro cliente compró lo mismo justo ahora
            raise SinStock(self._mensaje_sin_stock([], canal=pedido.canal)) from e

    def _descontar_de_la_reserva(self, pedido: Pedido) -> None:
        motor = ReservaService(self.db, self.empresa_id)
        reserva = motor.completa(pedido.reserva_id)
        if reserva is None or reserva.estado not in ("PREPARADA", "EN_PROBADOR") or reserva.vence_en <= ahora():
            raise SinStock("La reserva ya no está vigente. No se realizó ningún cobro.")
        try:
            motor.completar_con_venta(reserva, {i.variante_id: i.cantidad for i in pedido.items}, pedido.id, self.ctx.usuario.id)
        except Conflicto as e:
            raise SinStock(f"{e.message} No se realizó ningún cobro.") from e

    # ---- ventas de caja (las usan CU-29 y CU-30) ----
    def ventas_abiertas(self, sucursal_id: int) -> list[Pedido]:
        return self.pedidos.abiertos_presenciales(sucursal_id)

    def venta_abierta_de_reserva(self, reserva_id: int) -> Pedido | None:
        return self.pedidos.abierto_de_reserva(reserva_id)

    def venta_de_caja(self, pedido_id: int, sucursal_id: int) -> Pedido:
        """Una venta presencial de la sucursal del cajero; la de otra sucursal u otra empresa no existe para él."""
        pedido = self.pedidos.obtener_completo(pedido_id)
        if pedido is None or pedido.canal != "PRESENCIAL" or pedido.sucursal_id != sucursal_id:
            raise NoEncontrado("Venta no encontrada.")
        return pedido

    def cancelar(self, pedido: Pedido, motivo: str) -> None:
        pedido.estado, pedido.motivo_cancelacion = "CANCELADO", motivo
        for pago in self.pedidos.pagos_de([pedido.id])[pedido.id]:
            if pago.estado in ("PENDIENTE", "AUTORIZADO", "PENDIENTE_CONFIRMACION"):
                pago.estado = "CANCELADO"

    def faltantes_ahora(self, pedido: Pedido) -> str | None:
        """Mensaje con las prendas que ya no alcanzan, o None si todo sigue disponible (CU-32 lo usa antes de pedir el pago)."""
        if pedido.reserva_id is not None:
            return None  # el stock de una reserva ya está apartado: se valida al cobrar
        faltantes = self._faltantes(pedido)
        return self._mensaje_sin_stock(faltantes, aviso_previo=True, canal=pedido.canal) if faltantes else None

    # ---- salida ----
    def salida(self, pedidos: list[Pedido]) -> list[schemas.PedidoOut]:
        sucursales = nombres_de_sucursales(self.db, self.empresa_id)
        pagos = self.pedidos.pagos_de([p.id for p in pedidos])
        personas = nombres_de_usuarios(self.db, self.empresa_id, {u for p in pedidos for u in (p.cliente_id, p.creado_por) if u})
        return [
            schemas.PedidoOut(
                id=p.id, codigo=p.codigo, estado=p.estado, canal=p.canal, tipo_entrega=p.tipo_entrega, direccion_entrega=p.direccion_entrega,
                nit_ci=p.nit_ci, razon_social=p.razon_social, sucursal_id=p.sucursal_id, sucursal=sucursales.get(p.sucursal_id, ""),
                subtotal=p.subtotal, descuento=p.descuento, iva_incluido=p.iva_incluido, total=p.total, moneda=p.moneda,
                total_unidades=sum(i.cantidad for i in p.items), comprobante_numero=p.comprobante_numero, comprobante_tipo=p.comprobante_tipo,
                comprobante_aviso=MSG_FALLA_IMPUESTOS if p.comprobante_tipo == "INTERNO_TEMPORAL" else None,
                cliente=personas.get(p.cliente_id), vendedor=personas.get(p.creado_por) if p.canal == "PRESENCIAL" else None,
                reserva_id=p.reserva_id, creado_en=p.creado_en, pagado_en=p.pagado_en,
                items=[schemas.ItemPedidoOut.model_validate(i, from_attributes=True) for i in p.items],
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
    def _mensaje_sin_stock(faltantes: list[tuple[str, int, int]], aviso_previo: bool = False, canal: str = "DIGITAL") -> str:
        detalle = "; ".join(f"{nombre}: quedan {hay}, necesita {pide}" for nombre, hay, pide in faltantes)
        causa = f"Algunas prendas se agotaron{'' if aviso_previo else ' mientras pagaba'}" + (f": {detalle}" if detalle else "")
        cierre = "Ajuste su carrito e intente de nuevo." if canal == "DIGITAL" else "Anule la venta y regístrela de nuevo con lo disponible."
        return f"{causa}. No se realizó ningún cobro. {cierre}"

    def _codigo_libre(self) -> str:
        while True:
            codigo = "PED-" + "".join(secrets.choice(ALFABETO) for _ in range(8))
            if not self.pedidos.existe_codigo(codigo):
                return codigo

"""Ejecuta una operación offline con los mismos casos de uso del trabajo en línea (regla 15): la venta de contado es la venta de caja (CU-29 y CU-30) y la reserva es CU-09.

Todo va en UNA transacción: el que llama hace el único commit junto con el registro de la operación (RNF04, RNF05).
Una falta de stock no deja nada a medias: se deshace todo y la operación queda en conflicto (RN14).
"""
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.errors import Conflicto, DatosInvalidos
from app.modules.acceso.dependencias import Contexto
from app.modules.inventario.publico import disponible_por_variante
from app.modules.offline.repository import OperacionRepository
from app.modules.offline.schemas import CompraOfflineIn, VentaOfflineIn
from app.modules.reservas.publico import ReservaClienteService, ReservaIn, ReservaService
from app.modules.sucursales.publico import nombres_de_sucursales
from app.modules.ventas.publico import LineaIn, VarianteVentaRepository, VentaIn, VentaPresencialService
from app.primer_parcial.catalogo.publico import descuentos_vigentes
from app.primer_parcial.ventas.publico import CobroCajaService, CobroIn, CompraService, Linea, SinStock


class Resultado:
    def __init__(self, referencia: str | None, comprobante: str | None, pedido_id: int | None = None, reserva_id: int | None = None):
        self.referencia, self.comprobante, self.pedido_id, self.reserva_id = referencia, comprobante, pedido_id, reserva_id


MSG_PRECIO = "El precio de una prenda cambió desde que se registró la venta."


class PrecioCambio(Conflicto):
    """Regla de precio (§7.2): se respeta el precio local solo si sigue siendo el vigente; si cambió, la venta queda EN_CONFLICTO para que el Encargado decida."""

    def __init__(self, cambios: list[dict]):
        super().__init__(MSG_PRECIO)
        self.cambios = cambios


def es_falta_de_stock(e: Exception) -> bool:
    return isinstance(e, SinStock) or (isinstance(e, Conflicto) and "stock suficiente" in e.message)


class Ejecutor:
    def __init__(self, db: Session, ctx: Contexto):
        self.db, self.ctx = db, ctx

    def ejecutar(self, tipo: str, payload: dict, validar_precio: bool = True) -> Resultado:
        if tipo == "COMPRA":
            return self._compra(CompraOfflineIn.model_validate(payload))
        if tipo == "VENTA_CONTADO":
            datos = VentaOfflineIn.model_validate(payload)
            if validar_precio:
                self._validar_precios(datos)
            venta = VentaPresencialService(self.db, self.ctx).crear(
                VentaIn(items=[LineaIn(variante_id=i.variante_id, cantidad=i.cantidad) for i in datos.items], cliente_email=datos.cliente_email, nit_ci=datos.nit_ci, razon_social=datos.razon_social),
                commit=False,
            )
            cobro = CobroCajaService(self.db, self.ctx).cobrar(venta.id, CobroIn(metodo="EFECTIVO", monto_recibido=datos.monto_recibido), commit=False)  # RN13: de contado
            return Resultado(cobro.pedido.codigo, cobro.pedido.comprobante_numero, pedido_id=venta.id)
        if tipo == "CANCELAR_RESERVA":
            reserva_id = payload.get("reserva_id")
            if not isinstance(reserva_id, int) or reserva_id <= 0:
                raise DatosInvalidos("La operación no tiene una reserva válida para cancelar.")
            reserva = ReservaClienteService(self.db, self.ctx).cancelar(reserva_id, str(payload.get("motivo", "")), commit=False)
            return Resultado(reserva.codigo, None, reserva_id=reserva.id)
        reserva = ReservaService(self.db, self.ctx.empresa_id).crear(self.ctx, ReservaIn.model_validate(payload), commit=False)
        return Resultado(reserva.codigo, None, reserva_id=reserva.id)

    def _validar_precios(self, datos: VentaOfflineIn) -> None:
        """Compara el precio usado sin conexión con el vigente en el servidor (con promociones). Si alguno cambió, nada se registra."""
        usados = {i.variante_id: i.precio_unitario for i in datos.items if i.precio_unitario is not None}
        if not usados:
            return
        variantes = VarianteVentaRepository(self.db, self.ctx.empresa_id).vendibles(set(usados))
        descuentos = descuentos_vigentes(self.db, self.ctx.empresa_id)
        cambios = []
        for vid, precio in usados.items():
            v = variantes.get(vid)
            if v is None:
                continue
            vigente = descuentos.precio_final(v.producto, v.precio)[0]
            if Decimal(vigente).quantize(Decimal("0.01")) != precio.quantize(Decimal("0.01")):
                cambios.append({"variante_id": vid, "producto": v.producto.nombre, "precio_registrado": f"{precio:.2f}", "precio_actual": f"{Decimal(vigente):.2f}"})
        if cambios:
            raise PrecioCambio(cambios)

    def _compra(self, datos: CompraOfflineIn) -> Resultado:
        """La compra del cliente es el pedido por pagar del checkout (CU-11), sin cobrar nada: si ya no alcanzan las existencias, no se crea y queda en conflicto (RN14)."""
        pedidas: dict[int, int] = {}
        for i in datos.items:
            pedidas[i.variante_id] = pedidas.get(i.variante_id, 0) + i.cantidad
        variantes = VarianteVentaRepository(self.db, self.ctx.empresa_id).vendibles(set(pedidas))
        if len(variantes) != len(pedidas):
            raise DatosInvalidos("Una o más prendas ya no están disponibles en el catálogo.")
        disponibles = disponible_por_variante(self.db, self.ctx.empresa_id, pedidas, datos.sucursal_id)
        faltan = [
            f"{variantes[v].producto.nombre} ({variantes[v].talla.codigo}, {variantes[v].color.nombre}): solicitadas {c}, disponibles {disponibles.get(v, 0)}"
            for v, c in pedidas.items() if disponibles.get(v, 0) < c
        ]
        if faltan:
            sucursal = nombres_de_sucursales(self.db, self.ctx.empresa_id).get(datos.sucursal_id, "")
            raise SinStock(f"No hay stock suficiente en {sucursal} para: " + "; ".join(faltan) + ".")
        descuentos = descuentos_vigentes(self.db, self.ctx.empresa_id)
        lineas = [Linea(v.id, v.sku, v.producto.nombre, v.talla.codigo, v.color.nombre, pedidas[v.id], v.precio, descuentos.precio_final(v.producto, v.precio)[0]) for v in variantes.values()]
        pedido = CompraService(self.db, self.ctx).crear_pedido(
            sucursal_id=datos.sucursal_id, canal="DIGITAL", tipo_entrega=datos.tipo_entrega, lineas=lineas, cliente_id=self.ctx.usuario.id,
            nit_ci=datos.nit_ci.strip(), razon_social=datos.razon_social.strip() or "Sin nombre",
            direccion=datos.direccion_entrega if datos.tipo_entrega == "DELIVERY" else "",
        )
        self.db.flush()
        return Resultado(pedido.codigo, None, pedido_id=pedido.id)

    def faltantes(self, payload: dict, sucursal_id: int) -> list[dict]:
        """RN14: qué prendas no alcanzan en la sucursal ahora mismo (para que el Encargado resuelva el conflicto)."""
        pedidas: dict[int, int] = {}
        for item in payload.get("items", []):
            pedidas[int(item["variante_id"])] = pedidas.get(int(item["variante_id"]), 0) + int(item["cantidad"])
        disponibles = disponible_por_variante(self.db, self.ctx.empresa_id, pedidas, sucursal_id)
        variantes = OperacionRepository(self.db, self.ctx.empresa_id).variantes(set(pedidas))
        return [
            {"variante_id": v, "producto": variantes[v].producto.nombre, "talla": variantes[v].talla.codigo, "color": variantes[v].color.nombre, "solicitadas": c, "disponibles": disponibles.get(v, 0)}
            for v, c in pedidas.items() if v in variantes and disponibles.get(v, 0) < c
        ]

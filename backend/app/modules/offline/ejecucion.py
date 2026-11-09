"""Ejecuta una operación offline con los mismos casos de uso del trabajo en línea (regla 15): la venta de contado es la venta de caja (CU-29 y CU-30) y la reserva es CU-09.

Todo va en UNA transacción: el que llama hace el único commit junto con el registro de la operación (RNF04, RNF05).
Una falta de stock no deja nada a medias: se deshace todo y la operación queda en conflicto (RN14).
"""
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.errors import Conflicto, DatosInvalidos
from app.modules.acceso.dependencias import Contexto
from app.modules.inventario.publico import aplicar_movimientos, disponible_por_variante
from app.modules.offline.repository import OperacionRepository
from app.modules.offline.schemas import AjusteOfflineIn, AtencionReservaOfflineIn, CompraOfflineIn, DevolucionOfflineIn, RecepcionOfflineIn, VentaOfflineIn
from app.modules.reservas.publico import ReservaClienteService, ReservaIn, ReservaService
from app.primer_parcial.reservas.publico import AtencionService, CompletarIn, ReservasSucursalService
from app.modules.sucursales.publico import nombres_de_sucursales
from app.modules.ventas.publico import CondicionIn, Devolucion, DevolucionIn, DevolucionService, ItemDevueltoIn, LineaIn, VarianteVentaRepository, VentaIn, VentaPresencialService
from app.primer_parcial.catalogo.publico import descuentos_vigentes
from app.primer_parcial.ventas.publico import CobroCajaService, CobroIn, CompraService, Linea, Pedido, SinStock


class Resultado:
    def __init__(self, referencia: str | None, comprobante: str | None, pedido_id: int | None = None, reserva_id: int | None = None):
        self.referencia, self.comprobante, self.pedido_id, self.reserva_id = referencia, comprobante, pedido_id, reserva_id
        self.despues = None  # lo que debe hacerse DESPUÉS de confirmar la operación (por ejemplo, el aviso push al cliente, regla 17)


MSG_PRECIO = "El precio de una prenda cambió desde que se registró la venta."


class PrecioCambio(Conflicto):
    """Regla de precio (§7.2): se respeta el precio local solo si sigue siendo el vigente; si cambió, la venta queda EN_CONFLICTO para que el Encargado decida."""

    def __init__(self, cambios: list[dict]):
        super().__init__(MSG_PRECIO)
        self.cambios = cambios


def es_falta_de_stock(e: Exception) -> bool:
    return isinstance(e, SinStock) or (isinstance(e, Conflicto) and ("stock suficiente" in e.message or e.message.startswith("Stock insuficiente")))


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
        if tipo in ("PREPARAR_RESERVA", "PRENDA_NO_ENCONTRADA", "ATENDER_RESERVA"):
            return self._atencion(tipo, AtencionReservaOfflineIn.model_validate(payload))
        if tipo == "AJUSTE_INVENTARIO":
            return self._ajuste(AjusteOfflineIn.model_validate(payload), payload.get("sucursal_id"))
        if tipo == "RECEPCION":
            return self._recepcion(RecepcionOfflineIn.model_validate(payload), payload.get("sucursal_id"))
        if tipo == "DEVOLUCION":
            return self._devolucion(DevolucionOfflineIn.model_validate(payload))
        if tipo == "CANCELAR_RESERVA":
            reserva_id = payload.get("reserva_id")
            if not isinstance(reserva_id, int) or reserva_id <= 0:
                raise DatosInvalidos("La operación no tiene una reserva válida para cancelar.")
            reserva = ReservaClienteService(self.db, self.ctx).cancelar(reserva_id, str(payload.get("motivo", "")), commit=False)
            return Resultado(reserva.codigo, None, reserva_id=reserva.id)
        reserva = ReservaService(self.db, self.ctx.empresa_id).crear(self.ctx, ReservaIn.model_validate(payload), commit=False)
        return Resultado(reserva.codigo, None, reserva_id=reserva.id)

    def _atencion(self, tipo: str, datos: AtencionReservaOfflineIn) -> Resultado:
        """B4: son los mismos casos de uso CU-24 y CU-25 de la web (regla 15). Si la reserva ya fue cancelada o atendida desde otro dispositivo, el servicio lo dice y la operación queda RECHAZADA."""
        if tipo == "PREPARAR_RESERVA":
            reserva = ReservasSucursalService(self.db, self.ctx).preparar(datos.reserva_id, commit=False)
        elif tipo == "PRENDA_NO_ENCONTRADA":
            if datos.item_id is None:
                raise DatosInvalidos("Indique la prenda de la reserva que no se encontró.")
            reserva = ReservasSucursalService(self.db, self.ctx).marcar_no_encontrado(datos.reserva_id, datos.item_id, commit=False)
        else:
            servicio = AtencionService(self.db, self.ctx)
            servicio.atender(datos.reserva_id, commit=False)
            reserva = servicio.completar(datos.reserva_id, CompletarIn(llevara_prendas=datos.llevara_prendas), commit=False).reserva
        return Resultado(reserva.codigo, None, reserva_id=reserva.id)

    def _ajuste(self, datos: AjusteOfflineIn, sucursal_id: int) -> Resultado:
        """B6: aplica la diferencia con el mismo servicio de inventario de la web. Si dejaría el stock negativo, la operación queda EN_CONFLICTO."""
        tipo = "AJUSTE_ENTRADA" if datos.diferencia > 0 else "AJUSTE_SALIDA"
        nota = f"{datos.motivo}: {datos.nota.strip()}".strip(": ") if datos.nota.strip() else f"Ajuste por {datos.motivo.lower()}"
        aplicar_movimientos(self.db, self.ctx.empresa_id, sucursal_id, [(datos.variante_id, abs(datos.diferencia))], tipo, "MANUAL", usuario_id=self.ctx.usuario.id, nota=nota)
        return Resultado(f"AJU-{datos.variante_id}", None)

    def _recepcion(self, datos: RecepcionOfflineIn, sucursal_id: int) -> Resultado:
        """B5: la mercadería recibida suma al inventario como cualquier recepción (ENTRADA_RECEPCION)."""
        aplicar_movimientos(self.db, self.ctx.empresa_id, sucursal_id, [(datos.variante_id, datos.cantidad)], "ENTRADA_RECEPCION", "RECEPCION", usuario_id=self.ctx.usuario.id, nota=f"Recepción sin conexión: {datos.referencia.strip()}")
        return Resultado(datos.referencia.strip()[:40], None)

    def _devolucion(self, datos: DevolucionOfflineIn) -> Resultado:
        """B3: es la devolución del CU-41 (regla 15): valida plazo, existencias y que no esté ya devuelta. El aviso al cliente sale después de confirmar."""
        servicio = DevolucionService(self.db, self.ctx)
        salida = servicio.registrar(
            DevolucionIn(
                comprobante=datos.comprobante, motivo=datos.motivo, items=[ItemDevueltoIn(**i) for i in datos.items], condicion=CondicionIn(**datos.condicion) if datos.condicion else CondicionIn(sin_danos=True, sin_desgaste=True, con_etiquetas=True),
            ),
            confirmar=False,
        )
        resultado = Resultado(salida.numero, None)
        devolucion = self.db.get(Devolucion, salida.id)
        resultado.pedido_id = devolucion.pedido_id

        def avisar():
            servicio._avisar_al_cliente(self.db.get(Pedido, devolucion.pedido_id), devolucion)

        resultado.despues = avisar
        return resultado

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

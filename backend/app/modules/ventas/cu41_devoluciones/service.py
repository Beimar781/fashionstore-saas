"""CU-41 · Gestionar devoluciones y cambios de prendas (RN10, RN15). Capa de negocio.

Reglas de RN15: la devolución requiere el comprobante de la venta y se acepta dentro del plazo que fija la empresa; genera una nota de
devolución y reingresa la prenda al inventario de la sucursal; el cambio está sujeto a disponibilidad. Todo se registra en una sola
transacción: si algo falla (por ejemplo, el reembolso en la pasarela), no queda nada a medias.
"""
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.constantes import ADMIN
from app.core.errors import AppError, Conflicto, DatosInvalidos, NoEncontrado
from app.core.tiempo import a_local, ahora
from app.modules.acceso.dependencias import Contexto
from app.modules.acceso.publico import nombres_de_usuarios
from app.modules.inventario.publico import aplicar_movimientos, disponible_por_variante
from app.modules.plataforma.publico import datos_de_empresa
from app.modules.sucursales.publico import datos_de_sucursal, nombres_de_sucursales
from app.modules.ventas.cu29_venta_presencial.repository import VarianteVentaRepository
from app.modules.ventas.cu41_devoluciones import schemas
from app.modules.ventas.cu41_devoluciones.nota import generar_nota
from app.modules.ventas.cu41_devoluciones.repository import ConfiguracionRepository, DevolucionRepository, IntentoRepository
from app.modules.ventas.models import Devolucion, DevolucionItem, IntentoDiferencia
from app.primer_parcial.catalogo.publico import descuentos_vigentes
from app.primer_parcial.ventas.publico import (
    MSG_RECHAZO, CompraService, PagoRechazado, PasarelaNoDisponible, Pedido, Tarjeta, obtener_pasarela, pasarela_para, sucursal_de_caja,
)

CERO = Decimal("0.00")
MSG_SIN_COMPROBANTE = "Para devolver o cambiar una prenda se requiere el comprobante de la venta."  # RN15
MSG_NO_ENCONTRADA = "No se encontró una venta con ese comprobante en su sucursal."
MSG_MOTIVO = "Indique el motivo de la devolución."
MSG_SIN_PRENDAS = "Seleccione al menos una prenda a devolver."
MSG_AJENA = "La prenda indicada no pertenece a esa venta."
MSG_CAMBIO_SIN_NUEVAS = "Un cambio requiere al menos una prenda nueva."
MSG_DEVOLUCION_CON_NUEVAS = "Una devolución no lleva prendas nuevas; registre un cambio."
MSG_NO_DISPONIBLE = "Una o más prendas del cambio ya no están disponibles en el catálogo."
MSG_COBRO_TARJETA = "Inicie el cobro con tarjeta de la diferencia antes de registrar el cambio."
MSG_SIN_DIFERENCIA = "El cambio no tiene una diferencia a cobrar."
MSG_DIFERENCIA_CAMBIO = "El cobro de la diferencia ya no coincide con el cambio. Inicie el cobro con tarjeta nuevamente."
MSG_PASARELA = "No se pudo comunicar con la pasarela de pago. Intente nuevamente: no se registró el cambio ni se cobró nada."
MSG_REEMBOLSO = "No se pudo reembolsar el pago en la pasarela: la devolución no se registró. Intente nuevamente."


class ReembolsoFallido(AppError):
    status_code = 502


class DevolucionService:
    def __init__(self, db: Session, ctx: Contexto):
        self.db = db
        self.ctx = ctx
        self.empresa_id = ctx.empresa_id
        self.devoluciones = DevolucionRepository(db, ctx.empresa_id)
        self.intentos = IntentoRepository(db, ctx.empresa_id)
        self.configuracion = ConfiguracionRepository(db, ctx.empresa_id)
        self.compras = CompraService(db, ctx)
        self.variantes = VarianteVentaRepository(db, ctx.empresa_id)

    # ---- paso 1: la venta que se devuelve, por el número de su comprobante ----
    def venta(self, comprobante: str) -> schemas.VentaDevolvibleOut:
        pedido = self._pedido(comprobante)
        plazo, vence = self._plazo(pedido)
        devueltas = self.devoluciones.devuelto_por_item(pedido.id)
        pago = self.compras.pago_aprobado(pedido)
        return schemas.VentaDevolvibleOut(
            pedido=self.compras.salida([pedido])[0],
            items=[
                schemas.ItemDevolvibleOut(
                    pedido_item_id=i.id, variante_id=i.variante_id, sku=i.sku, producto=i.producto, talla=i.talla, color=i.color, precio_final=i.precio_final,
                    vendida=i.cantidad, devuelta=devueltas.get(i.id, 0), devolvible=i.cantidad - devueltas.get(i.id, 0),
                )
                for i in pedido.items
            ],
            medio_pago=pago.metodo if pago else None, plazo_dias=plazo, vence_el=vence, dentro_del_plazo=ahora() <= vence,
            devoluciones=self._salida(self.devoluciones.de_pedido(pedido.id)),
        )

    # ---- pasos 2 a 5: registrar la devolución o el cambio ----
    def registrar(self, datos: schemas.DevolucionIn) -> schemas.DevolucionOut:
        pedido, devueltas, nuevas, devuelto, entregado, reembolso, adicional = self._preparar(datos)
        recibido, vuelto = self._cobro_adicional(datos, adicional)
        tarjeta = self._autorizar_tarjeta(pedido, datos.cobro, adicional) if adicional and datos.cobro.metodo == "TARJETA" else None
        try:
            devolucion = self._guardar(datos, pedido, devueltas, nuevas, (devuelto, entregado, reembolso, adicional), (recibido, vuelto), tarjeta)
            if tarjeta:
                tarjeta[1].capturar(tarjeta[0].referencia)  # recién con el cambio ya registrado se cobra la diferencia
        except Exception as e:
            self.db.rollback()  # nada a medias: ni inventario ni dinero
            if tarjeta:
                self._anular_cobro(tarjeta[0].id, tarjeta[0].referencia, tarjeta[1])
            if isinstance(e, AppError):
                raise
            raise PasarelaNoDisponible(MSG_PASARELA) from e
        self.db.commit()
        return self._salida([devolucion])[0]

    # ---- cobro con tarjeta de la diferencia de un cambio: primero se inicia, luego se confirma al registrar el cambio ----
    def iniciar_diferencia(self, datos: schemas.DevolucionIn) -> schemas.DiferenciaOut:
        pedido, _, _, _, _, _, adicional = self._preparar(datos)
        if adicional <= 0:
            raise DatosInvalidos(MSG_SIN_DIFERENCIA)
        pasarela = obtener_pasarela()
        try:
            intento = pasarela.crear_intento(
                monto_bob=adicional, descripcion=f"Cambio de la venta {pedido.codigo}", metadata={"pedido": pedido.codigo, "empresa_id": str(self.empresa_id)},
                cliente_ref=None, metodo_ref=None, guardar=False,
            )
        except AppError:
            raise
        except Exception as e:
            raise PasarelaNoDisponible(MSG_PASARELA) from e
        for abierto in self.intentos.abiertos(pedido.id, self.ctx.usuario.id):  # un solo cobro abierto por venta y cajero
            self._anular_cobro(abierto.id, abierto.referencia, pasarela_para(abierto.proveedor), confirmar=False)
        fila = self.intentos.agregar(IntentoDiferencia(
            pedido_id=pedido.id, usuario_id=self.ctx.usuario.id, monto=adicional, proveedor=pasarela.proveedor, referencia=intento.referencia,
            monto_pasarela=intento.monto_pasarela, moneda_pasarela=intento.moneda_pasarela,
        ))
        self.db.commit()
        return schemas.DiferenciaOut(
            pago_id=fila.id, modo=pasarela.modo, publishable_key=pasarela.publishable_key, client_secret=intento.client_secret, monto=adicional, moneda="BOB",
            monto_pasarela=intento.monto_pasarela / 100, moneda_pasarela=intento.moneda_pasarela.upper(),
        )

    def _preparar(self, datos: schemas.DevolucionIn):
        """Pasos 2 y 3: valida el comprobante, el plazo, el motivo, las prendas y calcula lo devuelto, lo entregado y la diferencia. No cambia nada."""
        pedido = self._pedido(datos.comprobante)
        self._plazo(pedido, exigir=True)
        if not datos.motivo.strip():
            raise DatosInvalidos(MSG_MOTIVO)
        if not datos.items:
            raise DatosInvalidos(MSG_SIN_PRENDAS)
        if datos.tipo == "CAMBIO" and not datos.nuevos:
            raise DatosInvalidos(MSG_CAMBIO_SIN_NUEVAS)
        if datos.tipo == "DEVOLUCION" and datos.nuevos:
            raise DatosInvalidos(MSG_DEVOLUCION_CON_NUEVAS)

        devueltas = self._a_devolver(pedido, datos)
        nuevas = self._nuevas(datos) if datos.nuevos else []
        devuelto = sum((i.precio_final * c for i, c in devueltas), CERO)
        entregado = sum((precio * c for _, precio, c in nuevas), CERO)
        return pedido, devueltas, nuevas, devuelto, entregado, max(devuelto - entregado, CERO), max(entregado - devuelto, CERO)

    def _guardar(self, datos, pedido, devueltas, nuevas, montos, efectivo, tarjeta) -> Devolucion:
        devuelto, entregado, reembolso, adicional = montos
        recibido, vuelto = efectivo
        devolucion = self.devoluciones.agregar(Devolucion(
            numero=self.devoluciones.siguiente_numero(pedido.sucursal_id), pedido_id=pedido.id, sucursal_id=pedido.sucursal_id, tipo=datos.tipo,
            motivo=datos.motivo.strip(), monto_devuelto=devuelto, monto_nuevo=entregado, reembolso=reembolso, cobro_adicional=adicional,
            medio_cobro=datos.cobro.metodo if adicional else None, monto_recibido=recibido, cambio_entregado=vuelto, registrada_por=self.ctx.usuario.id,
        ))
        for item, cantidad in devueltas:
            devolucion.items.append(DevolucionItem(
                empresa_id=self.empresa_id, sentido="DEVUELTA", pedido_item_id=item.id, variante_id=item.variante_id, sku=item.sku, producto=item.producto,
                talla=item.talla, color=item.color, cantidad=cantidad, precio_final=item.precio_final, subtotal=item.precio_final * cantidad,
            ))
        for variante, precio, cantidad in nuevas:
            devolucion.items.append(DevolucionItem(
                empresa_id=self.empresa_id, sentido="ENTREGADA", variante_id=variante.id, sku=variante.sku, producto=variante.producto.nombre,
                talla=variante.talla.codigo, color=variante.color.nombre, cantidad=cantidad, precio_final=precio, subtotal=precio * cantidad,
            ))
        self.db.flush()
        self._mover_inventario(pedido, devolucion, devueltas, nuevas)
        if reembolso > 0:
            self._reembolsar(pedido, devolucion, reembolso)
        if tarjeta:
            intento, pasarela, r = tarjeta
            intento.estado = "USADO"
            devolucion.referencia_cobro, devolucion.cobro_pasarela, devolucion.proveedor_cobro = intento.referencia, intento.monto_pasarela, intento.proveedor
            devolucion.cobro_tarjeta_marca, devolucion.cobro_tarjeta_ultimos4 = r.marca, r.ultimos4
        return devolucion

    # ---- consultas ----
    def listar(self, sucursal: int | None, desde: datetime | None, hasta: datetime | None) -> list[schemas.DevolucionOut]:
        return self._salida(self.devoluciones.buscar(self._alcance(sucursal), desde, hasta))

    def obtener(self, devolucion_id: int) -> schemas.DevolucionOut:
        return self._salida([self._propia(devolucion_id)])[0]

    def nota(self, devolucion_id: int) -> tuple[bytes, str]:
        devolucion = self._propia(devolucion_id)
        pedido = self.compras.pedidos.obtener_completo(devolucion.pedido_id)
        autor = nombres_de_usuarios(self.db, self.empresa_id, {devolucion.registrada_por} if devolucion.registrada_por else set())
        pdf = generar_nota(
            datos_de_empresa(self.db, self.empresa_id), datos_de_sucursal(self.db, self.empresa_id, devolucion.sucursal_id), devolucion,
            pedido.comprobante_numero or "", autor.get(devolucion.registrada_por, ""),
        )
        return pdf, f"{devolucion.numero}.pdf"

    # ---- plazo configurable por la empresa (RN15) ----
    def plazo(self) -> schemas.ConfiguracionOut:
        return schemas.ConfiguracionOut(plazo_dias=self.configuracion.plazo_dias())

    def fijar_plazo(self, dias: int) -> schemas.ConfiguracionOut:
        self.configuracion.fijar_plazo(dias)
        self.db.commit()
        return self.plazo()

    # ---- auxiliares ----
    def _pedido(self, comprobante: str) -> Pedido:
        numero = comprobante.strip()
        if not numero:
            raise DatosInvalidos(MSG_SIN_COMPROBANTE)
        pedido = self.compras.venta_por_comprobante(numero, sucursal_de_caja(self.ctx))
        if pedido is None:
            raise NoEncontrado(MSG_NO_ENCONTRADA)  # también si es de otra sucursal u otra empresa
        return pedido

    def _plazo(self, pedido: Pedido, exigir: bool = False) -> tuple[int, datetime]:
        dias = self.configuracion.plazo_dias()
        vence = pedido.pagado_en + timedelta(days=dias)
        if exigir and ahora() > vence:
            raise Conflicto(f"El plazo para devolver o cambiar esta compra venció el {a_local(vence):%d/%m/%Y} (plazo de {dias} días).")
        return dias, vence

    def _a_devolver(self, pedido: Pedido, datos: schemas.DevolucionIn) -> list[tuple]:
        """Valida cada prenda: debe ser de la venta y no se puede devolver más de lo vendido, ni dos veces lo mismo."""
        pedidas: dict[int, int] = {}
        for i in datos.items:
            pedidas[i.pedido_item_id] = pedidas.get(i.pedido_item_id, 0) + i.cantidad
        propias = {i.id: i for i in pedido.items}
        devueltas = self.devoluciones.devuelto_por_item(pedido.id)
        salida = []
        for item_id, cantidad in pedidas.items():
            item = propias.get(item_id)
            if item is None:
                raise DatosInvalidos(MSG_AJENA)
            nombre = f"{item.producto} ({item.talla}, {item.color})"
            quedan = item.cantidad - devueltas.get(item_id, 0)
            if quedan <= 0:
                raise Conflicto(f"{nombre} ya fue devuelto por completo.")
            if cantidad > quedan:
                raise Conflicto(f"Solo se pueden devolver {quedan} unidad(es) de {nombre}: se vendieron {item.cantidad} y ya se devolvieron {devueltas.get(item_id, 0)}.")
            salida.append((item, cantidad))
        return salida

    def _nuevas(self, datos: schemas.DevolucionIn) -> list[tuple]:
        """Prendas del cambio con su precio vigente (promociones incluidas)."""
        pedidas: dict[int, int] = {}
        for n in datos.nuevos:
            pedidas[n.variante_id] = pedidas.get(n.variante_id, 0) + n.cantidad
        variantes = self.variantes.vendibles(set(pedidas))
        if len(variantes) != len(pedidas):
            raise DatosInvalidos(MSG_NO_DISPONIBLE)
        descuentos = descuentos_vigentes(self.db, self.empresa_id)
        return [(v, descuentos.precio_final(v.producto, v.precio)[0], pedidas[v.id]) for v in variantes.values()]

    def _cobro_adicional(self, datos: schemas.DevolucionIn, adicional: Decimal) -> tuple[Decimal | None, Decimal | None]:
        """Si la prenda nueva vale más, el cliente paga la diferencia como prefiera: efectivo (con cambio) o tarjeta."""
        if adicional <= 0:
            return None, None
        if datos.cobro is None:
            raise DatosInvalidos(f"El cambio tiene una diferencia de Bs {adicional} a cobrar: indique cómo paga el cliente.")
        if datos.cobro.metodo == "TARJETA":
            if datos.cobro.intento_id is None:
                raise DatosInvalidos(MSG_COBRO_TARJETA)
            return None, None
        if datos.cobro.monto_recibido is None or datos.cobro.monto_recibido < adicional:
            raise DatosInvalidos("El monto recibido es menor a la diferencia a cobrar.")
        return datos.cobro.monto_recibido, datos.cobro.monto_recibido - adicional

    def _autorizar_tarjeta(self, pedido: Pedido, cobro: schemas.CobroDiferenciaIn, adicional: Decimal):
        """La pasarela autoriza la tarjeta (todavía no cobra): si la rechaza, no se registra nada."""
        intento = self.intentos.bloquear(cobro.intento_id)
        if intento is None or intento.pedido_id != pedido.id or intento.usuario_id != self.ctx.usuario.id:
            raise NoEncontrado("Cobro de la diferencia no encontrado.")
        if intento.estado != "PENDIENTE" or intento.monto != adicional:
            raise Conflicto(MSG_DIFERENCIA_CAMBIO)
        pasarela = pasarela_para(intento.proveedor)
        if pasarela is None:
            raise PasarelaNoDisponible(MSG_PASARELA)
        try:
            r = pasarela.confirmar(referencia=intento.referencia, tarjeta=Tarjeta(**cobro.tarjeta.model_dump()) if cobro.tarjeta else None, escenario_guardado=None)
        except AppError:
            raise  # datos de tarjeta inválidos (422)
        except Exception as e:
            raise PasarelaNoDisponible(MSG_PASARELA) from e
        if r.estado == "RECHAZADO":
            raise PagoRechazado(MSG_RECHAZO, extra={"motivo": r.motivo})
        if r.estado != "AUTORIZADO":  # la pasarela no respondió: no se registra el cambio hasta confirmar el cobro
            raise PasarelaNoDisponible(MSG_PASARELA)
        return intento, pasarela, r

    def _anular_cobro(self, intento_id: int, referencia: str, pasarela, confirmar: bool = True) -> None:
        """Anula la autorización de la tarjeta (no se cobra) y deja el intento CANCELADO."""
        if pasarela is not None:
            try:
                pasarela.cancelar(referencia)
            except Exception:  # si la pasarela no responde, igual no se registró el cambio
                pass
        fila = self.intentos.bloquear(intento_id)
        if fila is not None:
            fila.estado = "CANCELADO"
        if confirmar:
            self.db.commit()

    def _mover_inventario(self, pedido: Pedido, devolucion: Devolucion, devueltas: list[tuple], nuevas: list[tuple]) -> None:
        """Lo devuelto vuelve a disponible de la sucursal (DEVOLUCION); lo entregado en un cambio se descuenta (VENTA). Todo con referencia DEVOLUCION."""
        nota = f"Nota {devolucion.numero}: {devolucion.motivo}"[:200]
        lineas = {}
        for item, cantidad in devueltas:
            lineas[item.variante_id] = lineas.get(item.variante_id, 0) + cantidad
        aplicar_movimientos(self.db, self.empresa_id, pedido.sucursal_id, list(lineas.items()), "DEVOLUCION", "DEVOLUCION", devolucion.id, self.ctx.usuario.id, nota)
        if nuevas:
            pedidas = {v.id: c for v, _, c in nuevas}
            disponibles = disponible_por_variante(self.db, self.empresa_id, pedidas, pedido.sucursal_id)  # ya incluye lo que acaba de volver
            faltantes = [f"{v.producto.nombre} ({v.talla.codigo}, {v.color.nombre}): solicitadas {c}, disponibles {disponibles.get(v.id, 0)}" for v, _, c in nuevas if disponibles.get(v.id, 0) < c]
            if faltantes:
                sucursal = nombres_de_sucursales(self.db, self.empresa_id).get(pedido.sucursal_id, "")
                raise Conflicto(f"No hay stock suficiente en {sucursal} para el cambio: " + "; ".join(faltantes) + ".")
            aplicar_movimientos(self.db, self.empresa_id, pedido.sucursal_id, list(pedidas.items()), "VENTA", "DEVOLUCION", devolucion.id, self.ctx.usuario.id, f"Cambio {devolucion.numero}")

    def _reembolsar(self, pedido: Pedido, devolucion: Devolucion, monto: Decimal) -> None:
        """Con tarjeta, el dinero vuelve por la misma pasarela del pago; en efectivo queda registrada la devolución del dinero."""
        pago = self.compras.pago_aprobado(pedido)
        if pago is None:
            raise Conflicto("La venta no tiene un pago aprobado que reembolsar.")
        devolucion.medio_reembolso = pago.metodo
        if pago.metodo != "TARJETA":
            return
        pasarela = pasarela_para(pago.proveedor)
        if pasarela is None:
            raise ReembolsoFallido(MSG_REEMBOLSO)
        ya_bob, ya_centavos = self.devoluciones.reembolsado_con_tarjeta(pedido.id)
        try:
            r = pasarela.reembolsar(pago.referencia_externa, monto, pago.monto - ya_bob, (pago.monto_pasarela or 0) - ya_centavos)
        except Exception as e:  # la pasarela no respondió: no se registra la devolución, para no dejar el inventario y el dinero descuadrados
            raise ReembolsoFallido(MSG_REEMBOLSO) from e
        devolucion.referencia_reembolso, devolucion.reembolso_pasarela = r.referencia, r.centavos

    def _alcance(self, sucursal: int | None) -> int | None:
        """El personal de caja solo ve su sucursal; el Administrador, todas (o la que indique)."""
        return sucursal if self.ctx.rol == ADMIN else sucursal_de_caja(self.ctx)

    def _propia(self, devolucion_id: int) -> Devolucion:
        d = self.devoluciones.obtener_completa(devolucion_id)
        if d is None or (self.ctx.rol != ADMIN and d.sucursal_id != self.ctx.sucursal_id):
            raise NoEncontrado("Devolución no encontrada.")  # también si es de otra sucursal u otra empresa
        return d

    def _salida(self, devoluciones: list[Devolucion]) -> list[schemas.DevolucionOut]:
        sucursales = nombres_de_sucursales(self.db, self.empresa_id)
        autores = nombres_de_usuarios(self.db, self.empresa_id, {d.registrada_por for d in devoluciones if d.registrada_por})
        pedidos = {d.pedido_id: self.compras.pedidos.obtener(d.pedido_id) for d in devoluciones}
        return [
            schemas.DevolucionOut(
                id=d.id, numero=d.numero, tipo=d.tipo, motivo=d.motivo, comprobante=pedidos[d.pedido_id].comprobante_numero, pedido_codigo=pedidos[d.pedido_id].codigo,
                sucursal_id=d.sucursal_id, sucursal=sucursales.get(d.sucursal_id, ""), fecha=d.creada_en, monto_devuelto=d.monto_devuelto, monto_nuevo=d.monto_nuevo,
                reembolso=d.reembolso, cobro_adicional=d.cobro_adicional, medio_reembolso=d.medio_reembolso, referencia_reembolso=d.referencia_reembolso,
                medio_cobro=d.medio_cobro, monto_recibido=d.monto_recibido, cambio_entregado=d.cambio_entregado,
                tarjeta_cobro=f"{d.cobro_tarjeta_marca} ****{d.cobro_tarjeta_ultimos4}" if d.cobro_tarjeta_ultimos4 else None, registrada_por=autores.get(d.registrada_por),
                items=[schemas.ItemDevolucionOut.model_validate(i, from_attributes=True) for i in d.items],
            )
            for d in devoluciones
        ]

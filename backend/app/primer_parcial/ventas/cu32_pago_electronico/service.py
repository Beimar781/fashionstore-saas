"""CU-32 · Procesar pago electrónico web/móvil (RN01, RN02). Capa de negocio.

Flujo: `iniciar` consolida el monto del pedido y crea el intento en la pasarela → el cliente ingresa su tarjeta (Stripe.js en el navegador,
o el formulario de pruebas si no hay claves) → `confirmar` lee la respuesta de la pasarela: si aprobó, se descuenta el stock y recién
entonces se cobra; si rechazó, el pedido sigue por pagar; si la pasarela no responde, queda «pendiente de confirmación» (`reconciliar`).
"""
import logging

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.constantes import CLIENTE
from app.core.errors import AppError, Conflicto, NoEncontrado
from app.modules.acceso.dependencias import Contexto
from app.primer_parcial.ventas.cu11_compra_digital.schemas import PagoResumenOut
from app.primer_parcial.ventas.cu11_compra_digital.service import MSG_RECHAZO, CompraService, SinStock
from app.primer_parcial.ventas.cu32_pago_electronico import schemas
from app.primer_parcial.ventas.cu32_pago_electronico.pasarela import TARJETAS_PRUEBA, Resultado, Tarjeta, obtener_pasarela
from app.primer_parcial.ventas.cu32_pago_electronico.repository import ClientePasarelaRepository, PagoRepository, TarjetaRepository
from app.primer_parcial.ventas.models import ClientePasarela, Pago, Pedido, TarjetaGuardada

logger = logging.getLogger(__name__)
MSG_PENDIENTE = "Pendiente de confirmación: la pasarela no respondió. Verificaremos el estado de su pago; no se le cobrará dos veces."
MSG_APROBADO = "Pago aprobado."


class PagoRechazado(AppError):
    """La pasarela rechazó la tarjeta (402). El detalle del banco viaja en `motivo`."""

    status_code = 402


class PasarelaNoDisponible(AppError):
    status_code = 502


class PagoService:
    def __init__(self, db: Session, ctx: Contexto, pasarela=None):
        self.db = db
        self.ctx = ctx
        self.empresa_id = ctx.empresa_id
        self.pasarela = pasarela or obtener_pasarela()
        self.pagos = PagoRepository(db, ctx.empresa_id)
        self.tarjetas = TarjetaRepository(db, ctx.empresa_id)
        self.clientes = ClientePasarelaRepository(db, ctx.empresa_id)
        self.compras = CompraService(db, ctx)

    # ---- configuración y tarjetas guardadas ----
    def config(self) -> schemas.ConfigPagoOut:
        simulado = self.pasarela.proveedor == "SIMULADO"
        return schemas.ConfigPagoOut(
            modo=self.pasarela.modo, publishable_key=self.pasarela.publishable_key,
            tarjetas_prueba=[schemas.TarjetaPruebaOut(numero=t["numero"], marca=t["marca"], resultado=t["resultado"]) for t in TARJETAS_PRUEBA] if simulado else [],
            moneda_pasarela="USD", tasa_bob_por_usd=get_settings().tasa_bob_por_usd,
        )

    def listar_tarjetas(self) -> list[TarjetaGuardada]:
        return self.tarjetas.de_cliente(self.ctx.usuario.id, self.pasarela.proveedor)

    def eliminar_tarjeta(self, tarjeta_id: int) -> None:
        tarjeta = self.tarjetas.del_cliente(tarjeta_id, self.ctx.usuario.id)
        if tarjeta is None:
            raise NoEncontrado("Tarjeta no encontrada.")
        if tarjeta.proveedor == self.pasarela.proveedor:
            self.pasarela.eliminar_metodo(tarjeta.referencia)
        self.db.delete(tarjeta)
        self.db.commit()

    # ---- pasos 1 y 2: consolidar el monto y pedirlo a la pasarela ----
    def iniciar(self, pedido_id: int, datos: schemas.IniciarIn) -> schemas.IniciarOut:
        pedido = self._pedido(pedido_id)
        if pedido.estado != "PENDIENTE_PAGO":
            raise Conflicto("El pedido no está pendiente de pago.")
        faltante = self.compras.faltantes_ahora(pedido)
        if faltante:  # si el stock cambió desde el carrito, se avisa antes de pedir la tarjeta
            raise SinStock(faltante)
        guardada = None
        guardar = datos.guardar_tarjeta and self._es_cliente  # en caja no se guardan tarjetas
        if datos.tarjeta_guardada_id is not None and self._es_cliente:
            guardada = self.tarjetas.del_cliente(datos.tarjeta_guardada_id, self.ctx.usuario.id)
            if guardada is None or guardada.proveedor != self.pasarela.proveedor:
                raise NoEncontrado("Tarjeta no encontrada.")
        for abierto in self.pagos.abiertos_de(pedido.id):  # un solo intento de pago abierto por pedido
            if abierto.referencia_externa:
                self.pasarela.cancelar(abierto.referencia_externa)
            abierto.estado = "CANCELADO"

        try:
            intento = self.pasarela.crear_intento(
                monto_bob=pedido.total, descripcion=f"Pedido {pedido.codigo}", metadata={"pedido": pedido.codigo, "empresa_id": str(self.empresa_id)},
                cliente_ref=self._cliente_pasarela(), metodo_ref=guardada.referencia if guardada else None, guardar=guardar,
            )
        except AppError:
            raise
        except Exception as e:  # error de red o de la pasarela
            raise PasarelaNoDisponible("No se pudo comunicar con la pasarela de pago. Intente nuevamente.") from e
        pago = self.pagos.agregar(Pago(
            pedido_id=pedido.id, metodo="TARJETA", proveedor=self.pasarela.proveedor, estado="PENDIENTE", monto=pedido.total, moneda=pedido.moneda,
            monto_pasarela=intento.monto_pasarela, moneda_pasarela=intento.moneda_pasarela, referencia_externa=intento.referencia,
            metodo_pago_ref=guardada.referencia if guardada else None, guardar_tarjeta=guardar and guardada is None,
            usuario_id=self.ctx.usuario.id,
        ))
        self.db.commit()
        return schemas.IniciarOut(
            pago_id=pago.id, modo=self.pasarela.modo, publishable_key=self.pasarela.publishable_key, client_secret=intento.client_secret,
            monto=pedido.total, moneda=pedido.moneda, monto_pasarela=intento.monto_pasarela / 100, moneda_pasarela=intento.moneda_pasarela.upper(),
            tarjeta_guardada=schemas.TarjetaGuardadaOut.model_validate(guardada) if guardada else None,
        )

    # ---- pasos 3 a 5: la respuesta de la pasarela actualiza el pedido ----
    def confirmar(self, pago_id: int, datos: schemas.ConfirmarIn) -> schemas.ResultadoPagoOut:
        pago, pedido = self._pago_y_pedido(pago_id)
        if pago.estado == "APROBADO":
            return self._resultado(pago, pedido)  # repetir la confirmación no cobra otra vez
        if pago.estado in ("RECHAZADO", "CANCELADO"):
            raise Conflicto("Este pago ya fue procesado. Inicie un nuevo pago.")
        escenario, guardada = None, None
        if pago.metodo_pago_ref and self.pasarela.proveedor == "SIMULADO":
            guardada = self.tarjetas.por_referencia(pago.metodo_pago_ref, self.ctx.usuario.id)
            escenario = guardada.escenario if guardada else "RECHAZADA"
        tarjeta = Tarjeta(**datos.tarjeta.model_dump()) if datos.tarjeta else None
        try:
            resultado = self.pasarela.confirmar(referencia=pago.referencia_externa, tarjeta=tarjeta, escenario_guardado=escenario)
        except AppError:
            raise  # datos de tarjeta inválidos (422): el pago sigue pendiente
        except Exception:
            resultado = Resultado("PENDIENTE_CONFIRMACION")  # la pasarela no respondió
        if guardada is not None:  # con una tarjeta guardada se muestra la misma marca y últimos 4 dígitos
            resultado.marca, resultado.ultimos4, resultado.exp_mes, resultado.exp_anio = guardada.marca, guardada.ultimos4, guardada.exp_mes, guardada.exp_anio
        return self._aplicar(pago, pedido, resultado)

    def reconciliar(self, pago_id: int) -> schemas.ResultadoPagoOut:
        """Vuelve a preguntar a la pasarela por un pago que quedó «pendiente de confirmación»."""
        pago, pedido = self._pago_y_pedido(pago_id)
        if pago.estado == "APROBADO":
            return self._resultado(pago, pedido)
        if pago.estado != "PENDIENTE_CONFIRMACION":
            raise Conflicto("Este pago no está pendiente de confirmación.")
        try:
            resultado = self.pasarela.consultar(pago.referencia_externa)
        except Exception:
            resultado = Resultado("PENDIENTE_CONFIRMACION")
        return self._aplicar(pago, pedido, resultado)

    def obtener(self, pago_id: int) -> schemas.ResultadoPagoOut:
        pago, pedido = self._pago_y_pedido(pago_id)
        return self._resultado(pago, pedido)

    # ---- aplicar la respuesta de la pasarela ----
    def _aplicar(self, pago: Pago, pedido: Pedido, r: Resultado) -> schemas.ResultadoPagoOut:
        pago_id, pedido_id = pago.id, pedido.id
        if r.marca:
            pago.tarjeta_marca, pago.tarjeta_ultimos4 = r.marca, r.ultimos4

        if r.estado == "RECHAZADO":
            pago.estado, pago.motivo, pago.mensaje = "RECHAZADO", r.motivo, MSG_RECHAZO
            self.db.commit()  # queda registrado el intento rechazado; el pedido sigue por pagar
            raise PagoRechazado(MSG_RECHAZO, extra={"motivo": r.motivo, "pago_id": pago_id})

        if r.estado == "PENDIENTE_CONFIRMACION":
            pago.estado, pago.mensaje = "PENDIENTE_CONFIRMACION", MSG_PENDIENTE
            pedido.estado = "PENDIENTE_CONFIRMACION"
            self.db.commit()
            return self._resultado(pago, pedido)

        # AUTORIZADO: se confirma el stock y recién entonces se cobra
        try:
            self.compras.finalizar(pedido)
            self.pasarela.capturar(pago.referencia_externa)
        except SinStock as e:
            self.db.rollback()  # no queda ningún descuento de stock a medias
            self.pasarela.cancelar(pago.referencia_externa)  # se anula la autorización: no se cobra
            pago, pedido = self._pago_y_pedido(pago_id)
            pago.estado, pago.motivo, pago.mensaje = "CANCELADO", "Sin stock al cobrar", str(e)
            self.compras.cancelar(pedido, "Sin stock al momento del pago.")
            self.db.commit()
            raise
        except Exception:  # no se pudo cobrar: nada se descuenta y queda por conciliar
            logger.exception("No se pudo completar el cobro del pago %s", pago_id)
            self.db.rollback()
            pago, pedido = self._pago_y_pedido(pago_id)
            pago.estado, pago.mensaje = "PENDIENTE_CONFIRMACION", MSG_PENDIENTE
            pedido.estado = "PENDIENTE_CONFIRMACION"
            self.db.commit()
            return self._resultado(pago, pedido)

        pago.estado, pago.mensaje, pago.motivo = "APROBADO", MSG_APROBADO, ""
        pago.tarjeta_marca, pago.tarjeta_ultimos4 = r.marca or pago.tarjeta_marca, r.ultimos4 or pago.tarjeta_ultimos4
        if pago.guardar_tarjeta and r.metodo_ref and r.ultimos4 and not self.tarjetas.existe(self.ctx.usuario.id, r.marca, r.ultimos4, r.exp_mes, r.exp_anio):
            self.tarjetas.agregar(TarjetaGuardada(
                cliente_id=self.ctx.usuario.id, proveedor=pago.proveedor, referencia=r.metodo_ref, marca=r.marca, ultimos4=r.ultimos4,
                exp_mes=r.exp_mes, exp_anio=r.exp_anio, escenario=r.escenario if pago.proveedor == "SIMULADO" else "",
            ))
        self.db.commit()
        return self._resultado(pago, pedido)

    # ---- auxiliares ----
    def _resultado(self, pago: Pago, pedido: Pedido) -> schemas.ResultadoPagoOut:
        return schemas.ResultadoPagoOut(
            aprobado=pago.estado == "APROBADO", pendiente=pago.estado == "PENDIENTE_CONFIRMACION", mensaje=pago.mensaje,
            pago=PagoResumenOut.model_validate(pago, from_attributes=True), pedido=self.compras.salida([pedido])[0],
        )

    @property
    def _es_cliente(self) -> bool:
        return self.ctx.rol == CLIENTE

    def _pedido(self, pedido_id: int) -> Pedido:
        """Un cliente paga sus pedidos digitales; el personal de caja cobra con tarjeta las ventas presenciales de su sucursal."""
        pedido = self.compras.pedidos.obtener_completo(pedido_id)
        propio = pedido is not None and (
            (pedido.cliente_id == self.ctx.usuario.id and pedido.canal == "DIGITAL") if self._es_cliente
            else (pedido.canal == "PRESENCIAL" and pedido.sucursal_id == self.ctx.sucursal_id)
        )
        if not propio:
            raise NoEncontrado("Pedido no encontrado.")  # también si es de otro cliente, de otra sucursal o de otra empresa
        return pedido

    def _pago_y_pedido(self, pago_id: int) -> tuple[Pago, Pedido]:
        pago = self.pagos.del_pedido_visible(pago_id, self.ctx.usuario.id if self._es_cliente else None, self.ctx.sucursal_id)
        if pago is None:
            raise NoEncontrado("Pago no encontrado.")
        return pago, self._pedido(pago.pedido_id)

    def _cliente_pasarela(self) -> str | None:
        """Cliente del comprador en Stripe (se crea la primera vez) para poder guardar y reutilizar sus tarjetas."""
        if self.pasarela.proveedor != "STRIPE" or not self._es_cliente:
            return None
        fila = self.clientes.de_cliente(self.ctx.usuario.id)
        referencia = self.pasarela.asegurar_cliente(self.ctx.usuario.email, f"{self.ctx.usuario.nombre} {self.ctx.usuario.apellidos}", fila.referencia if fila else None)
        if fila is None:
            self.clientes.agregar(ClientePasarela(cliente_id=self.ctx.usuario.id, referencia=referencia))
        return referencia

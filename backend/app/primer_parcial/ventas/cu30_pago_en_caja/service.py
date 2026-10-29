"""CU-30 · Procesar pago y emitir comprobante en caja (RN10). Capa de negocio.

El efectivo se cobra aquí; con tarjeta se usa la pasarela de CU-32. Al aprobarse el cobro el stock se descuenta en la misma
transacción y se emite el comprobante: si el servicio de impuestos no responde, la venta no se pierde y queda un comprobante interno temporal.
"""
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import Conflicto, DatosInvalidos
from app.modules.acceso.dependencias import Contexto
from app.modules.acceso.publico import nombres_de_usuarios
from app.modules.plataforma.publico import datos_de_empresa
from app.modules.sucursales.publico import datos_de_sucursal
from app.primer_parcial.ventas.cu11_compra_digital.schemas import PagoResumenOut
from app.primer_parcial.ventas.cu11_compra_digital.service import CompraService
from app.primer_parcial.ventas.cu12_historial_compras.comprobante import generar_pdf
from app.primer_parcial.ventas.cu28_productos_en_caja.service import sucursal_de_caja
from app.primer_parcial.ventas.cu30_pago_en_caja import schemas
from app.primer_parcial.ventas.models import Pago, Pedido

MSG_MONTO_MENOR = "El monto recibido es menor al total de la venta."
MSG_FALTA_MONTO = "Ingrese el monto recibido."


class CobroCajaService:
    def __init__(self, db: Session, ctx: Contexto, impuestos=None):
        self.db = db
        self.ctx = ctx
        self.sucursal_id = sucursal_de_caja(ctx)
        self.compras = CompraService(db, ctx, impuestos)

    def cobrar(self, pedido_id: int, datos: schemas.CobroIn, commit: bool = True, descontar: bool = True) -> schemas.CobroOut:
        pedido = self.compras.venta_de_caja(pedido_id, self.sucursal_id)
        if pedido.estado != "PENDIENTE_PAGO":
            raise Conflicto("La venta no está pendiente de cobro.")
        recibido, cambio = self._importes(pedido, datos)
        self.compras.finalizar(pedido, descontar)  # descuenta el stock; si se agotó lanza SinStock y no se registra ningún cobro
        pago = Pago(
            empresa_id=pedido.empresa_id, pedido_id=pedido.id, metodo=datos.metodo, proveedor="CAJA", estado="APROBADO", monto=pedido.total,
            moneda=pedido.moneda, monto_recibido=recibido, cambio=cambio, mensaje="Pago aprobado.", usuario_id=self.ctx.usuario.id,
        )
        self.db.add(pago)
        self.db.commit() if commit else self.db.flush()
        salida = self.compras.salida([pedido])[0]
        return schemas.CobroOut(pedido=salida, pago=PagoResumenOut.model_validate(pago, from_attributes=True), cambio=cambio, aviso=salida.comprobante_aviso)

    def comprobante(self, pedido_id: int) -> tuple[bytes, str]:
        """Paso 4: el comprobante en PDF listo para imprimir."""
        pedido = self.compras.venta_de_caja(pedido_id, self.sucursal_id)
        if pedido.estado != "PAGADO" or not pedido.comprobante_numero:
            raise Conflicto("Solo hay comprobante de ventas cobradas.")
        pago = next((g for g in reversed(self.compras.pedidos.pagos_de([pedido.id])[pedido.id]) if g.estado == "APROBADO"), None)
        nombres = nombres_de_usuarios(self.db, self.ctx.empresa_id, {u for u in (pedido.cliente_id, pedido.creado_por) if u})
        pdf = generar_pdf(
            datos_de_empresa(self.db, self.ctx.empresa_id), datos_de_sucursal(self.db, self.ctx.empresa_id, pedido.sucursal_id),
            nombres.get(pedido.cliente_id, "Consumidor final"), pedido, pago, get_settings().iva_porcentaje, atendio=nombres.get(pedido.creado_por),
        )
        return pdf, f"{pedido.comprobante_numero}.pdf"

    @staticmethod
    def _importes(pedido: Pedido, datos: schemas.CobroIn) -> tuple[Decimal, Decimal]:
        """Paso 2: en efectivo se calcula el cambio."""
        if datos.monto_recibido is None:
            raise DatosInvalidos(MSG_FALTA_MONTO)
        if datos.monto_recibido < pedido.total:
            raise DatosInvalidos(MSG_MONTO_MENOR)
        return datos.monto_recibido, datos.monto_recibido - pedido.total

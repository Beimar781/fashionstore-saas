"""CU-12 · Consultar historial de compras (RN02). Capa de negocio: el cliente solo ve sus propias compras."""
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import Conflicto, NoEncontrado
from app.modules.acceso.dependencias import Contexto
from app.modules.acceso.publico import nombres_de_usuarios
from app.modules.plataforma.publico import datos_de_empresa
from app.modules.sucursales.publico import datos_de_sucursal, nombres_de_sucursales
from app.primer_parcial.ventas.cu11_compra_digital.service import CompraService
from app.primer_parcial.ventas.cu12_historial_compras import schemas
from app.primer_parcial.ventas.cu12_historial_compras.comprobante import generar_pdf
from app.primer_parcial.ventas.cu12_historial_compras.repository import HistorialRepository
from app.primer_parcial.ventas.models import Pedido

MSG_SIN_COMPRAS = "Aún no has realizado ninguna compra en nuestras tiendas."  # excepción de la ficha CU-12


class HistorialService:
    def __init__(self, db: Session, ctx: Contexto):
        self.db = db
        self.ctx = ctx
        self.historial = HistorialRepository(db, ctx.empresa_id)
        self.compras = CompraService(db, ctx)

    def listar(self, estado: str | None) -> schemas.HistorialOut:
        pedidos = self.historial.del_cliente(self.ctx.usuario.id, estado)
        sucursales = nombres_de_sucursales(self.db, self.ctx.empresa_id)
        return schemas.HistorialOut(
            compras=[
                schemas.CompraResumenOut(
                    id=p.id, codigo=p.codigo, fecha=p.pagado_en or p.creado_en, sucursal=sucursales.get(p.sucursal_id, ""), canal=p.canal,
                    estado=p.estado, total=p.total, total_unidades=sum(i.cantidad for i in p.items), comprobante_numero=p.comprobante_numero,
                )
                for p in pedidos
            ],
            mensaje=None if pedidos else MSG_SIN_COMPRAS,
        )

    def detalle(self, pedido_id: int) -> schemas.PedidoOut:
        return self.compras.salida([self._propio(pedido_id)])[0]

    def comprobante(self, pedido_id: int) -> tuple[bytes, str]:
        pedido = self._propio(pedido_id)
        if pedido.estado != "PAGADO" or not pedido.comprobante_numero:
            raise Conflicto("Solo hay comprobante para compras pagadas.")
        pago = next((g for g in reversed(self.compras.pedidos.pagos_de([pedido.id])[pedido.id]) if g.estado == "APROBADO"), None)
        cliente = nombres_de_usuarios(self.db, self.ctx.empresa_id, {self.ctx.usuario.id}).get(self.ctx.usuario.id, "")
        pdf = generar_pdf(
            datos_de_empresa(self.db, self.ctx.empresa_id), datos_de_sucursal(self.db, self.ctx.empresa_id, pedido.sucursal_id),
            cliente, pedido, pago, get_settings().iva_porcentaje,
        )
        return pdf, f"{pedido.comprobante_numero}.pdf"

    def _propio(self, pedido_id: int) -> Pedido:
        pedido = self.historial.pedido_del_cliente(pedido_id, self.ctx.usuario.id)
        if pedido is None:
            raise NoEncontrado("Pedido no encontrado.")  # también si es de otro cliente o de otra empresa
        return pedido

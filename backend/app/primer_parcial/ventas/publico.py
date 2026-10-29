"""Interfaz pública del paquete P7 ventas (primer parcial) para otros paquetes.

La venta presencial (CU-29, SaaS), las devoluciones (CU-41) y los reportes usan los pedidos solo desde aquí.
"""
from app.primer_parcial.ventas.cu11_compra_digital.schemas import PagoResumenOut, PedidoOut  # noqa: F401
from app.primer_parcial.ventas.cu11_compra_digital.service import Linea, CompraService, SinStock  # noqa: F401
from app.primer_parcial.ventas.cu28_productos_en_caja.service import sucursal_de_caja  # noqa: F401
from app.primer_parcial.ventas.cu11_compra_digital.service import MSG_RECHAZO  # noqa: F401
from app.primer_parcial.ventas.cu32_pago_electronico.pasarela import Tarjeta, obtener_pasarela, pasarela_para  # noqa: F401
from app.primer_parcial.ventas.cu32_pago_electronico.schemas import TarjetaIn  # noqa: F401
from app.primer_parcial.ventas.cu32_pago_electronico.service import PagoRechazado, PasarelaNoDisponible  # noqa: F401
from app.primer_parcial.ventas.models import Pago, Pedido, PedidoItem  # noqa: F401  (entidades de solo lectura para los reportes)


def _ventas_del_mes(db, empresa_id: int) -> int:
    from sqlalchemy import func, select

    from app.core.tiempo import ahora

    inicio = ahora().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return db.scalar(select(func.count(Pedido.id)).where(Pedido.empresa_id == empresa_id, Pedido.estado == "PAGADO", Pedido.pagado_en >= inicio)) or 0


from app.modules.plataforma.publico import registrar_medidor  # noqa: E402

registrar_medidor("ventas_mes", "Ventas del mes", _ventas_del_mes)

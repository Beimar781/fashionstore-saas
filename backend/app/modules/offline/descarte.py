"""CU-40 · Descartar una venta de contado ya cobrada devolviendo el dinero (reutiliza CU-41, regla 15).

La venta sin conexión no alcanzó en el inventario, pero el efectivo ya se recibió en caja y la prenda salió con el cliente. Al descartarla se registra la venta
(sin descontar existencias, que ya no alcanzan) y enseguida su devolución con las mismas reglas de CU-41: la prenda se revisa (sin daños, sin desgaste, con
etiquetas), vuelve al inventario con su talla y color y se emite la nota de devolución. La salida de la venta se anota para que el inventario quede igual que antes.
Todo va en la transacción de quien llama.
"""
from sqlalchemy.orm import Session

from app.modules.acceso.dependencias import Contexto
from app.modules.offline.models import OperacionOffline
from app.modules.offline.schemas import VentaOfflineIn
from app.modules.ventas.publico import CondicionIn, DevolucionIn, DevolucionOut, DevolucionService, ItemDevueltoIn, LineaIn, VentaIn, VentaPresencialService
from app.primer_parcial.ventas.publico import CobroCajaService, CobroIn


def devolver_venta_descartada(db: Session, resolutor: Contexto, autor: Contexto, fila: OperacionOffline, condicion: CondicionIn, motivo: str) -> tuple[DevolucionOut, int]:
    datos = VentaOfflineIn.model_validate(fila.payload)
    venta = VentaPresencialService(db, autor).crear(
        VentaIn(items=[LineaIn(variante_id=i.variante_id, cantidad=i.cantidad) for i in datos.items], cliente_email=datos.cliente_email, nit_ci=datos.nit_ci, razon_social=datos.razon_social),
        commit=False, verificar_stock=False,
    )
    cobro = CobroCajaService(db, autor).cobrar(venta.id, CobroIn(metodo="EFECTIVO", monto_recibido=datos.monto_recibido), commit=False, descontar=False)
    en_la_sucursal = Contexto(resolutor.usuario, resolutor.rol, resolutor.empresa_id, fila.sucursal_id)  # el Administrador no tiene sucursal: actúa en la de la venta
    devolucion = DevolucionService(db, en_la_sucursal).registrar(
        DevolucionIn(
            comprobante=cobro.pedido.comprobante_numero or "", tipo="DEVOLUCION", motivo=f"Venta sin conexión descartada: {motivo}"[:200],
            items=[ItemDevueltoIn(pedido_item_id=i.id, cantidad=i.cantidad) for i in cobro.pedido.items], condicion=condicion,
        ),
        confirmar=False, venta_descartada=True,
    )
    return devolucion, venta.id

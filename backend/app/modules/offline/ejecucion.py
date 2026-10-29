"""Ejecuta una operación offline con los mismos casos de uso del trabajo en línea (regla 15): la venta de contado es la venta de caja (CU-29 y CU-30) y la reserva es CU-09.

Todo va en UNA transacción: el que llama hace el único commit junto con el registro de la operación (RNF04, RNF05).
Una falta de stock no deja nada a medias: se deshace todo y la operación queda en conflicto (RN14).
"""
from sqlalchemy.orm import Session

from app.core.errors import Conflicto
from app.modules.acceso.dependencias import Contexto
from app.modules.inventario.publico import disponible_por_variante
from app.modules.offline.repository import OperacionRepository
from app.modules.offline.schemas import VentaOfflineIn
from app.modules.reservas.publico import ReservaIn, ReservaService
from app.modules.ventas.publico import LineaIn, VentaIn, VentaPresencialService
from app.primer_parcial.ventas.publico import CobroCajaService, CobroIn, SinStock


class Resultado:
    def __init__(self, referencia: str | None, comprobante: str | None, pedido_id: int | None = None, reserva_id: int | None = None):
        self.referencia, self.comprobante, self.pedido_id, self.reserva_id = referencia, comprobante, pedido_id, reserva_id


def es_falta_de_stock(e: Exception) -> bool:
    return isinstance(e, SinStock) or (isinstance(e, Conflicto) and "stock suficiente" in e.message)


class Ejecutor:
    def __init__(self, db: Session, ctx: Contexto):
        self.db, self.ctx = db, ctx

    def ejecutar(self, tipo: str, payload: dict) -> Resultado:
        if tipo == "VENTA_CONTADO":
            datos = VentaOfflineIn.model_validate(payload)
            venta = VentaPresencialService(self.db, self.ctx).crear(
                VentaIn(items=[LineaIn(variante_id=i.variante_id, cantidad=i.cantidad) for i in datos.items], cliente_email=datos.cliente_email, nit_ci=datos.nit_ci, razon_social=datos.razon_social),
                commit=False,
            )
            cobro = CobroCajaService(self.db, self.ctx).cobrar(venta.id, CobroIn(metodo="EFECTIVO", monto_recibido=datos.monto_recibido), commit=False)  # RN13: de contado
            return Resultado(cobro.pedido.codigo, cobro.pedido.comprobante_numero, pedido_id=venta.id)
        reserva = ReservaService(self.db, self.ctx.empresa_id).crear(self.ctx, ReservaIn.model_validate(payload), commit=False)
        return Resultado(reserva.codigo, None, reserva_id=reserva.id)

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

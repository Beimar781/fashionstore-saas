"""CU-27 · Consultar ventas de la sucursal (RN10). Capa de negocio: el Encargado solo ve los datos de su sucursal."""
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.errors import NoEncontrado, Prohibido
from app.core.tiempo import a_local, ahora, zona_local
from app.modules.acceso.dependencias import Contexto
from app.modules.acceso.publico import nombres_de_usuarios
from app.modules.sucursales.publico import nombres_de_sucursales
from app.primer_parcial.reportes.cu27_ventas_sucursal import schemas
from app.primer_parcial.reportes.cu27_ventas_sucursal.repository import VentasSucursalRepository
from app.primer_parcial.ventas.publico import CompraService, PedidoOut

MSG_OTRA_SUCURSAL = "Acceso denegado a datos de otras sucursales."  # excepción de la ficha CU-27
CERO = Decimal("0.00")


def _rango(desde: date, hasta: date) -> tuple[datetime, datetime]:
    """Los días completos, en hora de la tienda (el fin es el día siguiente a `hasta`)."""
    inicio = datetime.combine(desde, time.min, tzinfo=zona_local())
    return inicio, datetime.combine(hasta, time.min, tzinfo=zona_local()) + timedelta(days=1)


class VentasSucursalService:
    def __init__(self, db: Session, ctx: Contexto):
        if ctx.sucursal_id is None:
            raise Prohibido("Su usuario no tiene una sucursal asignada.")
        self.db = db
        self.ctx = ctx
        self.sucursal_id = ctx.sucursal_id
        self.ventas = VentasSucursalRepository(db, ctx.empresa_id)

    def _sucursal(self, pedida: int | None) -> int:
        """Paso 5 de la prueba: pedir los datos de otra sucursal se bloquea con el mensaje de la ficha."""
        if pedida is not None and pedida != self.sucursal_id:
            raise Prohibido(MSG_OTRA_SUCURSAL)
        return self.sucursal_id

    def resumen(self, fecha: date | None, sucursal: int | None) -> schemas.ResumenDiaOut:
        sucursal_id = self._sucursal(sucursal)
        dia = fecha or a_local(ahora()).date()
        desde, hasta = _rango(dia, dia)
        canales = self.ventas.totales_por_canal(sucursal_id, desde, hasta)

        def canal(nombre: str) -> schemas.TotalCanal:
            n, u, t = canales.get(nombre, (0, 0, CERO))
            return schemas.TotalCanal(ventas=n, unidades=u, total=t)

        total = sum((t for _, _, t in canales.values()), CERO)
        ventas = sum(n for n, _, _ in canales.values())
        cierre = [
            schemas.CierreMetodo(metodo=m, cobros=n, total=t, recibido=r if m == "EFECTIVO" else None, cambio=c if m == "EFECTIVO" else None)
            for m, n, t, r, c in self.ventas.cierre_por_metodo(sucursal_id, desde, hasta)
        ]
        dev = self.ventas.devoluciones(sucursal_id, desde, hasta)
        reemb, cobros = dev["reembolsos"], dev["cobros"]
        efectivo = next((c.total for c in cierre if c.metodo == "EFECTIVO"), CERO) + cobros.get("EFECTIVO", CERO) - reemb.get("EFECTIVO", CERO)
        return schemas.ResumenDiaOut(
            fecha=dia, sucursal_id=sucursal_id, sucursal=nombres_de_sucursales(self.db, self.ctx.empresa_id).get(sucursal_id, ""), total_vendido=total, ventas_netas=total - dev["devuelto"] + dev["nuevo"],
            ventas=ventas, unidades=sum(u for _, u, _ in canales.values()), ticket_promedio=(total / ventas).quantize(CERO) if ventas else CERO,
            presencial=canal("PRESENCIAL"), digital=canal("DIGITAL"), cierre_de_caja=cierre,
            devoluciones=schemas.DevolucionesDia(
                notas=dev["notas"], devuelto=dev["devuelto"], entregado_en_cambios=dev["nuevo"], reembolsado_efectivo=reemb.get("EFECTIVO", CERO),
                reembolsado_tarjeta=reemb.get("TARJETA", CERO), cobrado_efectivo=cobros.get("EFECTIVO", CERO), cobrado_tarjeta=cobros.get("TARJETA", CERO),
            ),
            efectivo_en_caja=efectivo,
            reservas_completadas=self.ventas.reservas_completadas(sucursal_id, desde, hasta),
        )

    def listar(self, desde: date | None, hasta: date | None, canal: str | None, metodo: str | None, sucursal: int | None) -> schemas.VentasOut:
        sucursal_id = self._sucursal(sucursal)
        hoy = a_local(ahora()).date()
        desde, hasta = desde or hoy, hasta or desde or hoy
        inicio, fin = _rango(desde, hasta)
        filas = self.ventas.tickets(sucursal_id, inicio, fin, canal, metodo)
        personas = nombres_de_usuarios(self.db, self.ctx.empresa_id, {u for p, _ in filas for u in (p.cliente_id, p.creado_por) if u})
        tickets = [
            schemas.TicketOut(
                id=p.id, codigo=p.codigo, comprobante_numero=p.comprobante_numero, comprobante_tipo=p.comprobante_tipo, fecha=p.pagado_en, canal=p.canal,
                cliente=personas.get(p.cliente_id), vendedor=personas.get(p.creado_por) if p.canal == "PRESENCIAL" else None, metodo=m,
                unidades=sum(i.cantidad for i in p.items), total=p.total,
            )
            for p, m in filas
        ]
        return schemas.VentasOut(desde=desde, hasta=hasta, total=sum((t.total for t in tickets), CERO), tickets=tickets)

    def detalle(self, pedido_id: int) -> PedidoOut:
        """Paso 3: el detalle de un ticket de la sucursal."""
        pedido = self.ventas.pedido_pagado(pedido_id)
        if pedido is None:
            raise NoEncontrado("Venta no encontrada.")  # también si es de otra empresa
        self._sucursal(pedido.sucursal_id)  # el ticket de otra sucursal de la misma empresa: acceso denegado
        return CompraService(self.db, self.ctx).salida([pedido])[0]

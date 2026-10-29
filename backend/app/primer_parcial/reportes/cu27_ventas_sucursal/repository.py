from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.core.tenant import TenantRepository
from app.modules.reservas.publico import Reserva
from app.modules.ventas.publico import Devolucion
from app.primer_parcial.ventas.publico import Pago, Pedido, PedidoItem


class VentasSucursalRepository(TenantRepository[Pedido]):
    """Lectura de las ventas de UNA sucursal de la empresa (el servicio fija la sucursal con la del Encargado)."""

    model = Pedido

    def _pagadas(self, sucursal_id: int, desde: datetime, hasta: datetime):
        return self._consulta().where(Pedido.sucursal_id == sucursal_id, Pedido.estado == "PAGADO", Pedido.pagado_en >= desde, Pedido.pagado_en < hasta)

    def totales_por_canal(self, sucursal_id: int, desde: datetime, hasta: datetime) -> dict[str, tuple[int, int, Decimal]]:
        """{canal: (ventas, unidades, total)} de las ventas pagadas del periodo."""
        unidades = (
            select(PedidoItem.pedido_id, func.sum(PedidoItem.cantidad).label("u")).where(PedidoItem.empresa_id == self.empresa_id).group_by(PedidoItem.pedido_id).subquery()
        )
        stmt = (
            select(Pedido.canal, func.count(Pedido.id), func.coalesce(func.sum(unidades.c.u), 0), func.coalesce(func.sum(Pedido.total), 0))
            .join(unidades, unidades.c.pedido_id == Pedido.id, isouter=True)
            .where(Pedido.empresa_id == self.empresa_id, Pedido.sucursal_id == sucursal_id, Pedido.estado == "PAGADO", Pedido.pagado_en >= desde, Pedido.pagado_en < hasta)
            .group_by(Pedido.canal)
        )
        return {canal: (int(n), int(u), Decimal(t)) for canal, n, u, t in self.db.execute(stmt)}

    def cierre_por_metodo(self, sucursal_id: int, desde: datetime, hasta: datetime) -> list[tuple]:
        """Cobros aprobados de las ventas del periodo, por método: (método, cobros, total, recibido, cambio)."""
        stmt = (
            select(Pago.metodo, func.count(Pago.id), func.sum(Pago.monto), func.sum(Pago.monto_recibido), func.sum(Pago.cambio))
            .join(Pedido, Pedido.id == Pago.pedido_id)
            .where(Pago.empresa_id == self.empresa_id, Pago.estado == "APROBADO", Pedido.sucursal_id == sucursal_id, Pedido.estado == "PAGADO",
                   Pedido.pagado_en >= desde, Pedido.pagado_en < hasta)
            .group_by(Pago.metodo).order_by(Pago.metodo)
        )
        return list(self.db.execute(stmt))

    def devoluciones(self, sucursal_id: int, desde: datetime, hasta: datetime) -> dict:
        """Devoluciones y cambios del periodo: cuántas notas, valores y dinero movido por medio (reembolsos y diferencias cobradas)."""
        filtro = (Devolucion.empresa_id == self.empresa_id, Devolucion.sucursal_id == sucursal_id, Devolucion.creada_en >= desde, Devolucion.creada_en < hasta)
        notas, devuelto, nuevo = self.db.execute(
            select(func.count(Devolucion.id), func.coalesce(func.sum(Devolucion.monto_devuelto), 0), func.coalesce(func.sum(Devolucion.monto_nuevo), 0)).where(*filtro)
        ).one()
        reembolsos = {m: Decimal(t) for m, t in self.db.execute(select(Devolucion.medio_reembolso, func.sum(Devolucion.reembolso)).where(*filtro, Devolucion.reembolso > 0).group_by(Devolucion.medio_reembolso))}
        cobros = {m: Decimal(t) for m, t in self.db.execute(select(Devolucion.medio_cobro, func.sum(Devolucion.cobro_adicional)).where(*filtro, Devolucion.cobro_adicional > 0).group_by(Devolucion.medio_cobro))}
        return {"notas": int(notas), "devuelto": Decimal(devuelto), "nuevo": Decimal(nuevo), "reembolsos": reembolsos, "cobros": cobros}

    def reservas_completadas(self, sucursal_id: int, desde: datetime, hasta: datetime) -> int:
        stmt = select(func.count(Reserva.id)).where(
            Reserva.empresa_id == self.empresa_id, Reserva.sucursal_id == sucursal_id, Reserva.estado == "COMPLETADA",
            Reserva.actualizada_en >= desde, Reserva.actualizada_en < hasta,
        )
        return self.db.scalar(stmt) or 0

    def tickets(self, sucursal_id: int, desde: datetime, hasta: datetime, canal: str | None, metodo: str | None, limite: int = 500) -> list[tuple[Pedido, str | None]]:
        """Ventas pagadas del periodo con el método de pago con que se cobraron."""
        stmt = (
            select(Pedido, Pago.metodo).join(Pago, (Pago.pedido_id == Pedido.id) & (Pago.estado == "APROBADO"), isouter=True)
            .where(Pedido.empresa_id == self.empresa_id, Pedido.sucursal_id == sucursal_id, Pedido.estado == "PAGADO", Pedido.pagado_en >= desde, Pedido.pagado_en < hasta)
            .options(selectinload(Pedido.items)).order_by(Pedido.pagado_en.desc(), Pedido.id.desc()).limit(limite)
        )
        if canal:
            stmt = stmt.where(Pedido.canal == canal)
        if metodo:
            stmt = stmt.where(Pago.metodo == metodo)
        return [(p, m) for p, m in self.db.execute(stmt)]

    def pedido_pagado(self, pedido_id: int) -> Pedido | None:
        stmt = self._consulta().where(Pedido.id == pedido_id, Pedido.estado == "PAGADO").options(selectinload(Pedido.items))
        return self.db.scalar(stmt)

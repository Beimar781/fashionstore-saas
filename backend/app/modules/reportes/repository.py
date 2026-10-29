"""Consultas de lectura de los reportes (CU-21, CU-22) y del reporte generativo (CU-23). Todas filtran por empresa y, si se pide, por sucursal.
Las ventas son los pedidos PAGADOS (digitales y presenciales); las devoluciones y cambios (CU-41) las convierten en ventas netas."""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select

from app.core.tenant import TenantRepository
from app.modules.inventario.publico import Existencia
from app.modules.reservas.publico import Reserva
from app.modules.ventas.publico import Devolucion, DevolucionItem
from app.primer_parcial.catalogo.publico import Producto, Variante
from app.primer_parcial.ventas.publico import Pago, Pedido, PedidoItem

CERO = Decimal("0.00")


class ReportesRepository(TenantRepository[Pedido]):
    model = Pedido

    def _ventas(self, desde: datetime, hasta: datetime, sucursal_id: int | None, canal: str | None = None):
        condiciones = [Pedido.empresa_id == self.empresa_id, Pedido.estado == "PAGADO", Pedido.pagado_en >= desde, Pedido.pagado_en < hasta]
        if sucursal_id is not None:
            condiciones.append(Pedido.sucursal_id == sucursal_id)
        if canal:
            condiciones.append(Pedido.canal == canal)
        return condiciones

    # ---- ventas ----
    def por_canal(self, desde, hasta, sucursal_id, canal=None) -> dict[str, tuple[int, int, Decimal]]:
        """{canal: (ventas, unidades, total)}"""
        unidades = select(PedidoItem.pedido_id, func.sum(PedidoItem.cantidad).label("u")).where(PedidoItem.empresa_id == self.empresa_id).group_by(PedidoItem.pedido_id).subquery()
        stmt = (
            select(Pedido.canal, func.count(Pedido.id), func.coalesce(func.sum(unidades.c.u), 0), func.coalesce(func.sum(Pedido.total), 0))
            .join(unidades, unidades.c.pedido_id == Pedido.id, isouter=True)
            .where(*self._ventas(desde, hasta, sucursal_id, canal)).group_by(Pedido.canal)
        )
        return {c: (int(n), int(u), Decimal(t)) for c, n, u, t in self.db.execute(stmt)}

    def por_sucursal(self, desde, hasta, sucursal_id, canal=None) -> list[tuple[int, int, Decimal]]:
        stmt = (
            select(Pedido.sucursal_id, func.count(Pedido.id), func.coalesce(func.sum(Pedido.total), 0))
            .where(*self._ventas(desde, hasta, sucursal_id, canal)).group_by(Pedido.sucursal_id).order_by(func.sum(Pedido.total).desc())
        )
        return [(s, int(n), Decimal(t)) for s, n, t in self.db.execute(stmt)]

    def ventas_con_fecha(self, desde, hasta, sucursal_id, canal=None) -> list[tuple[datetime, Decimal]]:
        stmt = select(Pedido.pagado_en, Pedido.total).where(*self._ventas(desde, hasta, sucursal_id, canal))
        return [(f, Decimal(t)) for f, t in self.db.execute(stmt)]

    def tickets(self, desde, hasta, sucursal_id, canal=None, limite: int = 2000) -> list[Pedido]:
        stmt = select(Pedido).where(*self._ventas(desde, hasta, sucursal_id, canal)).order_by(Pedido.pagado_en.desc(), Pedido.id.desc()).limit(limite)
        return list(self.db.scalars(stmt))

    def por_metodo_de_pago(self, desde, hasta, sucursal_id, canal=None) -> list[tuple[str, int, Decimal]]:
        stmt = (
            select(Pago.metodo, func.count(Pago.id), func.sum(Pago.monto)).join(Pedido, Pedido.id == Pago.pedido_id)
            .where(Pago.empresa_id == self.empresa_id, Pago.estado == "APROBADO", *self._ventas(desde, hasta, sucursal_id, canal)).group_by(Pago.metodo).order_by(Pago.metodo)
        )
        return [(m, int(n), Decimal(t)) for m, n, t in self.db.execute(stmt)]

    def devoluciones(self, desde, hasta, sucursal_id, canal=None) -> tuple[int, Decimal, Decimal]:
        """(notas, valor devuelto, valor entregado en cambios) del periodo."""
        condiciones = [Devolucion.empresa_id == self.empresa_id, Devolucion.creada_en >= desde, Devolucion.creada_en < hasta]
        if sucursal_id is not None:
            condiciones.append(Devolucion.sucursal_id == sucursal_id)
        stmt = select(func.count(Devolucion.id), func.coalesce(func.sum(Devolucion.monto_devuelto), 0), func.coalesce(func.sum(Devolucion.monto_nuevo), 0)).where(*condiciones)
        if canal:  # el canal es el de la venta original
            stmt = stmt.join(Pedido, Pedido.id == Devolucion.pedido_id).where(Pedido.canal == canal)
        n, devuelto, nuevo = self.db.execute(stmt).one()
        return int(n), Decimal(devuelto), Decimal(nuevo)

    def productos_netos(self, desde, hasta, sucursal_id, canal=None) -> list[tuple[str, int, Decimal]]:
        """(producto, unidades netas, ingresos netos): lo vendido, menos lo devuelto, más lo entregado en cambios."""
        brutos = self.db.execute(
            select(PedidoItem.producto, func.sum(PedidoItem.cantidad), func.sum(PedidoItem.subtotal)).join(Pedido, Pedido.id == PedidoItem.pedido_id)
            .where(PedidoItem.empresa_id == self.empresa_id, *self._ventas(desde, hasta, sucursal_id, canal)).group_by(PedidoItem.producto)
        )
        netos = {p: [int(u), Decimal(i)] for p, u, i in brutos}
        condiciones = [DevolucionItem.empresa_id == self.empresa_id, Devolucion.creada_en >= desde, Devolucion.creada_en < hasta]
        if sucursal_id is not None:
            condiciones.append(Devolucion.sucursal_id == sucursal_id)
        stmt = (
            select(DevolucionItem.producto, DevolucionItem.sentido, func.sum(DevolucionItem.cantidad), func.sum(DevolucionItem.subtotal))
            .join(Devolucion, Devolucion.id == DevolucionItem.devolucion_id).where(*condiciones).group_by(DevolucionItem.producto, DevolucionItem.sentido)
        )
        if canal:
            stmt = stmt.join(Pedido, Pedido.id == Devolucion.pedido_id).where(Pedido.canal == canal)
        movimientos = self.db.execute(stmt)
        for producto, sentido, unidades, importe in movimientos:
            fila = netos.setdefault(producto, [0, CERO])
            signo = -1 if sentido == "DEVUELTA" else 1
            fila[0] += signo * int(unidades)
            fila[1] += signo * Decimal(importe)
        return [(p, u, i) for p, (u, i) in netos.items()]

    # ---- pagos (tabla pagos) ----
    def pagos_por_estado(self, desde, hasta, sucursal_id) -> list[tuple[str, str, int, Decimal]]:
        stmt = (
            select(Pago.estado, Pago.metodo, func.count(Pago.id), func.coalesce(func.sum(Pago.monto), 0)).join(Pedido, Pedido.id == Pago.pedido_id)
            .where(*self._pagos(desde, hasta, sucursal_id)).group_by(Pago.estado, Pago.metodo)
        )
        return [(e, m, int(n), Decimal(t)) for e, m, n, t in self.db.execute(stmt)]

    def pagos_con_problemas(self, desde, hasta, sucursal_id, limite: int = 50) -> list[tuple[Pago, str, int]]:
        """Pagos rechazados o pendientes de confirmación, con el código del pedido y su sucursal."""
        stmt = (
            select(Pago, Pedido.codigo, Pedido.sucursal_id).join(Pedido, Pedido.id == Pago.pedido_id)
            .where(*self._pagos(desde, hasta, sucursal_id), Pago.estado.in_(("RECHAZADO", "PENDIENTE_CONFIRMACION"))).order_by(Pago.creado_en.desc(), Pago.id.desc()).limit(limite)
        )
        return [(p, c, s) for p, c, s in self.db.execute(stmt)]

    def _pagos(self, desde, hasta, sucursal_id):
        condiciones = [Pago.empresa_id == self.empresa_id, Pago.creado_en >= desde, Pago.creado_en < hasta]
        if sucursal_id is not None:
            condiciones.append(Pedido.sucursal_id == sucursal_id)
        return condiciones

    # ---- reservas ----
    def reservas_por_estado(self, desde, hasta, sucursal_id) -> dict[str, int]:
        stmt = select(Reserva.estado, func.count(Reserva.id)).where(*self._reservas(desde, hasta, sucursal_id)).group_by(Reserva.estado)
        return {e: int(n) for e, n in self.db.execute(stmt)}

    def reservas_por_sucursal(self, desde, hasta, sucursal_id) -> list[tuple[int, int, int]]:
        """(sucursal, reservas, completadas)"""
        stmt = select(Reserva.sucursal_id, func.count(Reserva.id), func.count().filter(Reserva.estado == "COMPLETADA")).where(*self._reservas(desde, hasta, sucursal_id)).group_by(Reserva.sucursal_id)
        return [(s, int(n), int(c)) for s, n, c in self.db.execute(stmt)]

    def reservas_con_fecha(self, desde, hasta, sucursal_id) -> list[tuple[datetime, str]]:
        return [(f, e) for f, e in self.db.execute(select(Reserva.creada_en, Reserva.estado).where(*self._reservas(desde, hasta, sucursal_id)))]

    def reservas(self, desde, hasta, sucursal_id, limite: int = 2000) -> list[Reserva]:
        return list(self.db.scalars(select(Reserva).where(*self._reservas(desde, hasta, sucursal_id)).order_by(Reserva.creada_en.desc()).limit(limite)))

    def _reservas(self, desde, hasta, sucursal_id):
        condiciones = [Reserva.empresa_id == self.empresa_id, Reserva.creada_en >= desde, Reserva.creada_en < hasta]
        if sucursal_id is not None:
            condiciones.append(Reserva.sucursal_id == sucursal_id)
        return condiciones

    # ---- inventario y catálogo ----
    def inventario(self, sucursal_id: int | None) -> dict[str, int]:
        condiciones = [Existencia.empresa_id == self.empresa_id]
        if sucursal_id is not None:
            condiciones.append(Existencia.sucursal_id == sucursal_id)
        disp, res, ven, bajo, agotadas = self.db.execute(
            select(
                func.coalesce(func.sum(Existencia.disponible), 0), func.coalesce(func.sum(Existencia.reservada), 0), func.coalesce(func.sum(Existencia.vendida), 0),
                func.count().filter((Existencia.umbral_minimo > 0) & (Existencia.disponible <= Existencia.umbral_minimo)), func.count().filter(Existencia.disponible == 0),
            ).where(*condiciones)
        ).one()
        return {"disponibles": int(disp), "reservadas": int(res), "vendidas": int(ven), "stock_bajo": int(bajo), "agotadas": int(agotadas)}

    def stock_bajo(self, sucursal_id: int | None, limite: int = 10) -> list[tuple[int, str, str, int, int]]:
        """(sucursal, producto, sku, disponible, umbral) de lo que está en o bajo su mínimo."""
        condiciones = [Existencia.empresa_id == self.empresa_id, Existencia.umbral_minimo > 0, Existencia.disponible <= Existencia.umbral_minimo]
        if sucursal_id is not None:
            condiciones.append(Existencia.sucursal_id == sucursal_id)
        stmt = (
            select(Existencia.sucursal_id, Producto.nombre, Variante.sku, Existencia.disponible, Existencia.umbral_minimo)
            .join(Variante, Variante.id == Existencia.variante_id).join(Producto, Producto.id == Variante.producto_id)
            .where(*condiciones).order_by(Existencia.disponible, Producto.nombre).limit(limite)
        )
        return [(s, p, k, int(d), int(u)) for s, p, k, d, u in self.db.execute(stmt)]

    def productos_activos(self) -> int:
        return self.db.scalar(select(func.count(Producto.id)).where(Producto.empresa_id == self.empresa_id, Producto.activo.is_(True))) or 0

    # ---- para el análisis con ML (CU-42) ----
    def unidades_por_producto_y_fecha(self, desde, hasta, sucursal_id) -> list[tuple[str, datetime, int]]:
        """(producto, fecha de la venta, unidades) de las ventas pagadas del periodo."""
        stmt = (
            select(PedidoItem.producto, Pedido.pagado_en, PedidoItem.cantidad).join(Pedido, Pedido.id == PedidoItem.pedido_id)
            .where(PedidoItem.empresa_id == self.empresa_id, *self._ventas(desde, hasta, sucursal_id))
        )
        return [(p, f, int(c)) for p, f, c in self.db.execute(stmt)]

    def stock_por_producto(self, sucursal_id: int | None) -> dict[str, int]:
        condiciones = [Existencia.empresa_id == self.empresa_id]
        if sucursal_id is not None:
            condiciones.append(Existencia.sucursal_id == sucursal_id)
        stmt = (
            select(Producto.nombre, func.coalesce(func.sum(Existencia.disponible), 0)).join(Variante, Variante.id == Existencia.variante_id)
            .join(Producto, Producto.id == Variante.producto_id).where(*condiciones).group_by(Producto.nombre)
        )
        return {p: int(d) for p, d in self.db.execute(stmt)}

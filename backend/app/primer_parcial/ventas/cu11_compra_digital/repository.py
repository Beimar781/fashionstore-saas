from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import selectinload

from app.core.tenant import TenantRepository
from app.primer_parcial.ventas.models import Pago, Pedido, PedidoItem, SecuenciaComprobante


class PedidoRepository(TenantRepository[Pedido]):
    model = Pedido

    def obtener_completo(self, pedido_id: int) -> Pedido | None:
        return self.db.scalar(self._consulta().where(Pedido.id == pedido_id).options(selectinload(Pedido.items)))

    def existe_codigo(self, codigo: str) -> bool:
        return self.db.scalar(self._consulta().where(Pedido.codigo == codigo).limit(1)) is not None

    def pendientes_de_pago(self, cliente_id: int) -> list[Pedido]:
        return list(self.db.scalars(self._consulta().where(Pedido.cliente_id == cliente_id, Pedido.estado == "PENDIENTE_PAGO")))

    def abiertos_presenciales(self, sucursal_id: int) -> list[Pedido]:
        """Ventas de caja de la sucursal que todavía no se cobran."""
        stmt = (
            self._consulta().where(Pedido.canal == "PRESENCIAL", Pedido.sucursal_id == sucursal_id, Pedido.estado.in_(("PENDIENTE_PAGO", "PENDIENTE_CONFIRMACION")))
            .options(selectinload(Pedido.items)).order_by(Pedido.creado_en.desc(), Pedido.id.desc())
        )
        return list(self.db.scalars(stmt))

    def abierto_de_reserva(self, reserva_id: int) -> Pedido | None:
        stmt = self._consulta().where(Pedido.reserva_id == reserva_id, Pedido.estado.in_(("PENDIENTE_PAGO", "PENDIENTE_CONFIRMACION")))
        return self.db.scalar(stmt)

    def agregar_item(self, pedido: Pedido, **campos) -> PedidoItem:
        item = PedidoItem(empresa_id=self.empresa_id, **campos)
        pedido.items.append(item)
        return item

    def pagos_de(self, pedido_ids: list[int]) -> dict[int, list[Pago]]:
        porpedido: dict[int, list[Pago]] = {i: [] for i in pedido_ids}
        if pedido_ids:
            stmt = select(Pago).where(Pago.empresa_id == self.empresa_id, Pago.pedido_id.in_(pedido_ids)).order_by(Pago.creado_en, Pago.id)
            for pago in self.db.scalars(stmt):
                porpedido[pago.pedido_id].append(pago)
        return porpedido

    def siguiente_comprobante(self, sucursal_id: int) -> str:
        """Número de comprobante correlativo por sucursal. La fila se bloquea para que dos pagos simultáneos no repitan número."""
        self.db.execute(
            pg_insert(SecuenciaComprobante).values(empresa_id=self.empresa_id, sucursal_id=sucursal_id, ultimo=0)
            .on_conflict_do_nothing(index_elements=["empresa_id", "sucursal_id"])
        )
        fila = self.db.scalar(
            select(SecuenciaComprobante).where(SecuenciaComprobante.empresa_id == self.empresa_id, SecuenciaComprobante.sucursal_id == sucursal_id)
            .with_for_update().execution_options(populate_existing=True)
        )
        fila.ultimo += 1
        return f"CMP-{sucursal_id:03d}-{fila.ultimo:06d}"

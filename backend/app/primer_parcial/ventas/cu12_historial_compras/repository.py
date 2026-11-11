from sqlalchemy.orm import selectinload

from app.core.tenant import TenantRepository
from app.primer_parcial.ventas.models import Pedido

# Compras visibles al cliente: pagadas, con pago por confirmar o por pagar (dejadas así desde el móvil). Las canceladas no aparecen.
VISIBLES_AL_CLIENTE = ("PAGADO", "PENDIENTE_CONFIRMACION", "PENDIENTE_PAGO")


class HistorialRepository(TenantRepository[Pedido]):
    model = Pedido

    def del_cliente(self, cliente_id: int, estado: str | None) -> list[Pedido]:
        stmt = (
            self._consulta().where(Pedido.cliente_id == cliente_id, Pedido.estado.in_((estado,) if estado else VISIBLES_AL_CLIENTE))
            .options(selectinload(Pedido.items)).order_by(Pedido.creado_en.desc(), Pedido.id.desc())
        )
        return list(self.db.scalars(stmt))

    def pedido_del_cliente(self, pedido_id: int, cliente_id: int) -> Pedido | None:
        stmt = self._consulta().where(Pedido.id == pedido_id, Pedido.cliente_id == cliente_id).options(selectinload(Pedido.items))
        return self.db.scalar(stmt)

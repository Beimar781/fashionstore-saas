from app.core.tenant import TenantRepository
from app.primer_parcial.ventas.models import ClientePasarela, Pago, Pedido, TarjetaGuardada


class PagoRepository(TenantRepository[Pago]):
    model = Pago

    def del_cliente(self, pago_id: int, cliente_id: int) -> Pago | None:
        """El pago se busca por su pedido: solo el cliente dueño del pedido puede verlo o confirmarlo."""
        stmt = self._consulta().join(Pedido, Pedido.id == Pago.pedido_id).where(Pago.id == pago_id, Pedido.cliente_id == cliente_id)
        return self.db.scalar(stmt)

    def abiertos_de(self, pedido_id: int) -> list[Pago]:
        stmt = self._consulta().where(Pago.pedido_id == pedido_id, Pago.estado.in_(("PENDIENTE", "AUTORIZADO", "PENDIENTE_CONFIRMACION")))
        return list(self.db.scalars(stmt))


class TarjetaRepository(TenantRepository[TarjetaGuardada]):
    model = TarjetaGuardada

    def de_cliente(self, cliente_id: int, proveedor: str) -> list[TarjetaGuardada]:
        stmt = self._consulta().where(TarjetaGuardada.cliente_id == cliente_id, TarjetaGuardada.proveedor == proveedor).order_by(TarjetaGuardada.id.desc())
        return list(self.db.scalars(stmt))

    def del_cliente(self, tarjeta_id: int, cliente_id: int) -> TarjetaGuardada | None:
        return self.db.scalar(self._consulta().where(TarjetaGuardada.id == tarjeta_id, TarjetaGuardada.cliente_id == cliente_id))

    def por_referencia(self, referencia: str, cliente_id: int) -> TarjetaGuardada | None:
        return self.db.scalar(self._consulta().where(TarjetaGuardada.referencia == referencia, TarjetaGuardada.cliente_id == cliente_id))

    def existe(self, cliente_id: int, marca: str, ultimos4: str, exp_mes: int, exp_anio: int) -> bool:
        stmt = self._consulta().where(
            TarjetaGuardada.cliente_id == cliente_id, TarjetaGuardada.marca == marca, TarjetaGuardada.ultimos4 == ultimos4,
            TarjetaGuardada.exp_mes == exp_mes, TarjetaGuardada.exp_anio == exp_anio,
        ).limit(1)
        return self.db.scalar(stmt) is not None


class ClientePasarelaRepository(TenantRepository[ClientePasarela]):
    model = ClientePasarela

    def de_cliente(self, cliente_id: int) -> ClientePasarela | None:
        return self.db.scalar(self._consulta().where(ClientePasarela.cliente_id == cliente_id))

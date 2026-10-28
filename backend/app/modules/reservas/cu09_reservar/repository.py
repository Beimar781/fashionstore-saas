from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.tenant import TenantRepository
from app.modules.reservas.models import Reserva, ReservaItem
from app.primer_parcial.catalogo.publico import Producto, Variante

ACTIVAS = ("PENDIENTE", "PREPARADA", "EN_PROBADOR")


class ReservaRepository(TenantRepository[Reserva]):
    model = Reserva

    def obtener_completa(self, reserva_id: int) -> Reserva | None:
        return self.db.scalar(self._consulta().where(Reserva.id == reserva_id).options(selectinload(Reserva.items)))

    def por_codigo(self, codigo: str) -> Reserva | None:
        return self.db.scalar(self._consulta().where(Reserva.codigo == codigo.strip().upper()).options(selectinload(Reserva.items)))

    def existe_codigo(self, codigo: str) -> bool:
        return self.db.scalar(self._consulta().where(Reserva.codigo == codigo).limit(1)) is not None

    def buscar(
        self, cliente_id: int | None = None, sucursal_id: int | None = None, estados: tuple[str, ...] | None = None,
        desde: datetime | None = None, hasta: datetime | None = None, limite: int = 200,
    ) -> list[Reserva]:
        stmt = self._consulta().options(selectinload(Reserva.items)).limit(limite)
        if cliente_id is not None:
            stmt = stmt.where(Reserva.cliente_id == cliente_id)
        if sucursal_id is not None:
            stmt = stmt.where(Reserva.sucursal_id == sucursal_id)
        if estados:
            stmt = stmt.where(Reserva.estado.in_(estados))
        if desde is not None:
            stmt = stmt.where(Reserva.programada_para >= desde)
        if hasta is not None:
            stmt = stmt.where(Reserva.programada_para < hasta)
        orden = Reserva.programada_para.asc() if sucursal_id is not None else Reserva.creada_en.desc()
        return list(self.db.scalars(stmt.order_by(orden, Reserva.id.desc())))

    def hay_activas_en(self, sucursal_id: int) -> bool:
        stmt = self._consulta().where(Reserva.sucursal_id == sucursal_id, Reserva.estado.in_(ACTIVAS)).limit(1)
        return self.db.scalar(stmt) is not None

    def vencidas(self, ahora: datetime) -> list[Reserva]:
        """Reservas que siguen apartando stock y cuya vigencia ya pasó."""
        stmt = self._consulta().where(Reserva.estado.in_(("PENDIENTE", "PREPARADA")), Reserva.vence_en <= ahora).options(selectinload(Reserva.items))
        return list(self.db.scalars(stmt))

    def agregar_item(self, reserva: Reserva, variante_id: int, cantidad: int) -> ReservaItem:
        item = ReservaItem(empresa_id=self.empresa_id, variante_id=variante_id, cantidad=cantidad)
        reserva.items.append(item)
        return item


class VarianteReservaRepository(TenantRepository[Variante]):
    """Variantes del catálogo, solo lectura."""

    model = Variante

    def habilitadas(self, ids: set[int]) -> dict[int, Variante]:
        """Variantes activas de productos activos (lo único que se puede reservar)."""
        stmt = (
            self._consulta().join(Producto, Producto.id == Variante.producto_id)
            .where(Variante.id.in_(ids), Variante.activa.is_(True), Producto.activo.is_(True)).options(selectinload(Variante.producto))
        )
        return {v.id: v for v in self.db.scalars(stmt)}

    def con_producto(self, ids: set[int]) -> dict[int, Variante]:
        if not ids:
            return {}
        stmt = self._consulta().where(Variante.id.in_(ids)).options(selectinload(Variante.producto))
        return {v.id: v for v in self.db.scalars(stmt)}

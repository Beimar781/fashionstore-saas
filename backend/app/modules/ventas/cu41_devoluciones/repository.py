from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import selectinload

from app.core.tenant import TenantRepository
from app.modules.ventas.models import ConfiguracionVentas, Devolucion, DevolucionItem, IntentoDiferencia, SecuenciaNotaDevolucion

PLAZO_POR_DEFECTO = 15


class DevolucionRepository(TenantRepository[Devolucion]):
    model = Devolucion

    def obtener_completa(self, devolucion_id: int) -> Devolucion | None:
        return self.db.scalar(self._consulta().where(Devolucion.id == devolucion_id).options(selectinload(Devolucion.items)))

    def de_pedido(self, pedido_id: int) -> list[Devolucion]:
        stmt = self._consulta().where(Devolucion.pedido_id == pedido_id).options(selectinload(Devolucion.items)).order_by(Devolucion.creada_en, Devolucion.id)
        return list(self.db.scalars(stmt))

    def buscar(self, sucursal_id: int | None, desde: datetime | None, hasta: datetime | None, limite: int = 200) -> list[Devolucion]:
        stmt = self._consulta().options(selectinload(Devolucion.items)).order_by(Devolucion.creada_en.desc(), Devolucion.id.desc()).limit(limite)
        if sucursal_id is not None:
            stmt = stmt.where(Devolucion.sucursal_id == sucursal_id)
        if desde is not None:
            stmt = stmt.where(Devolucion.creada_en >= desde)
        if hasta is not None:
            stmt = stmt.where(Devolucion.creada_en < hasta)
        return list(self.db.scalars(stmt))

    def devuelto_por_item(self, pedido_id: int) -> dict[int, int]:
        """Unidades ya devueltas de cada prenda de la venta: así no se devuelve más de lo vendido ni dos veces lo mismo."""
        stmt = (
            select(DevolucionItem.pedido_item_id, func.sum(DevolucionItem.cantidad))
            .join(Devolucion, Devolucion.id == DevolucionItem.devolucion_id)
            .where(Devolucion.empresa_id == self.empresa_id, Devolucion.pedido_id == pedido_id, DevolucionItem.sentido == "DEVUELTA")
            .group_by(DevolucionItem.pedido_item_id)
        )
        return {item_id: int(c) for item_id, c in self.db.execute(stmt)}

    def reembolsado_con_tarjeta(self, pedido_id: int) -> tuple[Decimal, int]:
        """(bolivianos, centavos de la pasarela) ya reembolsados a la tarjeta de esa venta."""
        stmt = select(func.coalesce(func.sum(Devolucion.reembolso), 0), func.coalesce(func.sum(Devolucion.reembolso_pasarela), 0)).where(
            Devolucion.empresa_id == self.empresa_id, Devolucion.pedido_id == pedido_id, Devolucion.medio_reembolso == "TARJETA"
        )
        bob, centavos = self.db.execute(stmt).one()
        return Decimal(bob), int(centavos)

    def siguiente_numero(self, sucursal_id: int) -> str:
        """Número de nota correlativo por sucursal; la fila se bloquea para que dos devoluciones simultáneas no repitan número."""
        self.db.execute(
            pg_insert(SecuenciaNotaDevolucion).values(empresa_id=self.empresa_id, sucursal_id=sucursal_id, ultimo=0)
            .on_conflict_do_nothing(index_elements=["empresa_id", "sucursal_id"])
        )
        fila = self.db.scalar(
            select(SecuenciaNotaDevolucion).where(SecuenciaNotaDevolucion.empresa_id == self.empresa_id, SecuenciaNotaDevolucion.sucursal_id == sucursal_id)
            .with_for_update().execution_options(populate_existing=True)
        )
        fila.ultimo += 1
        return f"NDV-{sucursal_id:03d}-{fila.ultimo:06d}"


class IntentoRepository(TenantRepository[IntentoDiferencia]):
    model = IntentoDiferencia

    def bloquear(self, intento_id: int) -> IntentoDiferencia | None:
        return self.db.scalar(self._consulta().where(IntentoDiferencia.id == intento_id).with_for_update().execution_options(populate_existing=True))

    def abiertos(self, pedido_id: int, usuario_id: int) -> list[IntentoDiferencia]:
        return list(self.db.scalars(self._consulta().where(
            IntentoDiferencia.pedido_id == pedido_id, IntentoDiferencia.usuario_id == usuario_id, IntentoDiferencia.estado == "PENDIENTE"
        )))


class ConfiguracionRepository:
    """Configuración de ventas de UNA empresa (la fila se crea la primera vez que se guarda)."""

    def __init__(self, db, empresa_id: int):
        self.db = db
        self.empresa_id = empresa_id

    def plazo_dias(self) -> int:
        fila = self.db.get(ConfiguracionVentas, self.empresa_id)
        return fila.plazo_devolucion_dias if fila else PLAZO_POR_DEFECTO

    def fijar_plazo(self, dias: int) -> None:
        fila = self.db.get(ConfiguracionVentas, self.empresa_id)
        if fila is None:
            self.db.add(ConfiguracionVentas(empresa_id=self.empresa_id, plazo_devolucion_dias=dias))
        else:
            fila.plazo_devolucion_dias = dias

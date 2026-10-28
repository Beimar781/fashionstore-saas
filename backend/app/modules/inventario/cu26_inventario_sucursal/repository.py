from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.tenant import TenantRepository
from app.modules.inventario.models import Existencia, MovimientoInventario
from app.primer_parcial.catalogo.publico import Color, Producto, Talla, Variante


class ExistenciaRepository(TenantRepository[Existencia]):
    model = Existencia

    def bloquear(self, sucursal_id: int, variante_ids: list[int]) -> dict[int, Existencia]:
        """Crea las filas que falten y las bloquea (en orden de id, para evitar bloqueos cruzados) hasta terminar la operación."""
        for variante_id in variante_ids:
            self.db.execute(
                pg_insert(Existencia).values(empresa_id=self.empresa_id, sucursal_id=sucursal_id, variante_id=variante_id)
                .on_conflict_do_nothing(index_elements=["sucursal_id", "variante_id"])
            )
        stmt = (
            self._consulta().where(Existencia.sucursal_id == sucursal_id, Existencia.variante_id.in_(variante_ids))
            .order_by(Existencia.variante_id).with_for_update().execution_options(populate_existing=True)
        )
        return {e.variante_id: e for e in self.db.scalars(stmt)}


class VarianteLectura(TenantRepository[Variante]):
    model = Variante


class MovimientoRepository(TenantRepository[MovimientoInventario]):
    model = MovimientoInventario

    def registrar(self, **campos) -> MovimientoInventario:
        return self.agregar(MovimientoInventario(**campos))

    def buscar(
        self, sucursal_id: int | None, variante_id: int | None, tipo: str | None, desde: date | None, hasta: date | None,
        pagina: int, tamano: int,
    ) -> tuple[int, list]:
        filtros = [MovimientoInventario.empresa_id == self.empresa_id]
        if sucursal_id is not None:
            filtros.append(MovimientoInventario.sucursal_id == sucursal_id)
        if variante_id is not None:
            filtros.append(MovimientoInventario.variante_id == variante_id)
        if tipo:
            filtros.append(MovimientoInventario.tipo == tipo)
        if desde:
            filtros.append(MovimientoInventario.creado_en >= datetime.combine(desde, time.min, tzinfo=timezone.utc))
        if hasta:
            filtros.append(MovimientoInventario.creado_en < datetime.combine(hasta + timedelta(days=1), time.min, tzinfo=timezone.utc))
        total = self.db.scalar(select(func.count()).select_from(MovimientoInventario).where(*filtros)) or 0
        stmt = (
            select(MovimientoInventario, Variante.sku, Producto.nombre, Talla.codigo, Color.nombre)
            .join(Variante, Variante.id == MovimientoInventario.variante_id)
            .join(Producto, Producto.id == Variante.producto_id)
            .join(Talla, Talla.id == Variante.talla_id)
            .join(Color, Color.id == Variante.color_id)
            .where(*filtros)
            .order_by(MovimientoInventario.creado_en.desc(), MovimientoInventario.id.desc())
            .limit(tamano).offset((pagina - 1) * tamano)
        )
        return total, list(self.db.execute(stmt))

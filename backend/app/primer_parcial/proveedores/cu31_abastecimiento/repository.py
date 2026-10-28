from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.core.tenant import TenantRepository
from app.primer_parcial.catalogo.publico import Coleccion, Producto, Variante
from app.primer_parcial.proveedores.models import Lote, LoteItem, Propuesta


class LoteRepository(TenantRepository[Lote]):
    model = Lote

    def obtener_completo(self, lote_id: int) -> Lote | None:
        return self.db.scalar(self._consulta().where(Lote.id == lote_id).options(selectinload(Lote.items)))

    def listar(self, estado: str | None, proveedor_id: int | None, sucursal_id: int | None, limite: int = 200) -> list[Lote]:
        stmt = self._consulta().options(selectinload(Lote.items)).order_by(Lote.creado_en.desc(), Lote.id.desc()).limit(limite)
        if estado:
            stmt = stmt.where(Lote.estado == estado)
        if proveedor_id is not None:
            stmt = stmt.where(Lote.proveedor_id == proveedor_id)
        if sucursal_id is not None:
            stmt = stmt.where(Lote.sucursal_id == sucursal_id)
        return list(self.db.scalars(stmt))

    def contar_en_transito(self) -> int:
        return self.db.scalar(select(func.count()).select_from(Lote).where(Lote.empresa_id == self.empresa_id, Lote.estado == "EN_TRANSITO")) or 0

    def en_transito_por_variante(self, sucursal_id: int | None) -> dict[int, int]:
        """Unidades que vienen en camino por variante (próximas a ingresar), en una consulta agrupada."""
        stmt = (
            select(LoteItem.variante_id, func.sum(LoteItem.cantidad))
            .join(Lote, Lote.id == LoteItem.lote_id)
            .where(Lote.empresa_id == self.empresa_id, Lote.estado == "EN_TRANSITO")
            .group_by(LoteItem.variante_id)
        )
        if sucursal_id is not None:
            stmt = stmt.where(Lote.sucursal_id == sucursal_id)
        return {variante_id: int(cantidad) for variante_id, cantidad in self.db.execute(stmt)}

    def agregar_item(self, lote: Lote, variante_id: int, cantidad: int, costo) -> LoteItem:
        item = LoteItem(empresa_id=self.empresa_id, variante_id=variante_id, cantidad=cantidad, costo_unitario=costo)
        lote.items.append(item)
        return item


class VarianteRepository(TenantRepository[Variante]):
    """Variantes del catálogo, solo lectura: lo que un aviso de remisión puede referenciar."""

    model = Variante

    def habilitadas_por_sku(self, skus: list[str]) -> dict[str, Variante]:
        stmt = (
            self._consulta().join(Producto, Producto.id == Variante.producto_id)
            .where(func.upper(Variante.sku).in_(skus), Variante.activa.is_(True), Producto.activo.is_(True))
        )
        return {v.sku.upper(): v for v in self.db.scalars(stmt)}

    def buscar_habilitadas(self, q: str | None, limite: int = 40) -> list[Variante]:
        stmt = (
            self._consulta().join(Producto, Producto.id == Variante.producto_id)
            .where(Variante.activa.is_(True), Producto.activo.is_(True)).options(selectinload(Variante.producto))
            .order_by(Producto.nombre, Variante.sku).limit(limite)
        )
        if q and q.strip():
            patron = f"%{q.strip().lower()}%"
            stmt = stmt.where(func.lower(Producto.nombre).like(patron) | func.lower(Variante.sku).like(patron))
        return list(self.db.scalars(stmt))

    def con_producto(self, ids: set[int]) -> dict[int, Variante]:
        if not ids:
            return {}
        stmt = self._consulta().where(Variante.id.in_(ids)).options(selectinload(Variante.producto))
        return {v.id: v for v in self.db.scalars(stmt)}


class ColeccionLectura(TenantRepository[Coleccion]):
    model = Coleccion


class PropuestaRepository(TenantRepository[Propuesta]):
    model = Propuesta

    def listar(self, estado: str | None, proveedor_id: int | None) -> list[Propuesta]:
        stmt = self._consulta().order_by(Propuesta.creado_en.desc(), Propuesta.id.desc())
        if estado:
            stmt = stmt.where(Propuesta.estado == estado)
        if proveedor_id is not None:
            stmt = stmt.where(Propuesta.proveedor_id == proveedor_id)
        return list(self.db.scalars(stmt))

    def contar_pendientes(self) -> int:
        return self.db.scalar(select(func.count()).select_from(Propuesta).where(Propuesta.empresa_id == self.empresa_id, Propuesta.estado == "PENDIENTE")) or 0

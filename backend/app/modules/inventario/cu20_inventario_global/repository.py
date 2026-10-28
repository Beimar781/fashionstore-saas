from sqlalchemy import and_, false, func, or_, select

from app.core.tenant import TenantRepository
from app.modules.inventario.cu20_inventario_global.schemas import FiltrosInventario
from app.modules.inventario.models import Existencia
from app.primer_parcial.catalogo.publico import Categoria, Coleccion, Color, Producto, Talla, Variante


class ConsultaInventarioRepository(TenantRepository[Variante]):
    """Inventario consolidado por variante: se suman las sucursales (o se toma solo la pedida)."""

    model = Variante

    def buscar(self, f: FiltrosInventario, en_transito: dict[int, int]):
        eid = self.empresa_id
        ex = select(
            Existencia.variante_id.label("variante_id"),
            func.sum(Existencia.disponible).label("disponible"),
            func.sum(Existencia.reservada).label("reservada"),
            func.sum(Existencia.vendida).label("vendida"),
            func.max(Existencia.umbral_minimo).label("umbral"),
        ).where(Existencia.empresa_id == eid).group_by(Existencia.variante_id)
        if f.sucursal is not None:
            ex = ex.where(Existencia.sucursal_id == f.sucursal)
        ex = ex.subquery()

        disponible = func.coalesce(ex.c.disponible, 0)
        reservada = func.coalesce(ex.c.reservada, 0)
        vendida = func.coalesce(ex.c.vendida, 0)
        umbral = func.coalesce(ex.c.umbral, 0)

        base = (
            select(
                Variante.id.label("variante_id"), Variante.sku.label("sku"), Producto.id.label("producto_id"), Producto.nombre.label("producto"),
                Categoria.nombre.label("categoria"), Talla.codigo.label("talla"), Talla.orden.label("talla_orden"), Color.nombre.label("color"),
                disponible.label("disponible"), reservada.label("reservada"), vendida.label("vendida"), umbral.label("umbral"),
            )
            .select_from(Variante)
            .join(Producto, Producto.id == Variante.producto_id)
            .join(Categoria, Categoria.id == Producto.categoria_id)
            .join(Talla, Talla.id == Variante.talla_id)
            .join(Color, Color.id == Variante.color_id)
            .outerjoin(ex, ex.c.variante_id == Variante.id)
            .where(Variante.empresa_id == eid, Variante.activa.is_(True))
        )
        if f.q:
            patron = f"%{f.q.strip().lower()}%"
            base = base.where(or_(func.lower(Producto.nombre).like(patron), func.lower(Variante.sku).like(patron)))
        if f.categoria_id is not None:
            hijas = select(Categoria.id).where(Categoria.empresa_id == eid, or_(Categoria.id == f.categoria_id, Categoria.padre_id == f.categoria_id))
            base = base.where(Producto.categoria_id.in_(hijas))
        if f.temporada_id is not None:
            base = base.where(Producto.coleccion_id.in_(select(Coleccion.id).where(Coleccion.empresa_id == eid, Coleccion.temporada_id == f.temporada_id)))
        condiciones_estado = {
            "DISPONIBLE": disponible > 0, "AGOTADA": disponible == 0, "RESERVADA": reservada > 0, "VENDIDA": vendida > 0,
            "PROXIMA": Variante.id.in_(list(en_transito)) if en_transito else false(),
        }
        if f.estado:
            base = base.where(condiciones_estado[f.estado])
        if f.solo_bajo_minimo:
            base = base.where(and_(umbral > 0, disponible <= umbral))

        filtrado = base.subquery()
        totales = self.db.execute(select(
            func.coalesce(func.sum(filtrado.c.disponible), 0), func.coalesce(func.sum(filtrado.c.reservada), 0),
            func.coalesce(func.sum(filtrado.c.vendida), 0), func.count().filter(filtrado.c.disponible == 0), func.count(),
        )).one()
        proximas = 0
        if en_transito:
            ids = self.db.scalars(select(filtrado.c.variante_id).where(filtrado.c.variante_id.in_(list(en_transito)))).all()
            proximas = sum(en_transito[i] for i in ids)

        por_sucursal = []
        if f.sucursal is None:
            por_sucursal = list(self.db.execute(
                select(Existencia.sucursal_id, func.sum(Existencia.disponible), func.sum(Existencia.reservada), func.sum(Existencia.vendida))
                .where(Existencia.empresa_id == eid, Existencia.variante_id.in_(select(filtrado.c.variante_id)))
                .group_by(Existencia.sucursal_id)
            ))

        pagina = self.db.execute(
            base.order_by(Producto.nombre, Talla.orden, Color.nombre, Variante.id).limit(f.tamano).offset((f.pagina - 1) * f.tamano)
        ).all()
        return totales, proximas, por_sucursal, pagina

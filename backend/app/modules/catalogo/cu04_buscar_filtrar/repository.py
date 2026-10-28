from sqlalchemy import func, or_, select

from app.modules.catalogo.cu03_consultar_catalogo.repository import CatalogoRepository
from app.modules.catalogo.cu04_buscar_filtrar.schemas import FiltrosBusqueda
from app.modules.inventario.publico import variantes_con_stock
from app.primer_parcial.catalogo.publico import Coleccion, Producto, Talla, Variante

ORDENES = {
    "recientes": (Producto.creado_en.desc(), Producto.id.desc()),
    "precio_asc": (Producto.precio_base.asc(), Producto.id),
    "precio_desc": (Producto.precio_base.desc(), Producto.id),
    "nombre": (func.lower(Producto.nombre), Producto.id),
}


class BusquedaRepository(CatalogoRepository):
    def buscar(self, f: FiltrosBusqueda) -> tuple[int, list[Producto]]:
        stmt = self.visibles()
        if f.q:
            patron = f"%{f.q.strip().lower()}%"
            stmt = stmt.where(or_(
                func.lower(Producto.nombre).like(patron), func.lower(Producto.descripcion).like(patron),
                func.lower(Producto.material).like(patron),
            ))
        if f.categoria_id is not None:
            stmt = stmt.where(Producto.categoria_id.in_(self.categoria_y_subcategorias(f.categoria_id)))
        if f.marca_id is not None:
            stmt = stmt.where(Producto.marca_id == f.marca_id)
        if f.genero:
            stmt = stmt.where(Producto.genero == f.genero)
        if f.coleccion_id is not None:
            stmt = stmt.where(Producto.coleccion_id == f.coleccion_id)
        if f.temporada_id is not None:
            stmt = stmt.where(Producto.coleccion_id.in_(select(Coleccion.id).where(Coleccion.temporada_id == f.temporada_id)))

        # Todos los filtros de variante van en UNA sola condición sobre la misma variante activa.
        sobre_variante = []
        if f.talla:
            sobre_variante.append(Variante.talla_id.in_(
                select(Talla.id).where(Talla.empresa_id == self.empresa_id, func.upper(Talla.codigo) == f.talla.strip().upper())
            ))
        if f.color_id is not None:
            sobre_variante.append(Variante.color_id == f.color_id)
        precio = func.coalesce(Variante.precio_especifico, Producto.precio_base)
        if f.precio_min is not None:
            sobre_variante.append(precio >= f.precio_min)
        if f.precio_max is not None:
            sobre_variante.append(precio <= f.precio_max)
        if f.sucursal is not None or f.solo_disponibles:
            sobre_variante.append(variantes_con_stock(self.empresa_id, f.sucursal))
        if sobre_variante:
            stmt = stmt.where(self.con_variante(*sobre_variante))

        return self.pagina(stmt.order_by(*ORDENES[f.orden]), f.pagina, f.tamano)

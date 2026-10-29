"""CU-37 · Descargar catálogo para uso offline (RF18, RN16). Capa de negocio.

Un subconjunto del catálogo de la empresa: productos activos con sus variantes, el stock y el precio con promoción de las sucursales autorizadas
(el personal, la suya (RN10); el cliente, todas las activas para elegir dónde reservar) y los datos mínimos de los clientes (solo el personal).
"""
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.constantes import CLIENTE
from app.core.tiempo import ahora
from app.modules.acceso.dependencias import Contexto
from app.modules.acceso.publico import nombres_y_correos_de_clientes
from app.modules.inventario.publico import Existencia
from app.modules.offline.cu37_catalogo_offline import schemas
from app.modules.sucursales.publico import sucursales_activas
from app.primer_parcial.catalogo.publico import Producto, descuentos_vigentes


class CatalogoOfflineService:
    def __init__(self, db: Session, ctx: Contexto):
        self.db = db
        self.ctx = ctx
        self.empresa_id = ctx.empresa_id

    def descargar(self) -> schemas.CatalogoLocalOut:
        sucursales = [s for s in sucursales_activas(self.db, self.empresa_id) if self.ctx.rol == CLIENTE or s["id"] == self.ctx.sucursal_id]
        ids = {s["id"] for s in sucursales}
        stock: dict[int, dict[int, int]] = {}
        for sucursal_id, variante_id, disponible in self.db.execute(
            select(Existencia.sucursal_id, Existencia.variante_id, Existencia.disponible).where(Existencia.empresa_id == self.empresa_id, Existencia.sucursal_id.in_(ids))
        ):
            stock.setdefault(variante_id, {})[sucursal_id] = int(disponible)

        descuentos = descuentos_vigentes(self.db, self.empresa_id)
        productos = self.db.scalars(
            select(Producto).where(Producto.empresa_id == self.empresa_id, Producto.activo.is_(True)).options(selectinload(Producto.variantes), selectinload(Producto.imagenes))
            .order_by(Producto.nombre)
        )
        salida = []
        for p in productos:
            variantes = []
            for v in sorted((v for v in p.variantes if v.activa), key=lambda v: v.sku):
                final, promocion = descuentos.precio_final(p, v.precio)
                variantes.append(schemas.VarianteLocalOut(
                    id=v.id, sku=v.sku, codigo_barras=v.codigo_barras, talla=v.talla.codigo, color=v.color.nombre, precio=v.precio, precio_final=final,
                    promocion=promocion.nombre if promocion else None, stock=stock.get(v.id, {}),
                ))
            if variantes:
                principal = next((i for i in p.imagenes if i.principal), p.imagenes[0] if p.imagenes else None)
                salida.append(schemas.ProductoLocalOut(id=p.id, nombre=p.nombre, categoria=p.categoria.nombre, genero=p.genero, imagen=principal.url if principal else None, variantes=variantes))
        clientes = [] if self.ctx.rol == CLIENTE else [schemas.ClienteLocalOut(id=i, nombre=n, email=e) for i, n, e in nombres_y_correos_de_clientes(self.db, self.empresa_id)]
        return schemas.CatalogoLocalOut(generado_en=ahora(), empresa_id=self.empresa_id, sucursales=[schemas.SucursalLocalOut(**s) for s in sucursales], productos=salida, clientes=clientes)

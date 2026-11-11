"""CU-37 · Descargar catálogo para uso offline (RF18, RN16). Capa de negocio.

Un subconjunto del catálogo de la empresa: productos activos con sus variantes, el stock y el precio con promoción de las sucursales autorizadas
(el personal, la suya (RN10); el cliente, todas las activas para elegir dónde reservar) y los datos mínimos de los clientes (solo el personal).
"""
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from datetime import timedelta

from app.core.constantes import CAJERO, CLIENTE, ENCARGADO
from app.core.tiempo import ahora
from app.modules.acceso.dependencias import Contexto
from app.modules.acceso.publico import nombres_y_correos_de_clientes
from app.modules.inventario.publico import Existencia
from app.modules.offline.cu37_catalogo_offline import schemas
from app.modules.sucursales.publico import sucursales_activas
from app.modules.ventas.publico import ESTADOS_COBRABLES, DevolucionService
from app.primer_parcial.reservas.publico import ReservasSucursalService
from app.primer_parcial.ventas.publico import Pedido
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
                    promocion=promocion.nombre if promocion else None, talla_id=v.talla_id, color_id=v.color_id, color_hex=v.color.codigo_hex, stock=stock.get(v.id, {}),
                ))
            if variantes:
                principal = next((i for i in p.imagenes if i.principal), p.imagenes[0] if p.imagenes else None)
                salida.append(schemas.ProductoLocalOut(
                    id=p.id, nombre=p.nombre, categoria=p.categoria.nombre, genero=p.genero, imagen=principal.ruta if principal else None,
                    publico_id=str(p.publico_id), slug=p.slug, descripcion=p.descripcion, marca=p.marca.nombre if p.marca else None,
                    coleccion=p.coleccion.nombre, temporada=p.coleccion.temporada.nombre, material=p.material, cuidado=p.cuidado,
                    imagenes=[{"id": i.id, "color_id": i.color_id, "url": i.ruta, "texto_alt": i.texto_alt, "principal": i.principal} for i in sorted(p.imagenes, key=lambda x: x.orden)],
                    variantes=variantes,
                ))
        clientes = [] if self.ctx.rol == CLIENTE else [schemas.ClienteLocalOut(id=i, nombre=n, email=e) for i, n, e in nombres_y_correos_de_clientes(self.db, self.empresa_id)]
        extra = self._para_el_personal() if self.ctx.rol in (CAJERO, ENCARGADO) and self.ctx.sucursal_id is not None else {}
        return schemas.CatalogoLocalOut(generado_en=ahora(), empresa_id=self.empresa_id, sucursales=[schemas.SucursalLocalOut(**s) for s in sucursales], productos=salida, clientes=clientes, **extra)

    def _para_el_personal(self) -> dict:
        """Lo que el personal necesita para atender sin conexión: las ventas recientes de su sucursal con el plazo de devolución (B3) y, el Encargado, las reservas activas (B4)."""
        devoluciones = DevolucionService(self.db, self.ctx)
        plazo = devoluciones.plazo().plazo_dias
        pedidos = self.db.scalars(
            select(Pedido).where(
                Pedido.empresa_id == self.empresa_id, Pedido.sucursal_id == self.ctx.sucursal_id, Pedido.estado == "PAGADO", Pedido.comprobante_numero.is_not(None),
                Pedido.pagado_en >= ahora() - timedelta(days=plazo),
            ).order_by(Pedido.pagado_en.desc()).limit(60)
        ).all()
        ventas = []
        for p in pedidos:
            v = devoluciones.venta(p.comprobante_numero)
            ventas.append(schemas.VentaRecienteLocalOut(
                comprobante=p.comprobante_numero, pagado_en=p.pagado_en, total=p.total, vence_el=v.vence_el,
                items=[schemas.ItemVentaLocalOut(pedido_item_id=i.pedido_item_id, producto=i.producto, talla=i.talla, color=i.color, vendida=i.vendida, devolvible=i.devolvible, precio_final=i.precio_final) for i in v.items],
            ))
        reservas = []
        for r in ReservasSucursalService(self.db, self.ctx).listar(None, None):
            if self.ctx.rol == CAJERO and r.estado not in ESTADOS_COBRABLES:
                continue  # el Cajero solo cobra reservas ya preparadas o atendidas (CU-29)
            reservas.append(schemas.ReservaSucursalLocalOut(
                id=r.id, codigo=r.codigo, cliente=r.cliente, estado=r.estado, programada_para=r.programada_para,
                items=[schemas.ItemReservaLocalOut(id=i.id, variante_id=i.variante_id, producto=i.producto, talla=i.talla, color=i.color, cantidad=i.cantidad, estado=i.estado) for i in r.items],
            ))
        return {"plazo_devolucion_dias": plazo, "ventas_recientes": ventas, "reservas_sucursal": reservas}

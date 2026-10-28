"""CU-03 · Consultar catálogo de prendas (RN01, RN02). Capa de negocio."""
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.errors import NoEncontrado
from app.modules.catalogo.cu03_consultar_catalogo import schemas
from app.modules.catalogo.cu03_consultar_catalogo.repository import CatalogoRepository
from app.modules.inventario.publico import disponible_por_variante
from app.modules.sucursales.publico import sucursal_de_empresa, sucursales_activas
from app.primer_parcial.catalogo.publico import Descuentos, Producto, descuentos_vigentes


def _orden_variante(v) -> tuple:
    return (v.talla.orden, v.color.nombre)  # tallas por display_order (S, M, L, XL), nunca por orden de creación


class CatalogoService:
    def __init__(self, db: Session, empresa_id: int):
        self.db = db
        self.empresa_id = empresa_id
        self.catalogo = CatalogoRepository(db, empresa_id)

    def sucursales(self) -> list[dict]:
        return sucursales_activas(self.db, self.empresa_id)

    def listar(self, categoria_id: int | None, sucursal_id: int | None, pagina: int, tamano: int) -> schemas.PrendasPagina:
        self.validar_sucursal(sucursal_id)
        categorias = self.catalogo.categoria_y_subcategorias(categoria_id) if categoria_id is not None else None
        total, productos = self.catalogo.listar(categorias, pagina, tamano)
        return self.pagina(total, productos, sucursal_id, pagina, tamano)

    def detalle(self, producto_id: int, sucursal_id: int | None) -> schemas.PrendaDetalle:
        self.validar_sucursal(sucursal_id)
        producto = self._producto(producto_id)
        tarjeta = self.tarjetas([producto], sucursal_id)[0]
        imagenes = sorted(producto.imagenes, key=lambda i: (not i.principal, i.orden, i.id))
        return schemas.PrendaDetalle(
            **tarjeta.model_dump(), descripcion=producto.descripcion, material=producto.material, cuidado=producto.cuidado,
            imagenes=[
                schemas.ImagenOut(id=i.id, color_id=i.color_id, url=f"/media/{i.ruta}", texto_alt=i.texto_alt, principal=i.principal)
                for i in imagenes
            ],
        )

    def opciones(self, producto_id: int, sucursal_id: int | None) -> schemas.OpcionesOut:
        """Matriz color × talla con disponibilidad: una sola consulta agrupada de existencias, solo variantes activas."""
        self.validar_sucursal(sucursal_id)
        producto = self._producto(producto_id)
        variantes = sorted((v for v in producto.variantes if v.activa), key=_orden_variante)
        stock = disponible_por_variante(self.db, self.empresa_id, [v.id for v in variantes], sucursal_id)
        descuentos = descuentos_vigentes(self.db, self.empresa_id)

        filas = [
            schemas.OpcionVariante(
                variante_id=v.id, sku=v.sku, talla_id=v.talla_id, talla=v.talla.codigo, color_id=v.color_id, color=v.color.nombre,
                precio=v.precio, precio_final=descuentos.precio_final(producto, v.precio)[0],
                disponible=stock.get(v.id, 0) > 0, cantidad=stock.get(v.id, 0), orden=v.talla.orden,
            )
            for v in variantes
        ]
        tallas = {v.talla_id: v.talla for v in variantes}
        colores = {v.color_id: v.color for v in variantes}
        return schemas.OpcionesOut(
            producto_id=producto.id, sucursal_id=sucursal_id,
            tallas=[
                schemas.OpcionTalla(id=t.id, codigo=t.codigo, orden=t.orden, disponible=any(f.disponible for f in filas if f.talla_id == t.id))
                for t in sorted(tallas.values(), key=lambda t: (t.orden, t.codigo))
            ],
            colores=[
                schemas.OpcionColor(id=c.id, nombre=c.nombre, codigo_hex=c.codigo_hex, disponible=any(f.disponible for f in filas if f.color_id == c.id))
                for c in sorted(colores.values(), key=lambda c: c.nombre)
            ],
            variantes=filas,
        )

    # ---- compartido con CU-04 ----
    def pagina(self, total: int, productos: list[Producto], sucursal_id: int | None, pagina: int, tamano: int) -> schemas.PrendasPagina:
        return schemas.PrendasPagina(total=total, pagina=pagina, tamano=tamano, items=self.tarjetas(productos, sucursal_id))

    def tarjetas(self, productos: list[Producto], sucursal_id: int | None) -> list[schemas.PrendaOut]:
        activas = {p.id: [v for v in p.variantes if v.activa] for p in productos}
        stock = disponible_por_variante(self.db, self.empresa_id, [v.id for vs in activas.values() for v in vs], sucursal_id)
        descuentos = descuentos_vigentes(self.db, self.empresa_id)
        return [self._tarjeta(p, activas[p.id], stock, descuentos) for p in productos]

    def validar_sucursal(self, sucursal_id: int | None) -> None:
        if sucursal_id is not None and not sucursal_de_empresa(self.db, self.empresa_id, sucursal_id):
            raise NoEncontrado("Sucursal no encontrada.")  # también si es de otra empresa

    def _producto(self, producto_id: int) -> Producto:
        producto = self.catalogo.obtener_visible(producto_id)
        if producto is None:
            raise NoEncontrado("Producto no encontrado.")
        return producto

    def _tarjeta(self, p: Producto, variantes: list, stock: dict[int, int], descuentos: Descuentos) -> schemas.PrendaOut:
        variantes = sorted(variantes, key=_orden_variante)
        mejor: tuple[Decimal, object, Decimal] = min(
            ((*descuentos.precio_final(p, v.precio), v.precio) for v in variantes), key=lambda o: o[0]
        )
        precio_final, promocion, precio = mejor
        principal = min(p.imagenes, key=lambda i: (not i.principal, i.orden, i.id), default=None)
        colores = {v.color_id: v.color for v in variantes}
        tallas = {v.talla_id: v.talla for v in variantes}
        return schemas.PrendaOut(
            id=p.id, publico_id=str(p.publico_id), nombre=p.nombre, slug=p.slug, categoria=p.categoria.nombre,
            marca=p.marca.nombre if p.marca else None, genero=p.genero, coleccion=p.coleccion.nombre,
            temporada=p.coleccion.temporada.nombre, precio=precio, precio_final=precio_final,
            promocion=promocion.nombre if promocion else None, imagen=f"/media/{principal.ruta}" if principal else None,
            colores=[schemas.ColorOut(id=c.id, nombre=c.nombre, codigo_hex=c.codigo_hex) for c in sorted(colores.values(), key=lambda c: c.nombre)],
            tallas=[t.codigo for t in sorted(tallas.values(), key=lambda t: (t.orden, t.codigo))],
            disponible=any(stock.get(v.id, 0) > 0 for v in variantes),
        )

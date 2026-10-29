"""CU-28 · Consultar productos en punto de venta (RN10). Capa de negocio: el cajero ve el stock de SU sucursal."""
from sqlalchemy.orm import Session

from app.core.errors import NoEncontrado, Prohibido
from app.modules.acceso.dependencias import Contexto
from app.modules.inventario.publico import disponible_por_variante
from app.primer_parcial.catalogo.publico import descuentos_vigentes
from app.primer_parcial.ventas.cu28_productos_en_caja import schemas
from app.primer_parcial.ventas.cu28_productos_en_caja.repository import CajaRepository

MSG_CODIGO = "El código de barras escaneado no coincide con ningún producto registrado en la base de datos."  # excepción de la ficha CU-28


def sucursal_de_caja(ctx: Contexto) -> int:
    """RN10: el Cajero y el Encargado operan únicamente en su sucursal."""
    if ctx.sucursal_id is None:
        raise Prohibido("Su usuario no tiene una sucursal asignada.")
    return ctx.sucursal_id


class ProductosCajaService:
    def __init__(self, db: Session, ctx: Contexto):
        self.db = db
        self.ctx = ctx
        self.sucursal_id = sucursal_de_caja(ctx)
        self.caja = CajaRepository(db, ctx.empresa_id)

    def buscar(self, q: str, limite: int = 30) -> list[schemas.ProductoCajaOut]:
        """Paso 2 de la prueba: coincidencias por nombre, SKU o código de barras, con precio y promoción vigente."""
        return self._salida(self.caja.buscar(q, limite))

    def por_codigo(self, codigo: str) -> schemas.ProductoCajaOut:
        """Paso 1: el lector entrega un código y el sistema devuelve la prenda; si no existe, el mensaje de la ficha."""
        variante = self.caja.por_codigo(codigo)
        if variante is None:
            raise NoEncontrado(MSG_CODIGO)  # también si el código es de otra empresa
        return self._salida([variante])[0]

    def _salida(self, variantes) -> list[schemas.ProductoCajaOut]:
        stock = disponible_por_variante(self.db, self.ctx.empresa_id, [v.id for v in variantes], self.sucursal_id)
        imagenes = self.caja.imagenes_principales({v.producto_id for v in variantes})
        descuentos = descuentos_vigentes(self.db, self.ctx.empresa_id)
        filas = []
        for v in variantes:
            final, promocion = descuentos.precio_final(v.producto, v.precio)
            filas.append(schemas.ProductoCajaOut(
                variante_id=v.id, producto_id=v.producto_id, sku=v.sku, codigo_barras=v.codigo_barras, producto=v.producto.nombre, talla=v.talla.codigo,
                color=v.color.nombre, precio=v.precio, precio_final=final, promocion=promocion.nombre if promocion else None,
                disponible=stock.get(v.id, 0), imagen=f"/media/{imagenes[v.producto_id]}" if v.producto_id in imagenes else None,
            ))
        return filas

from datetime import datetime, timedelta

from sqlalchemy import delete, func, select

from app.core.tenant import TenantRepository
from app.primer_parcial.catalogo.publico import Categoria, Color, Producto, Talla, Variante
from app.primer_parcial.ia.models import InteraccionCliente, PreferenciaCliente
from app.primer_parcial.ventas.publico import Pedido, PedidoItem

MAX_INTERACCIONES = 200  # se conserva lo último: es lo que mejor dice qué le gusta hoy


class AsistenteRepository(TenantRepository[Pedido]):
    model = Pedido

    def nombres_de_categorias(self) -> list[tuple[int, str]]:
        return [(i, n) for i, n in self.db.execute(select(Categoria.id, Categoria.nombre).where(Categoria.empresa_id == self.empresa_id).order_by(Categoria.nombre))]

    def nombres_de_colores(self) -> list[tuple[int, str]]:
        return [(i, n) for i, n in self.db.execute(select(Color.id, Color.nombre).where(Color.empresa_id == self.empresa_id).order_by(Color.nombre))]

    def compras_del_cliente(self, cliente_id: int) -> list[tuple]:
        """Cada prenda que compró el cliente: (producto, categoría, color, talla, precio, cantidad, fecha)."""
        stmt = (
            select(Producto.id, Producto.categoria_id, Variante.color_id, Talla.codigo, PedidoItem.precio_final, PedidoItem.cantidad, Pedido.pagado_en)
            .join(Variante, Variante.id == PedidoItem.variante_id).join(Talla, Talla.id == Variante.talla_id).join(Producto, Producto.id == Variante.producto_id)
            .join(Pedido, Pedido.id == PedidoItem.pedido_id)
            .where(PedidoItem.empresa_id == self.empresa_id, Pedido.cliente_id == cliente_id, Pedido.estado == "PAGADO")
        )
        return [tuple(f) for f in self.db.execute(stmt)]

    def mas_vendidos(self, limite: int = 12, dias: int = 90) -> list[int]:
        """Ids de los productos más vendidos de la empresa en los últimos días."""
        desde = datetime.now().astimezone() - timedelta(days=dias)
        stmt = (
            select(Producto.id).join(Variante, Variante.producto_id == Producto.id).join(PedidoItem, PedidoItem.variante_id == Variante.id)
            .join(Pedido, Pedido.id == PedidoItem.pedido_id)
            .where(PedidoItem.empresa_id == self.empresa_id, Pedido.estado == "PAGADO", Pedido.pagado_en >= desde)
            .group_by(Producto.id).order_by(func.sum(PedidoItem.cantidad).desc()).limit(limite)
        )
        return list(self.db.scalars(stmt))

    def producto_existe(self, producto_id: int) -> Producto | None:
        return self.db.scalar(select(Producto).where(Producto.empresa_id == self.empresa_id, Producto.id == producto_id))


class InteraccionRepository(TenantRepository[InteraccionCliente]):
    model = InteraccionCliente

    def del_cliente(self, cliente_id: int) -> list[tuple]:
        """(tipo, producto, categoría, color, talla, precio máximo, texto, fecha) de lo último que hizo el cliente."""
        stmt = (
            select(InteraccionCliente.tipo, InteraccionCliente.producto_id, InteraccionCliente.categoria_id, InteraccionCliente.color_id, InteraccionCliente.talla,
                   InteraccionCliente.precio_max, InteraccionCliente.texto, InteraccionCliente.creado_en)
            .where(InteraccionCliente.empresa_id == self.empresa_id, InteraccionCliente.cliente_id == cliente_id)
            .order_by(InteraccionCliente.creado_en.desc(), InteraccionCliente.id.desc()).limit(MAX_INTERACCIONES)
        )
        return [tuple(f) for f in self.db.execute(stmt)]

    def cuantas(self, cliente_id: int) -> int:
        return self.db.scalar(select(func.count(InteraccionCliente.id)).where(InteraccionCliente.empresa_id == self.empresa_id, InteraccionCliente.cliente_id == cliente_id)) or 0

    def recortar(self, cliente_id: int) -> None:
        conservar = select(InteraccionCliente.id).where(InteraccionCliente.empresa_id == self.empresa_id, InteraccionCliente.cliente_id == cliente_id) \
            .order_by(InteraccionCliente.creado_en.desc(), InteraccionCliente.id.desc()).limit(MAX_INTERACCIONES)
        self.db.execute(delete(InteraccionCliente).where(
            InteraccionCliente.empresa_id == self.empresa_id, InteraccionCliente.cliente_id == cliente_id, InteraccionCliente.id.not_in(conservar)))

    def borrar_del_cliente(self, cliente_id: int) -> None:
        self.db.execute(delete(InteraccionCliente).where(InteraccionCliente.empresa_id == self.empresa_id, InteraccionCliente.cliente_id == cliente_id))

    def personaliza(self, cliente_id: int) -> bool:
        fila = self.db.scalar(select(PreferenciaCliente).where(PreferenciaCliente.empresa_id == self.empresa_id, PreferenciaCliente.cliente_id == cliente_id))
        return True if fila is None else fila.personalizar

    def fijar_personalizar(self, cliente_id: int, valor: bool) -> None:
        fila = self.db.scalar(select(PreferenciaCliente).where(PreferenciaCliente.empresa_id == self.empresa_id, PreferenciaCliente.cliente_id == cliente_id))
        if fila is None:
            self.db.add(PreferenciaCliente(cliente_id=cliente_id, empresa_id=self.empresa_id, personalizar=valor))
        else:
            fila.personalizar = valor

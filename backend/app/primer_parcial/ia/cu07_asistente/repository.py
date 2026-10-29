from datetime import datetime, timedelta

from sqlalchemy import func, select

from app.core.tenant import TenantRepository
from app.primer_parcial.catalogo.publico import Categoria, Color, Producto, Variante
from app.primer_parcial.ventas.publico import Pedido, PedidoItem


class AsistenteRepository(TenantRepository[Pedido]):
    model = Pedido

    def nombres_de_categorias(self) -> list[tuple[int, str]]:
        return [(i, n) for i, n in self.db.execute(select(Categoria.id, Categoria.nombre).where(Categoria.empresa_id == self.empresa_id).order_by(Categoria.nombre))]

    def nombres_de_colores(self) -> list[tuple[int, str]]:
        return [(i, n) for i, n in self.db.execute(select(Color.id, Color.nombre).where(Color.empresa_id == self.empresa_id).order_by(Color.nombre))]

    def compras_del_cliente(self, cliente_id: int) -> tuple[list[tuple[int, int]], list[tuple[int, int]], set[int]]:
        """Qué categorías y colores compró más el cliente: ([(categoria_id, unidades)], [(color_id, unidades)], productos que ya compró)."""
        base = (
            select(Producto.categoria_id, Variante.color_id, Producto.id, PedidoItem.cantidad).join(Variante, Variante.id == PedidoItem.variante_id)
            .join(Producto, Producto.id == Variante.producto_id).join(Pedido, Pedido.id == PedidoItem.pedido_id)
            .where(PedidoItem.empresa_id == self.empresa_id, Pedido.cliente_id == cliente_id, Pedido.estado == "PAGADO")
        )
        categorias: dict[int, int] = {}
        colores: dict[int, int] = {}
        productos: set[int] = set()
        for categoria_id, color_id, producto_id, cantidad in self.db.execute(base):
            categorias[categoria_id] = categorias.get(categoria_id, 0) + cantidad
            colores[color_id] = colores.get(color_id, 0) + cantidad
            productos.add(producto_id)
        ordenar = lambda d: sorted(d.items(), key=lambda x: -x[1])  # noqa: E731
        return ordenar(categorias), ordenar(colores), productos

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

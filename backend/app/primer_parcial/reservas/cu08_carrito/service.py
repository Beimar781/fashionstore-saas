"""CU-08 · Gestionar carrito de compras (RN01, RN02). Capa de negocio.

El carrito es de un cliente dentro de una empresa y de una sucursal (de ahí sale el stock). No aparta stock: la disponibilidad se
vuelve a verificar al agregar, al mostrar el carrito y al pagar.
"""
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.errors import Conflicto, DatosInvalidos, NoEncontrado
from app.modules.inventario.publico import disponible_por_variante
from app.modules.sucursales.publico import datos_de_sucursal_activa, nombres_de_sucursales
from app.core.tiempo import ahora
from app.core.tipos import iva_incluido
from app.primer_parcial.catalogo.publico import descuentos_vigentes
from app.primer_parcial.reservas.cu08_carrito import schemas
from app.primer_parcial.reservas.cu08_carrito.repository import CarritoRepository, VarianteCarritoRepository
from app.primer_parcial.reservas.models import Carrito

MSG_STOCK = "La cantidad solicitada supera el stock disponible temporalmente."  # excepción de la ficha CU-08
MSG_ELEGIR_SUCURSAL = "Elija la sucursal en la que desea comprar."
MSG_NO_DISPONIBLE = "La prenda ya no está disponible en el catálogo."


class CarritoService:
    def __init__(self, db: Session, empresa_id: int):
        self.db = db
        self.empresa_id = empresa_id
        self.carritos = CarritoRepository(db, empresa_id)
        self.variantes = VarianteCarritoRepository(db, empresa_id)

    # ---- pasos 4 y 5 de la ficha: ver el carrito con su subtotal ----
    def obtener(self, cliente_id: int) -> schemas.CarritoOut:
        return self._salida(self.carritos.de_cliente(cliente_id))

    # ---- pasos 1 a 3: agregar ----
    def agregar(self, cliente_id: int, datos: schemas.ItemIn) -> schemas.CarritoOut:
        variante = self._habilitada(datos.variante_id)
        carrito = self.carritos.de_cliente(cliente_id) or self.carritos.crear(cliente_id)
        self._fijar_sucursal(carrito, datos.sucursal_id)
        existente = next((i for i in carrito.items if i.variante_id == variante.id), None)
        total = (existente.cantidad if existente else 0) + datos.cantidad
        self._verificar_stock(variante.id, total, carrito.sucursal_id)  # el stock se valida al agregar, no solo al pagar
        if existente:
            existente.cantidad = total
        else:
            self.carritos.agregar_item(carrito, variante.id, datos.cantidad)
        return self._guardar(carrito)

    # ---- paso 3 de la prueba: modificar la cantidad ----
    def cambiar_cantidad(self, cliente_id: int, item_id: int, cantidad: int) -> schemas.CarritoOut:
        carrito, item = self._item(cliente_id, item_id)
        self._habilitada(item.variante_id)
        self._verificar_stock(item.variante_id, cantidad, carrito.sucursal_id)
        item.cantidad = cantidad
        return self._guardar(carrito)

    # ---- paso 4 de la prueba: eliminar ----
    def quitar(self, cliente_id: int, item_id: int) -> schemas.CarritoOut:
        carrito, item = self._item(cliente_id, item_id)
        carrito.items.remove(item)
        return self._guardar(carrito)

    def elegir_sucursal(self, cliente_id: int, sucursal_id: int) -> schemas.CarritoOut:
        """Cambia la sucursal del carrito. Las prendas que no tengan stock allí se marcan: no se pierden, pero no se pueden pagar."""
        carrito = self.carritos.de_cliente(cliente_id) or self.carritos.crear(cliente_id)
        if datos_de_sucursal_activa(self.db, self.empresa_id, sucursal_id) is None:
            raise NoEncontrado("Sucursal no encontrada.")  # también si es de otra empresa o está inactiva
        carrito.sucursal_id = sucursal_id
        return self._guardar(carrito)

    def vaciar(self, cliente_id: int, confirmar: bool = True) -> schemas.CarritoOut:
        """Quita todas las prendas. El pago lo llama con `confirmar=False` para que todo se guarde en una sola transacción."""
        carrito = self.carritos.de_cliente(cliente_id)
        if carrito is not None:
            carrito.items.clear()
            if confirmar:
                self.db.commit()
        return self._salida(carrito)

    # ---- auxiliares ----
    def _guardar(self, carrito: Carrito) -> schemas.CarritoOut:
        carrito.actualizado_en = ahora()
        self.db.commit()
        return self._salida(carrito)

    def _habilitada(self, variante_id: int):
        variante = self.variantes.con_producto({variante_id}).get(variante_id)
        if variante is None or not variante.activa or not variante.producto.activo:
            raise DatosInvalidos(MSG_NO_DISPONIBLE)  # sin variantes inactivas ni de otra empresa
        return variante

    def _fijar_sucursal(self, carrito: Carrito, sucursal_id: int | None) -> None:
        if carrito.sucursal_id is not None:
            if sucursal_id is not None and sucursal_id != carrito.sucursal_id:
                if carrito.items:
                    nombre = nombres_de_sucursales(self.db, self.empresa_id).get(carrito.sucursal_id, "")
                    raise Conflicto(f"Su carrito es para la sucursal {nombre}. Cambie de sucursal en el carrito o vacíelo.")
            else:
                return
        if sucursal_id is None:
            raise DatosInvalidos(MSG_ELEGIR_SUCURSAL)
        if datos_de_sucursal_activa(self.db, self.empresa_id, sucursal_id) is None:
            raise NoEncontrado("Sucursal no encontrada.")
        carrito.sucursal_id = sucursal_id

    def _verificar_stock(self, variante_id: int, cantidad: int, sucursal_id: int | None) -> None:
        disponible = disponible_por_variante(self.db, self.empresa_id, [variante_id], sucursal_id).get(variante_id, 0)
        if cantidad > disponible:
            raise Conflicto(MSG_STOCK)

    def _item(self, cliente_id: int, item_id: int):
        carrito = self.carritos.de_cliente(cliente_id)
        item = next((i for i in carrito.items if i.id == item_id), None) if carrito else None
        if item is None:
            raise NoEncontrado("Prenda del carrito no encontrada.")  # también si es del carrito de otro cliente
        return carrito, item

    def _salida(self, carrito: Carrito | None) -> schemas.CarritoOut:
        """Arma el carrito con precios vigentes (promociones incluidas), disponibilidad actual y totales."""
        items = list(carrito.items) if carrito else []
        sucursal_id = carrito.sucursal_id if carrito else None
        sucursal = nombres_de_sucursales(self.db, self.empresa_id).get(sucursal_id) if sucursal_id else None
        variantes = self.variantes.con_producto({i.variante_id for i in items})
        stock = disponible_por_variante(self.db, self.empresa_id, variantes, sucursal_id) if sucursal_id else {}
        imagenes = self.variantes.imagenes_principales({v.producto_id for v in variantes.values()})
        descuentos = descuentos_vigentes(self.db, self.empresa_id)

        filas, avisos = [], []
        for item in items:
            v = variantes[item.variante_id]
            disponible = stock.get(v.id, 0)
            retirada = not v.activa or not v.producto.activo
            estado = "RETIRADA" if retirada else ("SIN_STOCK" if item.cantidad > disponible else "OK")
            final = descuentos.precio_final(v.producto, v.precio)[0]
            filas.append(schemas.ItemCarritoOut(
                id=item.id, variante_id=v.id, producto_id=v.producto_id, sku=v.sku, producto=v.producto.nombre, talla=v.talla.codigo,
                color=v.color.nombre, imagen=f"/media/{imagenes[v.producto_id]}" if v.producto_id in imagenes else None,
                cantidad=item.cantidad, precio=v.precio, precio_final=final, subtotal=final * item.cantidad, disponible=disponible, estado=estado,
            ))
            nombre = f"{v.producto.nombre} ({v.talla.codigo}, {v.color.nombre})"
            if retirada:
                avisos.append(f"{nombre} ya no está disponible en el catálogo. Quítela del carrito.")
            elif estado == "SIN_STOCK":
                avisos.append(f"{nombre}: en {sucursal} hay {disponible} disponible(s) y tiene {item.cantidad} en el carrito.")

        subtotal = sum((f.precio * f.cantidad for f in filas), Decimal(0))
        total = sum((f.subtotal for f in filas), Decimal(0))
        iva = iva_incluido(total)
        return schemas.CarritoOut(
            sucursal_id=sucursal_id, sucursal=sucursal, items=filas, total_unidades=sum(f.cantidad for f in filas), subtotal=subtotal,
            descuento=subtotal - total, iva_incluido=iva, total=total, avisos=avisos,
            puede_pagar=bool(filas) and sucursal_id is not None and all(f.estado == "OK" for f in filas),
        )

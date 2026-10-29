"""CU-29 · Registrar venta presencial (RN10). Capa de negocio.

El cajero arma la venta con las prendas que escanea o busca (CU-28), o la toma de una reserva ya preparada. La venta queda
«pendiente de cobro» (pedido PRESENCIAL de entrega EN_TIENDA); el stock se descuenta cuando se cobra (CU-30).
"""
from sqlalchemy.orm import Session

from app.core.errors import Conflicto, DatosInvalidos, NoEncontrado
from app.core.tiempo import ahora
from app.modules.acceso.dependencias import Contexto
from app.modules.acceso.publico import cliente_por_email
from app.modules.inventario.publico import disponible_por_variante
from app.modules.reservas.publico import ReservaOut, ReservaService
from app.modules.sucursales.publico import nombres_de_sucursales
from app.modules.ventas.cu29_venta_presencial import schemas
from app.modules.ventas.cu29_venta_presencial.repository import VarianteVentaRepository
from app.primer_parcial.catalogo.publico import descuentos_vigentes
from app.primer_parcial.ventas.publico import CompraService, Linea, PedidoOut, sucursal_de_caja

MSG_SIN_PRENDAS = "Agregue al menos una prenda a la venta."
MSG_NO_DISPONIBLE = "Una o más prendas ya no están disponibles en el catálogo."
MSG_CODIGO_RESERVA = "El código de reserva no existe o ya ha expirado su vigencia."  # el mismo de la ficha CU-25
MSG_FUERA_DE_RESERVA = "La venta incluye prendas o cantidades que no están en la reserva."
ESTADOS_COBRABLES = ("PREPARADA", "EN_PROBADOR")


class VentaPresencialService:
    def __init__(self, db: Session, ctx: Contexto):
        self.db = db
        self.ctx = ctx
        self.empresa_id = ctx.empresa_id
        self.sucursal_id = sucursal_de_caja(ctx)
        self.compras = CompraService(db, ctx)
        self.variantes = VarianteVentaRepository(db, ctx.empresa_id)
        self.reservas = ReservaService(db, ctx.empresa_id)

    # ---- pasos 1 a 4: armar la venta ----
    def crear(self, datos: schemas.VentaIn, commit: bool = True, verificar_stock: bool = True) -> PedidoOut:
        reserva = self._reserva_para_cobrar(datos.reserva_codigo) if datos.reserva_codigo else None
        pedidas = self._pedidas(datos, reserva)
        variantes = self.variantes.con_producto(set(pedidas)) if reserva else self.variantes.vendibles(set(pedidas))
        if len(variantes) != len(pedidas):
            raise DatosInvalidos(MSG_NO_DISPONIBLE)  # también si la prenda es de otra empresa
        if reserva is None and verificar_stock:
            self._verificar_stock(pedidas, variantes)  # una reserva ya tiene su stock apartado

        descuentos = descuentos_vigentes(self.db, self.empresa_id)
        lineas = [
            Linea(v.id, v.sku, v.producto.nombre, v.talla.codigo, v.color.nombre, pedidas[v.id], v.precio, descuentos.precio_final(v.producto, v.precio)[0])
            for v in variantes.values()
        ]
        if reserva is not None:  # una reserva tiene una sola venta abierta: la nueva reemplaza a la anterior
            anterior = self.compras.venta_abierta_de_reserva(reserva.id)
            if anterior is not None:
                self.compras.cancelar(anterior, "Reemplazada por una nueva venta.")
                self.db.flush()
        pedido = self.compras.crear_pedido(
            sucursal_id=self.sucursal_id, canal="PRESENCIAL", tipo_entrega="EN_TIENDA", lineas=lineas, cliente_id=self._cliente_id(datos, reserva),
            nit_ci=datos.nit_ci.strip() or "0", razon_social=datos.razon_social.strip() or "Sin nombre", reserva_id=reserva.id if reserva else None,
        )
        self.db.commit() if commit else self.db.flush()  # la sincronización offline (CU-38) hace un solo commit por operación
        return self.compras.salida([pedido])[0]

    # ---- consultas y anulación de la venta en curso ----
    def pendientes(self) -> list[PedidoOut]:
        return self.compras.salida(self.compras.ventas_abiertas(self.sucursal_id))

    def obtener(self, pedido_id: int) -> PedidoOut:
        return self.compras.salida([self.compras.venta_de_caja(pedido_id, self.sucursal_id)])[0]

    def anular(self, pedido_id: int) -> PedidoOut:
        pedido = self.compras.venta_de_caja(pedido_id, self.sucursal_id)
        if pedido.estado == "PAGADO":
            raise Conflicto("Una venta ya cobrada no se puede anular; registre una devolución.")
        if pedido.estado == "CANCELADO":
            raise Conflicto("La venta ya está anulada.")
        self.compras.cancelar(pedido, "Anulada en caja.")
        self.db.commit()
        return self.compras.salida([pedido])[0]

    def reserva(self, codigo: str) -> ReservaOut:
        """Datos de la reserva que el cliente presenta en caja (paso previo a cobrarla)."""
        return self.reservas.salida([self._reserva_para_cobrar(codigo)])[0]

    # ---- auxiliares ----
    def _reserva_para_cobrar(self, codigo: str):
        reserva = self.reservas.por_codigo(codigo)
        if reserva is None or reserva.estado not in ESTADOS_COBRABLES or reserva.vence_en <= ahora():
            raise NoEncontrado(MSG_CODIGO_RESERVA)  # inexistente, de otra empresa, cerrada o vencida
        if reserva.sucursal_id != self.sucursal_id:
            raise Conflicto("La reserva corresponde a otra sucursal.")
        return reserva

    def _pedidas(self, datos: schemas.VentaIn, reserva) -> dict[int, int]:
        pedidas: dict[int, int] = {}
        for item in datos.items:
            pedidas[item.variante_id] = pedidas.get(item.variante_id, 0) + item.cantidad  # una prenda repetida se suma
        if reserva is not None:
            reservadas = {i.variante_id: i.cantidad for i in reserva.items if i.estado == "RESERVADO"}
            if not pedidas:
                return reservadas  # sin elegir: el cliente se lleva toda la reserva
            if any(v not in reservadas or c > reservadas[v] for v, c in pedidas.items()):
                raise DatosInvalidos(MSG_FUERA_DE_RESERVA)
        elif not pedidas:
            raise DatosInvalidos(MSG_SIN_PRENDAS)
        return pedidas

    def _verificar_stock(self, pedidas: dict[int, int], variantes) -> None:
        disponibles = disponible_por_variante(self.db, self.empresa_id, pedidas, self.sucursal_id)
        faltantes = [
            f"{variantes[v].producto.nombre} ({variantes[v].talla.codigo}, {variantes[v].color.nombre}): solicitadas {c}, disponibles {disponibles.get(v, 0)}"
            for v, c in pedidas.items() if disponibles.get(v, 0) < c
        ]
        if faltantes:
            sucursal = nombres_de_sucursales(self.db, self.empresa_id).get(self.sucursal_id, "")
            raise Conflicto(f"No hay stock suficiente en {sucursal} para: " + "; ".join(faltantes) + ".")

    def _cliente_id(self, datos: schemas.VentaIn, reserva) -> int | None:
        if reserva is not None:
            return reserva.cliente_id  # la venta aparece en el historial del cliente que reservó
        if datos.cliente_email and datos.cliente_email.strip():
            cliente = cliente_por_email(self.db, self.empresa_id, datos.cliente_email)
            if cliente is None:
                raise NoEncontrado("No hay un cliente registrado con ese correo.")
            return cliente.id
        return None

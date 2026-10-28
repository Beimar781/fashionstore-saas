"""CU-26 · Gestionar disponibilidad e inventario de la sucursal (RN01, RN02, RN10). Capa de negocio.

Todo cambio de existencias pasa por `aplicar_movimientos`: valida que nada quede en negativo y deja una fila
en la bitácora con tipo, referencia y usuario. Los demás paquetes (reservas, ventas) la usan desde `publico.py`.
"""
from datetime import date

from sqlalchemy.orm import Session

from app.core.constantes import ADMIN
from app.core.errors import Conflicto, NoEncontrado, Prohibido
from app.modules.acceso.dependencias import Contexto
from app.modules.acceso.publico import nombres_de_usuarios
from app.modules.inventario.cu26_inventario_sucursal import schemas
from app.modules.inventario.cu26_inventario_sucursal.repository import ExistenciaRepository, MovimientoRepository, VarianteLectura
from app.modules.sucursales.publico import nombres_de_sucursales
from app.primer_parcial.proveedores.publico import LoteOut, lotes_para_recibir, recibir_lote

# Efecto de cada tipo de movimiento sobre (disponible, reservada, vendida), por unidad
EFECTOS: dict[str, tuple[int, int, int]] = {
    "ENTRADA_RECEPCION": (+1, 0, 0),
    "AJUSTE_ENTRADA": (+1, 0, 0),
    "AJUSTE_SALIDA": (-1, 0, 0),
    "RESERVA": (-1, +1, 0),
    "LIBERA_RESERVA": (+1, -1, 0),
    "VENTA": (-1, 0, +1),
    "VENTA_RESERVA": (0, -1, +1),
    "DEVOLUCION": (+1, 0, -1),
}


def sucursal_del_usuario(ctx: Contexto) -> int:
    """RN10: el Encargado opera únicamente en su sucursal."""
    if ctx.sucursal_id is None:
        raise Prohibido("Su usuario no tiene una sucursal asignada.")
    return ctx.sucursal_id


class InventarioService:
    def __init__(self, db: Session, empresa_id: int):
        self.db = db
        self.empresa_id = empresa_id
        self.existencias = ExistenciaRepository(db, empresa_id)
        self.movimientos = MovimientoRepository(db, empresa_id)
        self.variantes = VarianteLectura(db, empresa_id)

    def aplicar_movimientos(
        self, sucursal_id: int, lineas: list[tuple[int, int]], tipo: str, referencia_tipo: str,
        referencia_id: int | None = None, usuario_id: int | None = None, nota: str = "",
    ) -> None:
        """Aplica un tipo de movimiento a varias variantes (todo o nada). No hace commit: lo hace quien lo llama."""
        d_disponible, d_reservada, d_vendida = EFECTOS[tipo]
        filas = self.existencias.bloquear(sucursal_id, sorted({variante_id for variante_id, _ in lineas}))
        for variante_id, cantidad in lineas:
            e = filas[variante_id]
            disponible = e.disponible + d_disponible * cantidad
            reservada = e.reservada + d_reservada * cantidad
            vendida = e.vendida + d_vendida * cantidad
            if disponible < 0:
                raise Conflicto(f"Stock insuficiente: se requieren {cantidad} unidades, pero solo hay {e.disponible} disponibles.")
            if reservada < 0:
                raise Conflicto("No se pueden liberar más unidades de las que están reservadas.")
            if vendida < 0:
                raise Conflicto("No se pueden devolver más unidades de las que se vendieron.")
            e.disponible, e.reservada, e.vendida = disponible, reservada, vendida
            self.movimientos.registrar(
                sucursal_id=sucursal_id, variante_id=variante_id, tipo=tipo, cantidad=cantidad, referencia_tipo=referencia_tipo,
                referencia_id=referencia_id, usuario_id=usuario_id, nota=nota,
            )
        self.db.flush()

    # ---- ajustes del Encargado ----
    def ajustar(self, ctx: Contexto, datos: schemas.AjusteIn) -> schemas.ExistenciaOut:
        sucursal_id = sucursal_del_usuario(ctx)
        self._variante(datos.variante_id)
        self.aplicar_movimientos(
            sucursal_id, [(datos.variante_id, datos.cantidad)], datos.tipo, "MANUAL", usuario_id=ctx.usuario.id, nota=datos.nota.strip()
        )
        self.db.commit()
        return self._existencia_out(sucursal_id, datos.variante_id)

    def fijar_umbral(self, ctx: Contexto, variante_id: int, datos: schemas.UmbralIn) -> schemas.ExistenciaOut:
        sucursal_id = sucursal_del_usuario(ctx)
        self._variante(variante_id)
        self.existencias.bloquear(sucursal_id, [variante_id])[variante_id].umbral_minimo = datos.umbral_minimo
        self.db.commit()
        return self._existencia_out(sucursal_id, variante_id)

    # ---- bitácora ----
    def listar_movimientos(
        self, ctx: Contexto, sucursal_id: int | None, variante_id: int | None, tipo: str | None,
        desde: date | None, hasta: date | None, pagina: int, tamano: int,
    ) -> schemas.MovimientosPagina:
        if ctx.sucursal_id is not None and ctx.rol != ADMIN:
            sucursal_id = ctx.sucursal_id  # el Encargado solo ve los movimientos de su sucursal
        total, filas = self.movimientos.buscar(sucursal_id, variante_id, tipo, desde, hasta, pagina, tamano)
        sucursales = nombres_de_sucursales(self.db, self.empresa_id)
        usuarios = nombres_de_usuarios(self.db, self.empresa_id, {m.usuario_id for m, *_ in filas if m.usuario_id})
        return schemas.MovimientosPagina(total=total, pagina=pagina, tamano=tamano, items=[
            schemas.MovimientoOut(
                id=m.id, creado_en=m.creado_en, sucursal_id=m.sucursal_id, sucursal=sucursales.get(m.sucursal_id, ""),
                variante_id=m.variante_id, sku=sku, producto=producto, talla=talla, color=color, tipo=m.tipo, cantidad=m.cantidad,
                referencia_tipo=m.referencia_tipo, referencia_id=m.referencia_id, usuario=usuarios.get(m.usuario_id),
                nota=m.nota,
            )
            for m, sku, producto, talla, color in filas
        ])

    # ---- recepción de lotes en tránsito (CU-31) ----
    def recepciones(self, ctx: Contexto) -> list[LoteOut]:
        return lotes_para_recibir(self.db, ctx, ctx.sucursal_id if ctx.rol != ADMIN else None)

    def recibir(self, ctx: Contexto, lote_id: int, datos: schemas.RecepcionIn) -> LoteOut:
        """Suma al inventario lo recibido de un lote EN_TRANSITO y lo cierra como RECIBIDO."""
        sucursal_id = None if ctx.rol == ADMIN else sucursal_del_usuario(ctx)
        recibidas = {i.item_id: i.cantidad_recibida for i in datos.items}

        def aplicar(lote_id_: int, sucursal_destino: int, lineas: list[tuple[int, int]]) -> None:
            self.aplicar_movimientos(
                sucursal_destino, lineas, "ENTRADA_RECEPCION", "RECEPCION", lote_id_, ctx.usuario.id, f"Recepción del lote {lote_id_}"
            )

        return recibir_lote(self.db, ctx, lote_id, sucursal_id, recibidas or None, aplicar)

    # ---- auxiliares ----
    def _variante(self, variante_id: int):
        variante = self.variantes.obtener(variante_id)
        if variante is None:
            raise NoEncontrado("Variante no encontrada.")  # también si es de otra empresa
        return variante

    def _existencia_out(self, sucursal_id: int, variante_id: int) -> schemas.ExistenciaOut:
        e = self.existencias.bloquear(sucursal_id, [variante_id])[variante_id]
        return schemas.ExistenciaOut(
            variante_id=variante_id, disponible=e.disponible, reservada=e.reservada, vendida=e.vendida, umbral_minimo=e.umbral_minimo
        )

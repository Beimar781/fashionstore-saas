"""CU-24 · Gestionar reservas de la sucursal (RN10). Capa de negocio: el Encargado solo opera en su sucursal."""
from datetime import date, datetime, time, timedelta

from sqlalchemy.orm import Session

from app.core.errors import Conflicto, NoEncontrado, Prohibido
from app.core.tiempo import zona_local
from app.modules.acceso.dependencias import Contexto
from app.modules.reservas.publico import Reserva, ReservaOut, ReservaService, TEXTO_ESTADO, notificar

ACTIVAS = ("PENDIENTE", "PREPARADA", "EN_PROBADOR")


def sucursal_del_encargado(ctx: Contexto) -> int:
    if ctx.sucursal_id is None:
        raise Prohibido("Su usuario no tiene una sucursal asignada.")
    return ctx.sucursal_id


class ReservasSucursalService:
    def __init__(self, db: Session, ctx: Contexto):
        self.db = db
        self.ctx = ctx
        self.sucursal_id = sucursal_del_encargado(ctx)
        self.motor = ReservaService(db, ctx.empresa_id)

    def listar(self, estado: str | None, fecha: date | None) -> list[ReservaOut]:
        self.motor.expirar_vencidas()
        desde = hasta = None
        if fecha is not None:  # el día completo en hora de la tienda
            desde = datetime.combine(fecha, time.min, tzinfo=zona_local())
            hasta = desde + timedelta(days=1)
        reservas = self.motor.de_sucursal(self.sucursal_id, (estado,) if estado else ACTIVAS, desde, hasta)
        return self.motor.salida(reservas)

    def obtener(self, reserva_id: int) -> ReservaOut:
        return self.motor.salida([self._de_mi_sucursal(reserva_id)])[0]

    def preparar(self, reserva_id: int) -> ReservaOut:
        """Paso 5 de la ficha: las prendas quedan apartadas y el cliente recibe el aviso de que puede pasar a la tienda."""
        self.motor.expirar_vencidas()
        reserva = self._de_mi_sucursal(reserva_id)
        if not any(i.estado == "RESERVADO" for i in reserva.items):
            raise Conflicto("La reserva no tiene prendas por preparar.")
        self.motor.cambiar_estado(reserva, "PREPARADA")
        reserva.preparada_por = self.ctx.usuario.id
        notificar(
            self.db, self.ctx.empresa_id, "RESERVA_PREPARADA", f"Reserva {reserva.codigo} lista",
            "Sus prendas ya están preparadas: puede pasar a la tienda con su código de reserva.",
            usuario_id=reserva.cliente_id, referencia_tipo="RESERVA", referencia_id=reserva.id,
        )
        self.db.commit()
        return self.motor.salida([reserva])[0]

    def marcar_no_encontrado(self, reserva_id: int, item_id: int) -> ReservaOut:
        """Excepción de la ficha: la prenda no está en físico. Se ajusta el stock y se avisa al cliente con disculpas."""
        self.motor.expirar_vencidas()
        reserva = self._de_mi_sucursal(reserva_id)
        if reserva.estado not in ("PENDIENTE", "PREPARADA"):
            raise Conflicto(f"No se puede modificar una reserva {TEXTO_ESTADO[reserva.estado]}.")
        item = next((i for i in reserva.items if i.id == item_id), None)
        if item is None:
            raise NoEncontrado("Prenda de la reserva no encontrada.")
        if item.estado != "RESERVADO":
            raise Conflicto("La prenda ya fue marcada.")
        self.motor.liberar(reserva, [item], self.ctx.usuario.id, f"Prenda no encontrada (reserva {reserva.codigo})", no_encontrado=True)
        sin_prendas = not any(i.estado == "RESERVADO" for i in reserva.items)
        if sin_prendas:
            self.motor.cambiar_estado(reserva, "CANCELADA")
        notificar(  # ajuste de stock para la sucursal y disculpas para el cliente
            self.db, self.ctx.empresa_id, "AJUSTE_STOCK", f"Ajuste de stock · reserva {reserva.codigo}",
            f"Una prenda de la reserva {reserva.codigo} no se encontró en físico; se descontó del inventario de la sucursal.",
            sucursal_id=reserva.sucursal_id, referencia_tipo="RESERVA", referencia_id=reserva.id,
        )
        notificar(
            self.db, self.ctx.empresa_id, "RESERVA_AJUSTE", f"Ajuste en su reserva {reserva.codigo}",
            "Lamentamos el inconveniente: una de sus prendas ya no está disponible en la tienda."
            + (" Su reserva fue cancelada." if sin_prendas else " Preparamos el resto de su reserva."),
            usuario_id=reserva.cliente_id, referencia_tipo="RESERVA", referencia_id=reserva.id,
        )
        self.db.commit()
        return self.motor.salida([reserva])[0]

    def _de_mi_sucursal(self, reserva_id: int) -> Reserva:
        reserva = self.motor.completa(reserva_id)
        if reserva is None or reserva.sucursal_id != self.sucursal_id:
            raise NoEncontrado("Reserva no encontrada.")  # también si es de otra sucursal u otra empresa
        return reserva

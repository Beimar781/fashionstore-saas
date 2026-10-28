"""CU-10 · Consultar y cancelar reservas (RF12). Capa de negocio: el cliente solo ve y cancela las suyas."""
from sqlalchemy.orm import Session

from app.core.errors import Conflicto, NoEncontrado
from app.modules.acceso.dependencias import Contexto
from app.modules.reservas.cu09_reservar.repository import ReservaRepository
from app.modules.reservas.cu09_reservar.schemas import ReservaOut
from app.modules.reservas.cu09_reservar.service import TEXTO_ESTADO, ReservaService
from app.modules.reservas.models import Reserva
from app.modules.reservas.rf11_notificaciones.service import notificar


class ReservaClienteService:
    def __init__(self, db: Session, ctx: Contexto):
        self.db = db
        self.ctx = ctx
        self.motor = ReservaService(db, ctx.empresa_id)
        self.reservas = ReservaRepository(db, ctx.empresa_id)

    def listar(self, estado: str | None) -> list[ReservaOut]:
        self.motor.expirar_vencidas()  # lo vencido se refleja antes de mostrar
        reservas = self.reservas.buscar(cliente_id=self.ctx.usuario.id, estados=(estado,) if estado else None)
        return self.motor.salida(reservas)

    def obtener(self, reserva_id: int) -> ReservaOut:
        self.motor.expirar_vencidas()
        return self.motor.salida([self._propia(reserva_id)])[0]

    def cancelar(self, reserva_id: int, motivo: str) -> ReservaOut:
        self.motor.expirar_vencidas()
        reserva = self._propia(reserva_id)
        if reserva.estado not in ("PENDIENTE", "PREPARADA"):
            raise Conflicto(f"No se puede cancelar una reserva {TEXTO_ESTADO[reserva.estado]}.")
        self.motor.liberar(reserva, reserva.items, self.ctx.usuario.id, f"Cancelación de la reserva {reserva.codigo}")  # devuelve el stock
        self.motor.cambiar_estado(reserva, "CANCELADA")
        if motivo.strip():
            reserva.notas = f"{reserva.notas}\nCANCELADA: {motivo.strip()}".strip()
        notificar(  # RF11: la sucursal deja de preparar esas prendas
            self.db, self.ctx.empresa_id, "RESERVA_CANCELADA", f"Reserva {reserva.codigo} cancelada",
            f"{self.ctx.usuario.nombre} {self.ctx.usuario.apellidos} canceló su reserva. Las prendas volvieron a estar disponibles.",
            sucursal_id=reserva.sucursal_id, referencia_tipo="RESERVA", referencia_id=reserva.id,
        )
        self.db.commit()
        return self.motor.salida([reserva])[0]

    def _propia(self, reserva_id: int) -> Reserva:
        reserva = self.reservas.obtener_completa(reserva_id)
        if reserva is None or reserva.cliente_id != self.ctx.usuario.id:
            raise NoEncontrado("Reserva no encontrada.")  # también si es de otro cliente o de otra empresa
        return reserva

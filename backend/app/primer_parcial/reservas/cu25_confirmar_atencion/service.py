"""CU-25 · Confirmar recepción y atención del cliente (RN10). Capa de negocio."""
from sqlalchemy.orm import Session

from app.core.errors import Conflicto, NoEncontrado
from app.modules.acceso.dependencias import Contexto
from app.modules.reservas.publico import Reserva, ReservaOut, ReservaService
from app.primer_parcial.reservas.cu24_gestionar_reservas_sucursal.service import sucursal_del_encargado
from app.primer_parcial.reservas.cu25_confirmar_atencion import schemas

MSG_CODIGO = "El código de reserva no existe o ya ha expirado su vigencia."  # excepción de la ficha CU-25


class AtencionService:
    def __init__(self, db: Session, ctx: Contexto):
        self.db = db
        self.ctx = ctx
        self.sucursal_id = sucursal_del_encargado(ctx)
        self.motor = ReservaService(db, ctx.empresa_id)

    def validar_codigo(self, codigo: str) -> ReservaOut:
        """Pasos 1 a 3: el código debe existir, estar vigente y pertenecer a esta sucursal."""
        self.motor.expirar_vencidas()
        reserva = self.motor.por_codigo(codigo)
        if reserva is None or reserva.estado not in ("PENDIENTE", "PREPARADA", "EN_PROBADOR"):
            raise NoEncontrado(MSG_CODIGO)  # inexistente, de otra empresa, cancelada, completada o expirada
        if reserva.sucursal_id != self.sucursal_id:
            raise Conflicto("La reserva corresponde a otra sucursal.")
        return self.motor.salida([reserva])[0]

    def atender(self, reserva_id: int) -> ReservaOut:
        """Paso 4: se entregan las prendas y el cliente pasa a los vestidores."""
        reserva = self._propia(reserva_id)
        if reserva.estado not in ("PENDIENTE", "PREPARADA"):
            raise Conflicto("La reserva debe estar pendiente o preparada para atender al cliente.")
        self.motor.cambiar_estado(reserva, "EN_PROBADOR")
        self.db.commit()
        return self.motor.salida([reserva])[0]

    def completar(self, reserva_id: int, datos: schemas.CompletarIn) -> schemas.AtencionOut:
        """Paso 5. Si el cliente no lleva nada, la reserva se completa y el stock apartado vuelve a disponible.
        Si decide llevar las prendas, sigue en probador y se cobra con la venta presencial (CU-29)."""
        reserva = self._propia(reserva_id)
        if reserva.estado != "EN_PROBADOR":
            raise Conflicto("Primero debe atender al cliente (entregar las prendas).")
        if datos.llevara_prendas:
            return schemas.AtencionOut(reserva=self.motor.salida([reserva])[0], habilita_venta=True)
        self.motor.liberar(reserva, reserva.items, self.ctx.usuario.id, f"Reserva {reserva.codigo} completada sin compra")
        self.motor.cambiar_estado(reserva, "COMPLETADA")
        self.db.commit()
        return schemas.AtencionOut(reserva=self.motor.salida([reserva])[0], habilita_venta=False)

    def _propia(self, reserva_id: int) -> Reserva:
        self.motor.expirar_vencidas()
        reserva = self.motor.completa(reserva_id)
        if reserva is None or reserva.sucursal_id != self.sucursal_id:
            raise NoEncontrado("Reserva no encontrada.")
        return reserva

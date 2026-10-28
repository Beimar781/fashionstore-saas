"""RF11 · Notificaciones: avisos de reservas para la sucursal y para el cliente. Capa de negocio."""
from sqlalchemy.orm import Session

from app.core.constantes import ADMIN
from app.core.errors import NoEncontrado
from app.modules.acceso.dependencias import Contexto
from app.modules.reservas.models import Notificacion
from app.modules.reservas.rf11_notificaciones import schemas
from app.modules.reservas.rf11_notificaciones.repository import NotificacionRepository


def notificar(
    db: Session, empresa_id: int, tipo: str, titulo: str, mensaje: str, usuario_id: int | None = None,
    sucursal_id: int | None = None, referencia_tipo: str = "", referencia_id: int | None = None,
) -> None:
    """Deja un aviso para un usuario o, sin usuario, para toda la sucursal. No hace commit: va en la transacción del caso de uso."""
    NotificacionRepository(db, empresa_id).agregar(Notificacion(
        usuario_id=usuario_id, sucursal_id=sucursal_id, tipo=tipo, titulo=titulo, mensaje=mensaje,
        referencia_tipo=referencia_tipo, referencia_id=referencia_id,
    ))


class NotificacionService:
    def __init__(self, db: Session, ctx: Contexto):
        self.db = db
        self.repo = NotificacionRepository(db, ctx.empresa_id)
        # quién es: el Administrador ve los avisos de todas las sucursales; el resto, los suyos y los de su sucursal
        self.alcance = (ctx.usuario.id, ctx.sucursal_id, ctx.rol == ADMIN)

    def listar(self, solo_no_leidas: bool, limite: int) -> list[schemas.NotificacionOut]:
        return [schemas.NotificacionOut.model_validate(n) for n in self.repo.listar_visibles(*self.alcance, solo_no_leidas, limite)]

    def resumen(self) -> schemas.ResumenNotificaciones:
        return schemas.ResumenNotificaciones(no_leidas=self.repo.contar_no_leidas(*self.alcance))

    def marcar_leida(self, notificacion_id: int) -> schemas.NotificacionOut:
        n = self.repo.obtener_visible(notificacion_id, *self.alcance)
        if n is None:
            raise NoEncontrado("Notificación no encontrada.")  # también si es de otra empresa o de otra sucursal
        n.leida = True
        self.db.commit()
        return schemas.NotificacionOut.model_validate(n)

    def marcar_todas(self) -> schemas.ResumenNotificaciones:
        self.repo.marcar_todas(*self.alcance)
        self.db.commit()
        return self.resumen()

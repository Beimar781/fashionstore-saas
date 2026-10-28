from sqlalchemy import and_, func, or_, select, update

from app.core.tenant import TenantRepository
from app.modules.reservas.models import Notificacion


class NotificacionRepository(TenantRepository[Notificacion]):
    model = Notificacion

    def _visibles(self, usuario_id: int, sucursal_id: int | None, todas_las_sucursales: bool):
        """Las propias, las de su sucursal y, para el Administrador, las de cualquier sucursal."""
        condiciones = [Notificacion.usuario_id == usuario_id]
        if todas_las_sucursales:
            condiciones.append(and_(Notificacion.usuario_id.is_(None), Notificacion.sucursal_id.is_not(None)))
        elif sucursal_id is not None:
            condiciones.append(and_(Notificacion.usuario_id.is_(None), Notificacion.sucursal_id == sucursal_id))
        return or_(*condiciones)

    def listar_visibles(self, usuario_id, sucursal_id, todas, solo_no_leidas: bool, limite: int) -> list[Notificacion]:
        stmt = self._consulta().where(self._visibles(usuario_id, sucursal_id, todas))
        if solo_no_leidas:
            stmt = stmt.where(Notificacion.leida.is_(False))
        return list(self.db.scalars(stmt.order_by(Notificacion.creada_en.desc(), Notificacion.id.desc()).limit(limite)))

    def contar_no_leidas(self, usuario_id, sucursal_id, todas) -> int:
        stmt = select(func.count()).select_from(Notificacion).where(
            Notificacion.empresa_id == self.empresa_id, Notificacion.leida.is_(False), self._visibles(usuario_id, sucursal_id, todas)
        )
        return self.db.scalar(stmt) or 0

    def obtener_visible(self, notificacion_id: int, usuario_id, sucursal_id, todas) -> Notificacion | None:
        return self.db.scalar(self._consulta().where(Notificacion.id == notificacion_id, self._visibles(usuario_id, sucursal_id, todas)))

    def marcar_todas(self, usuario_id, sucursal_id, todas) -> None:
        self.db.execute(
            update(Notificacion).where(
                Notificacion.empresa_id == self.empresa_id, Notificacion.leida.is_(False), self._visibles(usuario_id, sucursal_id, todas)
            ).values(leida=True)
        )

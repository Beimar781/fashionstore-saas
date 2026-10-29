import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.core.tenant import TenantRepository
from app.modules.offline.models import OperacionOffline
from app.primer_parcial.catalogo.publico import Variante


class OperacionRepository(TenantRepository[OperacionOffline]):
    model = OperacionOffline

    def bloquear(self, operacion_id: uuid.UUID) -> None:
        """Dos envíos simultáneos de la misma operación se procesan de a uno (RNF05): el segundo ya encuentra el resultado del primero."""
        clave = (int.from_bytes(operacion_id.bytes[:8], "big") ^ self.empresa_id) & 0x7FFFFFFFFFFFFFFF
        self.db.execute(select(func.pg_advisory_xact_lock(clave)))

    def por_operacion(self, operacion_id: uuid.UUID, bloquear: bool = False) -> OperacionOffline | None:
        stmt = self._consulta().where(OperacionOffline.operacion_id == operacion_id).execution_options(populate_existing=True)
        return self.db.scalar(stmt.with_for_update() if bloquear else stmt)

    def con_id(self, id_: int) -> OperacionOffline | None:
        return self.db.scalar(self._consulta().where(OperacionOffline.id == id_).with_for_update().execution_options(populate_existing=True))

    def del_usuario(self, usuario_id: int, limite: int = 200) -> list[OperacionOffline]:
        stmt = self._consulta().where(OperacionOffline.usuario_id == usuario_id).order_by(OperacionOffline.creada_en_cliente.desc(), OperacionOffline.id.desc()).limit(limite)
        return list(self.db.scalars(stmt))

    def en_conflicto(self, sucursal_id: int | None) -> list[OperacionOffline]:
        stmt = self._consulta().where(OperacionOffline.estado == "EN_CONFLICTO").order_by(OperacionOffline.creada_en_cliente)
        if sucursal_id is not None:
            stmt = stmt.where(OperacionOffline.sucursal_id == sucursal_id)
        return list(self.db.scalars(stmt))

    def hay_conflictos(self, sucursal_id: int) -> bool:
        return self.db.scalar(select(OperacionOffline.id).where(
            OperacionOffline.empresa_id == self.empresa_id, OperacionOffline.sucursal_id == sucursal_id, OperacionOffline.estado == "EN_CONFLICTO").limit(1)) is not None

    def variantes(self, ids: set[int]) -> dict[int, Variante]:
        if not ids:
            return {}
        stmt = select(Variante).where(Variante.empresa_id == self.empresa_id, Variante.id.in_(ids)).options(selectinload(Variante.producto))
        return {v.id: v for v in self.db.scalars(stmt)}

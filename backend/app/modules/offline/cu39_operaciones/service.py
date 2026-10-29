"""CU-39 · Consultar operaciones y su estado de sincronización. Capa de negocio.

Los clientes (web y móvil) muestran primero lo que tienen guardado en el dispositivo (REGISTRADA_LOCAL y ENVIADA); aquí se consulta lo que el servidor ya procesó,
para que una operación que quedó en conflicto y luego se resolvió cambie de estado en el dispositivo.
"""
from sqlalchemy.orm import Session

from app.core.tiempo import ahora
from app.modules.acceso.dependencias import Contexto
from app.modules.offline import schemas
from app.modules.offline.mapeo import operaciones_out
from app.modules.offline.repository import OperacionRepository


class OperacionesService:
    def __init__(self, db: Session, ctx: Contexto):
        self.db = db
        self.ctx = ctx
        self.ops = OperacionRepository(db, ctx.empresa_id)

    def mias(self) -> list[schemas.OperacionOut]:
        """Las operaciones del usuario que ya llegaron al servidor, de la más reciente a la más antigua."""
        return operaciones_out(self.db, self.ctx.empresa_id, self.ops.del_usuario(self.ctx.usuario.id))

    def sincronizado_en(self):
        return ahora()

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.core.constantes import SUS_ACTIVA
from app.modules.plataforma.models import Empresa, Suscripcion


class EmpresaRepository:
    def __init__(self, db: Session):
        self.db = db

    def obtener(self, empresa_id: int) -> Empresa | None:
        return self.db.get(Empresa, empresa_id)

    def por_codigo(self, codigo: str) -> Empresa | None:
        return self.db.scalar(select(Empresa).where(func.upper(Empresa.codigo) == codigo.upper()))

    def existe_codigo_o_nit(self, codigo: str, nit: str, excluir_id: int | None = None) -> bool:
        stmt = select(Empresa.id).where(or_(func.upper(Empresa.codigo) == codigo.upper(), Empresa.nit == nit))
        if excluir_id is not None:
            stmt = stmt.where(Empresa.id != excluir_id)
        return self.db.scalar(stmt.limit(1)) is not None

    def existe_nit(self, nit: str, excluir_id: int) -> bool:
        return self.db.scalar(select(Empresa.id).where(Empresa.nit == nit, Empresa.id != excluir_id)) is not None

    def agregar(self, empresa: Empresa) -> Empresa:
        self.db.add(empresa)
        self.db.flush()
        return empresa

    def listar_con_suscripcion(self) -> list[tuple[Empresa, Suscripcion | None]]:
        """Empresas con su suscripción vigente (o la más reciente) en UNA consulta (DISTINCT ON), RNF09."""
        ids_ultimas = (
            select(Suscripcion.id)
            .distinct(Suscripcion.empresa_id)
            .order_by(Suscripcion.empresa_id, (Suscripcion.estado == SUS_ACTIVA).desc(), Suscripcion.id.desc())
        )
        stmt = (
            select(Empresa, Suscripcion)
            .outerjoin(Suscripcion, and_(Suscripcion.empresa_id == Empresa.id, Suscripcion.id.in_(ids_ultimas)))
            .order_by(Empresa.id)
        )
        return [(e, s) for e, s in self.db.execute(stmt)]

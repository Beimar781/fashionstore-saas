from datetime import datetime, time, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.tiempo import zona_local
from app.modules.plataforma.bitacora.models import Bitacora
from app.modules.plataforma.bitacora.schemas import Filtros
from app.modules.plataforma.models import Empresa


class BitacoraRepository:
    """Solo agrega y consulta: no existe ninguna operación para editar o borrar un registro. Con `empresa_id` solo ve lo de esa empresa (el Administrador);
    sin él ve todo (el SuperAdministrador, que además puede filtrar por empresa)."""

    def __init__(self, db: Session, empresa_id: int | None = None):
        self.db = db
        self.empresa_id = empresa_id

    def agregar(self, registro: Bitacora) -> Bitacora:
        self.db.add(registro)
        return registro

    def _filtrar(self, stmt, f: Filtros):
        if self.empresa_id is not None:
            stmt = stmt.where(Bitacora.empresa_id == self.empresa_id)  # el empresa_id sale del token, nunca de la petición
        elif f.empresa == "plataforma":
            stmt = stmt.where(Bitacora.empresa_id.is_(None))
        elif f.empresa and f.empresa.isdigit():
            stmt = stmt.where(Bitacora.empresa_id == int(f.empresa))
        if f.usuario:
            stmt = stmt.where(Bitacora.usuario == f.usuario)
        if f.entidad:
            stmt = stmt.where(Bitacora.entidad == f.entidad)
        if f.accion:
            stmt = stmt.where(Bitacora.accion == f.accion)
        if f.desde:
            stmt = stmt.where(Bitacora.creado_en >= datetime.combine(f.desde, time.min, tzinfo=zona_local()))
        if f.hasta:  # incluye todo el día
            stmt = stmt.where(Bitacora.creado_en < datetime.combine(f.hasta + timedelta(days=1), time.min, tzinfo=zona_local()))
        if f.q:
            patron = f"%{f.q.strip().lower()}%"
            stmt = stmt.where(or_(func.lower(Bitacora.detalle).like(patron), func.lower(func.coalesce(Bitacora.ip, "")).like(patron)))
        return stmt

    def buscar(self, f: Filtros) -> tuple[int, list[tuple[Bitacora, str | None]]]:
        total = self.db.scalar(self._filtrar(select(func.count(Bitacora.id)), f)) or 0
        stmt = (
            self._filtrar(select(Bitacora, Empresa.razon_social).join(Empresa, Empresa.id == Bitacora.empresa_id, isouter=True), f)
            .order_by(Bitacora.creado_en.desc(), Bitacora.id.desc()).offset((f.pagina - 1) * f.tamano).limit(f.tamano)
        )
        return int(total), [(b, e) for b, e in self.db.execute(stmt)]

    def usuarios(self) -> list[str]:
        stmt = select(Bitacora.usuario).distinct().order_by(Bitacora.usuario).limit(300)
        if self.empresa_id is not None:
            stmt = stmt.where(Bitacora.empresa_id == self.empresa_id)
        return list(self.db.scalars(stmt))

    def entidades(self) -> list[str]:
        stmt = select(Bitacora.entidad).distinct().order_by(Bitacora.entidad)
        if self.empresa_id is not None:
            stmt = stmt.where(Bitacora.empresa_id == self.empresa_id)
        return list(self.db.scalars(stmt))

    def empresas(self) -> list[tuple[int, str]]:
        return [(i, f"{c} · {r}") for i, c, r in self.db.execute(select(Empresa.id, Empresa.codigo, Empresa.razon_social).order_by(Empresa.codigo))]

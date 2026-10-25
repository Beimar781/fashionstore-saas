"""Aislamiento multitenant en la capa de repositorios (RN01, RN02, RNF02).

Todo repositorio de una entidad que pertenece a una empresa hereda de TenantRepository:
cada consulta lleva `empresa_id = <empresa del token>`, de modo que un recurso de otra
empresa simplemente "no existe" para el usuario (404) y nunca se revela su existencia.
"""
from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

T = TypeVar("T")


class TenantRepository(Generic[T]):
    model: type[T]

    def __init__(self, db: Session, empresa_id: int):
        if empresa_id is None:
            raise ValueError("Un repositorio de tenant requiere empresa_id")
        self.db = db
        self.empresa_id = empresa_id

    def _consulta(self):
        return select(self.model).where(self.model.empresa_id == self.empresa_id)  # type: ignore[attr-defined]

    def obtener(self, id_: int) -> T | None:
        return self.db.scalar(self._consulta().where(self.model.id == id_))  # type: ignore[attr-defined]

    def listar(self) -> list[T]:
        return list(self.db.scalars(self._consulta().order_by(self.model.id)))  # type: ignore[attr-defined]

    def agregar(self, entidad: T) -> T:
        entidad.empresa_id = self.empresa_id  # type: ignore[attr-defined]
        self.db.add(entidad)
        self.db.flush()
        return entidad

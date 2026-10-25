"""CU-34 · Gestionar planes de suscripción (RN04, RN06, RN07). Capa de negocio."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.constantes import SUS_ACTIVA
from app.core.errors import Conflicto, NoEncontrado
from app.modules.plataforma.cu34_planes import schemas
from app.modules.plataforma.cu34_planes.repository import PlanRepository
from app.modules.plataforma.models import Empresa, Plan, Suscripcion
from app.modules.sucursales.publico import contar_sucursales_activas


class PlanService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = PlanRepository(db)

    def listar(self) -> list[schemas.PlanOut]:
        out = []
        for plan, n in self.repo.listar_con_empresas_suscritas():
            item = schemas.PlanOut.model_validate(plan)
            item.empresas_suscritas = n
            out.append(item)
        return out

    def crear(self, datos: schemas.PlanCreate) -> schemas.PlanGuardadoOut:
        if self.repo.por_nombre(datos.nombre):
            raise Conflicto("Ya existe un plan con ese nombre.")
        plan = self.repo.agregar(Plan(**datos.model_dump()))
        self.db.commit()
        return schemas.PlanGuardadoOut(plan=self._salida(plan))

    def modificar(self, plan_id: int, datos: schemas.PlanUpdate) -> schemas.PlanGuardadoOut:
        plan = self._obtener(plan_id)
        cambios = datos.model_dump(exclude_unset=True)
        if "nombre" in cambios and cambios["nombre"] is not None:
            existente = self.repo.por_nombre(cambios["nombre"])
            if existente and existente.id != plan.id:
                raise Conflicto("Ya existe un plan con ese nombre.")
        for campo, valor in cambios.items():
            if valor is not None:
                setattr(plan, campo, valor)
        self.db.flush()
        advertencias = self._empresas_excedidas(plan)
        self.db.commit()
        return schemas.PlanGuardadoOut(plan=self._salida(plan), advertencias=advertencias)

    def inactivar(self, plan_id: int) -> schemas.PlanOut:
        """Un plan con empresas suscritas no se elimina: solo se inactiva para nuevas contrataciones;
        las suscripciones vigentes se mantienen."""
        plan = self._obtener(plan_id)
        plan.activo = False
        self.db.commit()
        return self._salida(plan)

    # ---- auxiliares ----
    def _obtener(self, plan_id: int) -> Plan:
        plan = self.repo.obtener(plan_id)
        if plan is None:
            raise NoEncontrado("Plan no encontrado.")
        return plan

    def _salida(self, plan: Plan) -> schemas.PlanOut:
        out = schemas.PlanOut.model_validate(plan)
        out.empresas_suscritas = self.repo.contar_empresas_suscritas(plan.id)
        return out

    def _empresas_excedidas(self, plan: Plan) -> list[schemas.EmpresaExcedida]:
        """Advierte qué empresas quedan por encima del nuevo límite; NO desactiva sucursales."""
        filas = self.db.execute(
            select(Empresa).join(Suscripcion, Suscripcion.empresa_id == Empresa.id).where(
                Suscripcion.plan_id == plan.id, Suscripcion.estado == SUS_ACTIVA
            )
        ).scalars()
        excedidas = []
        for emp in filas:
            activas = contar_sucursales_activas(self.db, emp.id)
            if activas > plan.max_sucursales:
                excedidas.append(
                    schemas.EmpresaExcedida(
                        empresa_id=emp.id, codigo=emp.codigo, sucursales_activas=activas, limite=plan.max_sucursales
                    )
                )
        return excedidas

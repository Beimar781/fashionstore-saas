"""CU-35 · Gestionar suscripciones de empresas (RN04, RN05, RN06, RN07, RN08, RN18). Capa de negocio."""
from calendar import monthrange
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.constantes import (
    EMPRESA_ACTIVA,
    SUS_ACTIVA,
    SUS_VENCIDA,
)
from app.core.errors import Conflicto, DatosInvalidos, NoEncontrado
from app.modules.plataforma.cu34_planes.repository import PlanRepository
from app.modules.plataforma.cu35_suscripciones import schemas
from app.modules.plataforma.cu35_suscripciones.repository import SuscripcionRepository
from app.modules.plataforma.models import Empresa, Plan, Suscripcion
from app.modules.sucursales.publico import contar_sucursales_activas


def sumar_meses(inicio: date, meses: int) -> date:
    mes0 = inicio.month - 1 + meses
    anio, mes = inicio.year + mes0 // 12, mes0 % 12 + 1
    return date(anio, mes, min(inicio.day, monthrange(anio, mes)[1]))


def resolver_vigencia(inicio: date, vencimiento: date | None, duracion_meses: int | None) -> date:
    """Calcula/valida la fecha de vencimiento (la duración puede indicarse en lugar de la fecha)."""
    if vencimiento is None and duracion_meses is None:
        raise DatosInvalidos("Indique la fecha de vencimiento o la duración de la suscripción.")
    if vencimiento is None:
        vencimiento = sumar_meses(inicio, duracion_meses)  # type: ignore[arg-type]
    if vencimiento <= inicio:
        raise DatosInvalidos("La fecha de vencimiento debe ser posterior a la de inicio.")
    return vencimiento


def calcular_monto(plan: Plan, inicio: date, vencimiento: date) -> Decimal:
    """Monto referencial (la contratación es simulada, RN18): precio × períodos."""
    if plan.periodicidad == "anual":
        periodos = max(1, round(((vencimiento - inicio).days) / 365))
    else:
        periodos = max(1, round(((vencimiento - inicio).days) / 30))
    return (plan.precio * periodos).quantize(Decimal("0.01"))


class SuscripcionService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = SuscripcionRepository(db)
        self.planes = PlanRepository(db)

    # ---- consulta ----
    def detalle(self, empresa_id: int) -> schemas.SuscripcionDetalleOut:
        self._empresa(empresa_id)
        if self.repo.marcar_vencidas(empresa_id):
            self.db.commit()
        vigente = self.repo.ultima(empresa_id)
        if vigente is not None and vigente.estado != SUS_ACTIVA:
            # Si no hay una Activa, se muestra la más reciente como estado actual
            pass
        historial = self.repo.historial(empresa_id)
        limite = vigente.plan.max_sucursales if vigente else None
        return schemas.SuscripcionDetalleOut(
            vigente=schemas.SuscripcionOut.model_validate(vigente) if vigente else None,
            historial=[schemas.SuscripcionOut.model_validate(s) for s in historial],
            uso=schemas.UsoPlan(sucursales_activas=contar_sucursales_activas(self.db, empresa_id), limite=limite),
        )

    # ---- asignar / cambiar / renovar ----
    def asignar(self, empresa_id: int, datos: schemas.SuscripcionIn) -> schemas.SuscripcionOut:
        empresa = self._empresa(empresa_id)
        if empresa.estado != EMPRESA_ACTIVA:
            raise Conflicto("La empresa está suspendida o cancelada. Reactívela antes de asignar un plan.")
        plan = self._plan_contratable(datos.plan_id)
        vencimiento = resolver_vigencia(datos.fecha_inicio, datos.fecha_vencimiento, datos.duracion_meses)
        self.verificar_cobertura_plan(empresa_id, plan)  # RN08

        anterior = self.repo.vigente(empresa_id)
        if anterior is not None:
            self.repo.cerrar(anterior, SUS_VENCIDA)  # se cierra la vigencia anterior; queda en el historial
        nueva = self.crear_registro(empresa_id, plan, datos.fecha_inicio, vencimiento, datos.forma_pago)
        self.db.commit()
        self.repo.marcar_vencidas(empresa_id)  # si las fechas ya pasaron, queda Vencida (RN05)
        self.db.commit()
        return schemas.SuscripcionOut.model_validate(nueva)

    def crear_registro(
        self, empresa_id: int, plan: Plan, inicio: date, vencimiento: date, forma_pago: str | None
    ) -> Suscripcion:
        """Inserta la suscripción (reutilizado por CU-33 al registrar la empresa, sin hacer commit)."""
        return self.repo.agregar(
            Suscripcion(
                empresa_id=empresa_id,
                plan_id=plan.id,
                fecha_inicio=inicio,
                fecha_vencimiento=vencimiento,
                estado=SUS_ACTIVA,
                forma_pago=forma_pago,
                monto=calcular_monto(plan, inicio, vencimiento),
            )
        )

    def verificar_cobertura_plan(self, empresa_id: int, plan: Plan) -> None:
        """RN08: el límite del plan debe cubrir las sucursales activas de la empresa."""
        activas = contar_sucursales_activas(self.db, empresa_id)
        if activas > plan.max_sucursales:
            raise Conflicto(
                f"La empresa tiene {activas} sucursales activas; el plan elegido permite "
                f"{plan.max_sucursales}. Desactive sucursales antes de cambiar."
            )

    # ---- suspender / cancelar ----
    def cambiar_estado(self, empresa_id: int, estado: str) -> schemas.SuscripcionOut:
        self._empresa(empresa_id)
        vigente = self.repo.vigente(empresa_id)
        if vigente is None:
            raise Conflicto("La empresa no tiene una suscripción activa.")
        self.repo.cerrar(vigente, estado)
        self.db.commit()
        return schemas.SuscripcionOut.model_validate(vigente)

    # ---- auxiliares ----
    def _empresa(self, empresa_id: int) -> Empresa:
        empresa = self.db.get(Empresa, empresa_id)
        if empresa is None:
            raise NoEncontrado("Empresa no encontrada.")
        return empresa

    def _plan_contratable(self, plan_id: int) -> Plan:
        plan = self.planes.obtener(plan_id)
        if plan is None:
            raise NoEncontrado("Plan no encontrado.")
        if not plan.activo:
            raise Conflicto("El plan no está disponible para nuevas contrataciones.")
        return plan

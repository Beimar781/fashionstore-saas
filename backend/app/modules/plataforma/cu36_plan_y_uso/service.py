"""CU-36 · Plan, límites y uso de la empresa. Capa de negocio.

Lo ve el Administrador aunque la suscripción haya vencido (RN05: es lo único habilitado); en ese caso solo se muestra el plan y la vigencia.
Los consumos (usuarios, productos, ventas, consultas de IA) los miden los demás paquetes y se anotan en el registro de medidores de `publico.py`.
"""
from sqlalchemy.orm import Session

from app.core.constantes import SUS_ACTIVA
from app.core.tiempo import ahora, a_local
from app.modules.acceso.dependencias import Contexto
from app.modules.plataforma import publico
from app.modules.plataforma.cu36_plan_y_uso import schemas
from app.modules.sucursales.publico import contar_sucursales_activas

FUNCIONALIDADES = (
    ("reportes_convencionales", "Reportes de ventas, reservas y pagos e indicadores"),
    ("offline", "Operación sin conexión"),
    ("reportes_ia", "Reportes generativos, asistente y analítica con IA"),
)
AVISO_VENCIMIENTO_DIAS = 15


class PlanYUsoService:
    def __init__(self, db: Session, ctx: Contexto):
        self.db = db
        self.empresa_id = ctx.empresa_id

    def detalle(self) -> schemas.MiPlanOut:
        sus = publico.suscripcion_de(self.db, self.empresa_id)
        if sus is None:
            return schemas.MiPlanOut(plan=None, vigencia=None, limites=[], consumo=[], funcionalidades=[], alertas=["Su empresa todavía no tiene un plan asignado."])
        plan, vigente = sus.plan, sus.estado == SUS_ACTIVA
        hoy = a_local(ahora()).date()
        dias = max((sus.fecha_vencimiento - hoy).days, 0) if vigente else None
        alertas = [] if vigente else [f"La suscripción está {sus.estado.lower()}: solo puede consultar su plan hasta que se renueve."]
        if vigente and dias is not None and dias <= AVISO_VENCIMIENTO_DIAS:
            alertas.append(f"Su suscripción vence en {dias} día(s). Pida su renovación al administrador de la plataforma.")

        limites, consumo = [], []
        if vigente:
            usadas = contar_sucursales_activas(self.db, self.empresa_id)
            limites.append(schemas.LimiteOut(
                clave="sucursales", etiqueta="Sucursales activas", usado=usadas, limite=plan.max_sucursales,
                porcentaje=round(usadas / plan.max_sucursales * 100, 1) if plan.max_sucursales else None, alcanzado=usadas >= plan.max_sucursales,
            ))
            if usadas >= plan.max_sucursales:
                alertas.append(f"Alcanzó el límite de {plan.max_sucursales} sucursales activas de su plan.")
            consumo = [schemas.ConsumoOut(clave=c, etiqueta=e, valor=int(medir(self.db, self.empresa_id))) for c, e, medir in publico.medidores()]
        return schemas.MiPlanOut(
            plan=schemas.PlanDetalleOut(id=plan.id, nombre=plan.nombre, descripcion=plan.descripcion, precio=plan.precio, periodicidad=plan.periodicidad),
            vigencia=schemas.VigenciaOut(estado=sus.estado, fecha_inicio=sus.fecha_inicio, fecha_vencimiento=sus.fecha_vencimiento, dias_restantes=dias, vigente=vigente),
            limites=limites, consumo=consumo,
            funcionalidades=[schemas.FuncionalidadOut(clave=c, etiqueta=e, incluida=bool(getattr(plan, c, False))) for c, e in FUNCIONALIDADES], alertas=alertas,
        )

"""Interfaz pública del paquete P1 (Plataforma SaaS).

Los demás paquetes consultan aquí la vigencia de la suscripción, los límites del plan y las
funcionalidades habilitadas (RN05, RN06, RN07), sin conocer los detalles internos de P1.
"""
from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.constantes import EMPRESA_ACTIVA, MSG_EMPRESA_INACTIVA, MSG_SUSCRIPCION_NO_VIGENTE, SUS_ACTIVA, SUPERADMIN
from app.core.database import get_db
from app.core.errors import Prohibido
from app.modules.acceso.dependencias import Contexto, get_contexto
from app.modules.plataforma.cu35_suscripciones.repository import SuscripcionRepository
from app.modules.plataforma.models import Empresa, Suscripcion


def suscripcion_de(db: Session, empresa_id: int) -> Suscripcion | None:
    """Suscripción vigente de la empresa o, si no hay, la más reciente. Aplica el vencimiento
    automático (RN05) antes de responder."""
    repo = SuscripcionRepository(db)
    if repo.marcar_vencidas(empresa_id):
        db.commit()
    return repo.ultima(empresa_id)


def suscripcion_activa_de(db: Session, empresa_id: int) -> Suscripcion | None:
    sus = suscripcion_de(db, empresa_id)
    return sus if sus and sus.estado == SUS_ACTIVA else None


def contexto_operativo(*roles: str):
    """Dependencia para operaciones de empresa: verifica rol, que la empresa esté activa y que su
    suscripción esté vigente (RN05). Si no, bloquea la operación con el mensaje de la ficha de CU."""

    def _dep(ctx: Contexto = Depends(get_contexto), db: Session = Depends(get_db)) -> Contexto:
        if ctx.rol not in roles:
            raise Prohibido("No tiene permisos para esta operación.")
        if ctx.empresa_id is None:
            raise Prohibido("Esta operación pertenece a una empresa.")
        empresa = db.get(Empresa, ctx.empresa_id)
        if empresa is None or empresa.estado != EMPRESA_ACTIVA:
            raise Prohibido(MSG_EMPRESA_INACTIVA)
        if suscripcion_activa_de(db, ctx.empresa_id) is None:
            raise Prohibido(MSG_SUSCRIPCION_NO_VIGENTE)
        return ctx

    return _dep


def exigir_funcionalidad(nombre: str):
    """RN07: bloquea la operación si el plan contratado no habilita la funcionalidad
    (por ejemplo `reportes_ia`). Se usa como dependencia en los endpoints que la requieran."""

    def _dep(ctx: Contexto = Depends(get_contexto), db: Session = Depends(get_db)) -> Contexto:
        if ctx.rol == SUPERADMIN or ctx.empresa_id is None:
            raise Prohibido("Esta funcionalidad pertenece a una empresa.")
        sus = suscripcion_activa_de(db, ctx.empresa_id)
        if sus is None:
            raise Prohibido(MSG_SUSCRIPCION_NO_VIGENTE)
        if not getattr(sus.plan, nombre, False):
            raise Prohibido("Su plan no incluye esta funcionalidad. Cambie al plan Profesional.")
        return ctx

    return _dep

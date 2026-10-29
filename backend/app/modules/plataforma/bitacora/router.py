"""Consulta de la bitácora. Solo lectura: no existe ningún endpoint para editar ni borrar registros.
El Administrador ve únicamente la de su empresa; el SuperAdministrador ve la de todas las empresas. Encargado, Cajero y Cliente no tienen acceso."""
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.constantes import ADMIN, SUPERADMIN
from app.core.database import get_db
from app.modules.acceso.dependencias import Contexto, requerir_roles
from app.modules.plataforma.bitacora import schemas
from app.modules.plataforma.bitacora.service import BitacoraService
from app.modules.plataforma.publico import contexto_operativo

router = APIRouter(prefix="/bitacora", tags=["Bitácora de la empresa"])
router_plataforma = APIRouter(prefix="/plataforma/bitacora", tags=["Bitácora general de la plataforma"])


def _filtros(
    usuario: str | None = None, entidad: str | None = None, accion: str | None = None, desde: date | None = None, hasta: date | None = None,
    q: str | None = Query(default=None, max_length=100), empresa: str | None = None, pagina: int = 1, tamano: int = 25,
) -> schemas.Filtros:
    return schemas.Filtros(usuario=usuario or None, entidad=entidad or None, accion=accion or None, desde=desde, hasta=hasta, q=q or None, empresa=empresa or None, pagina=pagina, tamano=tamano)


@router.get("", response_model=schemas.PaginaBitacoraOut)
def bitacora_de_la_empresa(f: schemas.Filtros = Depends(_filtros), ctx: Contexto = Depends(contexto_operativo(ADMIN)), db: Session = Depends(get_db)):
    """Operaciones registradas en la empresa del Administrador, de la más reciente a la más antigua."""
    f.empresa = None  # el empresa_id sale del token, nunca de la petición
    return BitacoraService(db, ctx.empresa_id).consultar(f)


@router.get("/opciones", response_model=schemas.OpcionesOut)
def opciones_de_la_empresa(ctx: Contexto = Depends(contexto_operativo(ADMIN)), db: Session = Depends(get_db)):
    return BitacoraService(db, ctx.empresa_id).opciones()


@router_plataforma.get("", response_model=schemas.PaginaBitacoraOut)
def bitacora_general(f: schemas.Filtros = Depends(_filtros), ctx: Contexto = Depends(requerir_roles(SUPERADMIN)), db: Session = Depends(get_db)):
    """Operaciones de todas las empresas juntas (con filtro por empresa o «plataforma») y las propias de la plataforma."""
    return BitacoraService(db, None).consultar(f)


@router_plataforma.get("/opciones", response_model=schemas.OpcionesOut)
def opciones_generales(ctx: Contexto = Depends(requerir_roles(SUPERADMIN)), db: Session = Depends(get_db)):
    return BitacoraService(db, None).opciones()

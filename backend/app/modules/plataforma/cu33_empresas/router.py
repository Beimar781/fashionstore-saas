from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.constantes import SUPERADMIN
from app.core.database import get_db
from app.modules.acceso.dependencias import requerir_roles
from app.modules.plataforma.cu33_empresas import schemas
from app.modules.plataforma.cu33_empresas.service import EmpresaService

router = APIRouter(prefix="/plataforma/empresas", tags=["CU-33 Empresas (tenants)"], dependencies=[Depends(requerir_roles(SUPERADMIN))])


@router.get("", response_model=list[schemas.EmpresaOut])
def listar_empresas(db: Session = Depends(get_db)):
    return EmpresaService(db).listar()


@router.post("", response_model=schemas.EmpresaRegistradaOut, status_code=201)
def registrar_empresa(datos: schemas.EmpresaCreate, db: Session = Depends(get_db)):
    return EmpresaService(db).registrar(datos)


@router.put("/{empresa_id}", response_model=schemas.EmpresaOut)
def editar_empresa(empresa_id: int, datos: schemas.EmpresaUpdate, db: Session = Depends(get_db)):
    return EmpresaService(db).editar(empresa_id, datos)


@router.post("/{empresa_id}/suspender", response_model=schemas.EmpresaOut)
def suspender_empresa(empresa_id: int, db: Session = Depends(get_db)):
    return EmpresaService(db).suspender(empresa_id)


@router.post("/{empresa_id}/reactivar", response_model=schemas.EmpresaOut)
def reactivar_empresa(empresa_id: int, db: Session = Depends(get_db)):
    return EmpresaService(db).reactivar(empresa_id)


@router.delete("/{empresa_id}", status_code=409, include_in_schema=True)
def eliminar_empresa(empresa_id: int, db: Session = Depends(get_db)):
    """Las empresas con datos no se eliminan: solo baja lógica (suspensión o cancelación)."""
    EmpresaService(db).eliminar(empresa_id)

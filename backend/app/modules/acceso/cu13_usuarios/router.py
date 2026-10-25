from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.constantes import ADMIN
from app.core.database import get_db
from app.modules.acceso.cu13_usuarios import schemas
from app.modules.acceso.cu13_usuarios.service import UsuarioService
from app.modules.acceso.dependencias import Contexto
from app.modules.plataforma.publico import contexto_operativo

router = APIRouter(prefix="/usuarios", tags=["CU-13 Usuarios y roles"])
solo_admin = contexto_operativo(ADMIN)


@router.get("", response_model=list[schemas.UsuarioOut])
def listar_usuarios(ctx: Contexto = Depends(solo_admin), db: Session = Depends(get_db)):
    return UsuarioService(db, ctx.empresa_id).listar()


@router.post("", response_model=schemas.UsuarioOut, status_code=201)
def registrar_usuario(datos: schemas.UsuarioCreate, ctx: Contexto = Depends(solo_admin), db: Session = Depends(get_db)):
    return UsuarioService(db, ctx.empresa_id).registrar(datos)


@router.put("/{usuario_id}", response_model=schemas.UsuarioOut)
def editar_usuario(usuario_id: int, datos: schemas.UsuarioUpdate, ctx: Contexto = Depends(solo_admin), db: Session = Depends(get_db)):
    return UsuarioService(db, ctx.empresa_id).editar(usuario_id, datos)


@router.post("/{usuario_id}/desactivar", response_model=schemas.UsuarioOut)
def desactivar_usuario(usuario_id: int, ctx: Contexto = Depends(solo_admin), db: Session = Depends(get_db)):
    return UsuarioService(db, ctx.empresa_id).desactivar(usuario_id)

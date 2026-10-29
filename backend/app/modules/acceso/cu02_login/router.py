from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.acceso.cu02_login import schemas
from app.modules.acceso.cu02_login.service import AutenticacionService
from app.modules.acceso.dependencias import Contexto, get_contexto

router = APIRouter(prefix="/auth", tags=["CU-02 Iniciar sesión"])


@router.post("/login", response_model=schemas.TokenOut)
def login(datos: schemas.LoginIn, db: Session = Depends(get_db)):
    """Inicia sesión con código de empresa, correo y contraseña (el SuperAdministrador omite el código)."""
    return AutenticacionService(db).iniciar_sesion(datos)


@router.post("/refresh", response_model=schemas.TokenOut)
def refresh(datos: schemas.RefreshIn, db: Session = Depends(get_db)):
    return AutenticacionService(db).renovar(datos.refresh_token)


@router.post("/logout", response_model=schemas.MensajeOut)
def cerrar_sesion(ctx: Contexto = Depends(get_contexto)):
    """Los tokens no tienen estado en el servidor: el cliente los descarta. Esta llamada deja constancia del cierre en la bitácora."""
    return schemas.MensajeOut(detail="Sesión cerrada.")


@router.get("/me", response_model=schemas.SesionOut)
def me(ctx: Contexto = Depends(get_contexto), db: Session = Depends(get_db)):
    return AutenticacionService(db).sesion_actual(ctx)


@router.post("/olvide-password", response_model=schemas.MensajeOut)
def olvide_password(datos: schemas.OlvidePasswordIn, db: Session = Depends(get_db)):
    """Envía al correo un enlace de un solo uso para restablecer la contraseña (respuesta siempre genérica)."""
    return AutenticacionService(db).solicitar_restablecimiento(datos)


@router.post("/restablecer-password", response_model=schemas.MensajeOut)
def restablecer_password(datos: schemas.RestablecerPasswordIn, db: Session = Depends(get_db)):
    return AutenticacionService(db).restablecer_password(datos)

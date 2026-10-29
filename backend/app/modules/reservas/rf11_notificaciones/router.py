from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.constantes import ADMIN, CAJERO, CLIENTE, ENCARGADO, PROVEEDOR
from app.core.database import get_db
from app.core.config import get_settings
from app.modules.acceso.dependencias import Contexto
from app.modules.plataforma.publico import contexto_operativo
from app.modules.reservas.rf11_notificaciones import push, schemas
from app.modules.reservas.rf11_notificaciones.service import NotificacionService

router = APIRouter(prefix="/notificaciones", tags=["RF11 Notificaciones"])
cualquier_rol = contexto_operativo(ADMIN, ENCARGADO, CAJERO, CLIENTE, PROVEEDOR)


@router.get("", response_model=list[schemas.NotificacionOut])
def listar_notificaciones(
    solo_no_leidas: bool = False, limite: int = Query(50, ge=1, le=200), ctx: Contexto = Depends(cualquier_rol), db: Session = Depends(get_db)
):
    """Avisos propios, los de la sucursal del Encargado o Cajero y, para el Administrador, los de todas las sucursales."""
    return NotificacionService(db, ctx).listar(solo_no_leidas, limite)


@router.get("/resumen", response_model=schemas.ResumenNotificaciones)
def cuantas_sin_leer(ctx: Contexto = Depends(cualquier_rol), db: Session = Depends(get_db)):
    return NotificacionService(db, ctx).resumen()


@router.post("/leer-todas", response_model=schemas.ResumenNotificaciones)
def marcar_todas_leidas(ctx: Contexto = Depends(cualquier_rol), db: Session = Depends(get_db)):
    return NotificacionService(db, ctx).marcar_todas()


@router.post("/{notificacion_id}/leer", response_model=schemas.NotificacionOut)
def marcar_leida(notificacion_id: int, ctx: Contexto = Depends(cualquier_rol), db: Session = Depends(get_db)):
    return NotificacionService(db, ctx).marcar_leida(notificacion_id)


@router.get("/push/config", response_model=schemas.ConfigPush)
def configuracion_push(ctx: Contexto = Depends(cualquier_rol)):
    cfg = get_settings()
    return schemas.ConfigPush(vapid_public_key=cfg.vapid_public_key if cfg.vapid_activo else "", web_real=cfg.vapid_activo, movil_real=cfg.fcm_activo)


@router.post("/dispositivos", response_model=schemas.DispositivoOut, status_code=status.HTTP_201_CREATED)
def registrar_dispositivo(datos: schemas.DispositivoIn, ctx: Contexto = Depends(cualquier_rol), db: Session = Depends(get_db)):
    """Registra el navegador o el móvil del usuario para recibir avisos push (si ya estaba, lo reactiva)."""
    return push.registrar_dispositivo(db, ctx.empresa_id, ctx.usuario.id, datos.canal, datos.token)


@router.post("/dispositivos/baja", status_code=status.HTTP_204_NO_CONTENT)
def quitar_dispositivo(datos: schemas.DispositivoIn, ctx: Contexto = Depends(cualquier_rol), db: Session = Depends(get_db)):
    """El usuario deja de recibir avisos en ese dispositivo (al cerrar sesión o al revocar el permiso)."""
    push.quitar_dispositivo(db, ctx.empresa_id, ctx.usuario.id, datos.canal, datos.token)

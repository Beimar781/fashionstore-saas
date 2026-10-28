from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.core.constantes import CLIENTE
from app.core.database import get_db
from app.modules.acceso.dependencias import Contexto
from app.modules.plataforma.publico import contexto_operativo
from app.primer_parcial.ventas.cu32_pago_electronico import schemas
from app.primer_parcial.ventas.cu32_pago_electronico.pasarela import obtener_pasarela
from app.primer_parcial.ventas.cu32_pago_electronico.service import PagoService

router = APIRouter(prefix="/pagos", tags=["CU-32 Pago electrónico"])
solo_cliente = contexto_operativo(CLIENTE)


def _servicio(ctx: Contexto, db: Session, pasarela) -> PagoService:
    return PagoService(db, ctx, pasarela)


@router.get("/config", response_model=schemas.ConfigPagoOut)
def configuracion_de_pago(ctx: Contexto = Depends(solo_cliente), db: Session = Depends(get_db), pasarela=Depends(obtener_pasarela)):
    """Modo de pago (Stripe de prueba o simulado), clave pública y, si es simulado, las tarjetas de prueba."""
    return _servicio(ctx, db, pasarela).config()


@router.get("/tarjetas", response_model=list[schemas.TarjetaGuardadaOut])
def mis_tarjetas_guardadas(ctx: Contexto = Depends(solo_cliente), db: Session = Depends(get_db), pasarela=Depends(obtener_pasarela)):
    return _servicio(ctx, db, pasarela).listar_tarjetas()


@router.delete("/tarjetas/{tarjeta_id}", status_code=204)
def eliminar_tarjeta_guardada(tarjeta_id: int, ctx: Contexto = Depends(solo_cliente), db: Session = Depends(get_db), pasarela=Depends(obtener_pasarela)):
    _servicio(ctx, db, pasarela).eliminar_tarjeta(tarjeta_id)
    return Response(status_code=204)


@router.post("/pedidos/{pedido_id}/iniciar", response_model=schemas.IniciarOut, status_code=201)
def iniciar_pago(pedido_id: int, datos: schemas.IniciarIn, ctx: Contexto = Depends(solo_cliente), db: Session = Depends(get_db), pasarela=Depends(obtener_pasarela)):
    """Consolida el monto del pedido y crea el intento de pago en la pasarela."""
    return _servicio(ctx, db, pasarela).iniciar(pedido_id, datos)


@router.post("/{pago_id}/confirmar", response_model=schemas.ResultadoPagoOut)
def confirmar_pago(pago_id: int, datos: schemas.ConfirmarIn, ctx: Contexto = Depends(solo_cliente), db: Session = Depends(get_db), pasarela=Depends(obtener_pasarela)):
    """Lee la respuesta de la pasarela: aprobado (descuenta el stock y cobra), rechazado (402) o pendiente de confirmación."""
    return _servicio(ctx, db, pasarela).confirmar(pago_id, datos)


@router.post("/{pago_id}/reconciliar", response_model=schemas.ResultadoPagoOut)
def reconciliar_pago(pago_id: int, ctx: Contexto = Depends(solo_cliente), db: Session = Depends(get_db), pasarela=Depends(obtener_pasarela)):
    return _servicio(ctx, db, pasarela).reconciliar(pago_id)


@router.get("/{pago_id}", response_model=schemas.ResultadoPagoOut)
def estado_del_pago(pago_id: int, ctx: Contexto = Depends(solo_cliente), db: Session = Depends(get_db), pasarela=Depends(obtener_pasarela)):
    return _servicio(ctx, db, pasarela).obtener(pago_id)

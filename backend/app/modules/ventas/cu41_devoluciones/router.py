from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.core.constantes import ADMIN, CAJERO, ENCARGADO
from app.core.database import get_db
from app.core.tiempo import zona_local
from app.modules.acceso.dependencias import Contexto
from app.modules.plataforma.publico import contexto_operativo
from app.modules.ventas.cu41_devoluciones import schemas
from app.modules.ventas.cu41_devoluciones.service import DevolucionService

router = APIRouter(prefix="/devoluciones", tags=["CU-41 Devoluciones y cambios"])
en_caja = contexto_operativo(CAJERO, ENCARGADO)  # registran las devoluciones de su sucursal
consulta = contexto_operativo(ADMIN, CAJERO, ENCARGADO)
solo_admin = contexto_operativo(ADMIN)


def _dia(fecha: date | None, fin: bool = False):
    return None if fecha is None else datetime.combine(fecha + timedelta(days=1 if fin else 0), time.min, tzinfo=zona_local())


@router.get("/configuracion", response_model=schemas.ConfiguracionOut)
def plazo_de_devolucion(ctx: Contexto = Depends(consulta), db: Session = Depends(get_db)):
    """Días, desde el pago, dentro de los que se acepta una devolución o cambio (lo define cada empresa)."""
    return DevolucionService(db, ctx).plazo()


@router.put("/configuracion", response_model=schemas.ConfiguracionOut)
def fijar_plazo_de_devolucion(datos: schemas.ConfiguracionIn, ctx: Contexto = Depends(solo_admin), db: Session = Depends(get_db)):
    return DevolucionService(db, ctx).fijar_plazo(datos.plazo_dias)


@router.get("/venta", response_model=schemas.VentaDevolvibleOut)
def buscar_la_venta_por_comprobante(comprobante: str = "", ctx: Contexto = Depends(en_caja), db: Session = Depends(get_db)):
    """La venta que el cliente quiere devolver o cambiar: lo ya devuelto, el plazo y cómo se pagó."""
    return DevolucionService(db, ctx).venta(comprobante)


@router.post("/diferencia", response_model=schemas.DiferenciaOut, status_code=201)
def iniciar_cobro_con_tarjeta_de_la_diferencia(datos: schemas.DevolucionIn, ctx: Contexto = Depends(en_caja), db: Session = Depends(get_db)):
    """Cambio que vale más y se paga con tarjeta: el servidor calcula la diferencia y la pide a la pasarela (mismo flujo que el pago del CU-32)."""
    return DevolucionService(db, ctx).iniciar_diferencia(datos)


@router.post("", response_model=schemas.DevolucionOut, status_code=201)
def registrar_devolucion_o_cambio(datos: schemas.DevolucionIn, ctx: Contexto = Depends(en_caja), db: Session = Depends(get_db)):
    """Registra la devolución (total o parcial) o el cambio: la prenda vuelve al inventario de la sucursal y se emite la nota."""
    return DevolucionService(db, ctx).registrar(datos)


@router.get("", response_model=list[schemas.DevolucionOut])
def listar_devoluciones(
    desde: date | None = None, hasta: date | None = None, sucursal: int | None = None, ctx: Contexto = Depends(consulta), db: Session = Depends(get_db)
):
    return DevolucionService(db, ctx).listar(sucursal, _dia(desde), _dia(hasta, fin=True))


@router.get("/{devolucion_id}", response_model=schemas.DevolucionOut)
def consultar_devolucion(devolucion_id: int, ctx: Contexto = Depends(consulta), db: Session = Depends(get_db)):
    return DevolucionService(db, ctx).obtener(devolucion_id)


@router.get("/{devolucion_id}/nota")
def descargar_nota_de_devolucion(devolucion_id: int, ctx: Contexto = Depends(consulta), db: Session = Depends(get_db)):
    pdf, nombre = DevolucionService(db, ctx).nota(devolucion_id)
    return Response(pdf, media_type="application/pdf", headers={"Content-Disposition": f'inline; filename="{nombre}"'})

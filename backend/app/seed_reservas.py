"""Datos de ejemplo de reservas (Fase C): el cliente demo de cada empresa reserva en su primera sucursal. Idempotente."""
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.constantes import CLIENTE
from app.core.tiempo import a_local, ahora
from app.modules.acceso.dependencias import Contexto
from app.modules.acceso.models import Usuario
from app.modules.inventario.models import Existencia
from app.modules.reservas.cu09_reservar.schemas import ItemIn, ReservaIn
from app.modules.reservas.cu09_reservar.service import ReservaService
from app.modules.reservas.models import Reserva
from app.modules.sucursales.models import Sucursal


def cargar(db: Session, empresa) -> None:
    if db.scalar(select(Reserva.id).where(Reserva.empresa_id == empresa.id).limit(1)):
        return
    cliente = db.scalar(select(Usuario).where(Usuario.empresa_id == empresa.id, Usuario.email == f"cliente@{empresa.codigo.lower()}.com"))
    sucursal = db.scalar(select(Sucursal).where(Sucursal.empresa_id == empresa.id, Sucursal.activa.is_(True)).order_by(Sucursal.id).limit(1))
    if cliente is None or sucursal is None:
        return
    # prendas con stock en esa sucursal
    variantes = list(db.scalars(
        select(Existencia.variante_id).where(Existencia.sucursal_id == sucursal.id, Existencia.disponible >= 3).order_by(Existencia.variante_id).limit(4)
    ))
    if len(variantes) < 3:
        return
    ctx = Contexto(cliente, CLIENTE, empresa.id, None)
    servicio = ReservaService(db, empresa.id)
    manana = (a_local(ahora()) + timedelta(days=1)).replace(hour=11, minute=0, second=0, microsecond=0)
    servicio.crear(ctx, ReservaIn(
        sucursal_id=sucursal.id, programada_para=manana, notas="Quiero probármelas juntas",
        items=[ItemIn(variante_id=variantes[0], cantidad=1), ItemIn(variante_id=variantes[1], cantidad=2)],
    ))
    preparada = servicio.crear(ctx, ReservaIn(
        sucursal_id=sucursal.id, programada_para=manana + timedelta(days=1, hours=4),
        items=[ItemIn(variante_id=variantes[2], cantidad=1)],
    ))
    reserva = servicio.completa(preparada.id)
    servicio.cambiar_estado(reserva, "PREPARADA")
    db.commit()

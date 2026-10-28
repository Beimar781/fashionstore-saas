from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.constantes import ADMIN, PROVEEDOR
from app.core.database import get_db
from app.modules.acceso.dependencias import Contexto
from app.modules.plataforma.publico import contexto_operativo
from app.primer_parcial.proveedores.cu15_proveedores.schemas import ProveedorOut
from app.primer_parcial.proveedores.cu31_abastecimiento import schemas
from app.primer_parcial.proveedores.cu31_abastecimiento.service import AbastecimientoService

router = APIRouter(prefix="/abastecimiento", tags=["CU-31 Información de productos y abastecimiento"])
solo_admin = contexto_operativo(ADMIN)
solo_proveedor = contexto_operativo(PROVEEDOR)
admin_o_proveedor = contexto_operativo(ADMIN, PROVEEDOR)


@router.get("/mi-proveedor", response_model=ProveedorOut)
def mi_proveedor(ctx: Contexto = Depends(solo_proveedor), db: Session = Depends(get_db)):
    return AbastecimientoService(db, ctx).mi_proveedor()


@router.get("/sucursales", response_model=list[schemas.SucursalDestino])
def sucursales_de_destino(ctx: Contexto = Depends(admin_o_proveedor), db: Session = Depends(get_db)):
    return AbastecimientoService(db, ctx).sucursales_destino()


@router.get("/variantes", response_model=list[schemas.VarianteHabilitada])
def productos_habilitados(q: str | None = None, ctx: Contexto = Depends(admin_o_proveedor), db: Session = Depends(get_db)):
    """Productos ya creados que se pueden incluir en un aviso de remisión (se buscan por nombre o SKU)."""
    return AbastecimientoService(db, ctx).buscar_variantes(q)


@router.get("/resumen", response_model=schemas.ResumenOut)
def resumen_para_la_administracion(ctx: Contexto = Depends(solo_admin), db: Session = Depends(get_db)):
    """Avisos pendientes de la administración: lotes en tránsito y propuestas por revisar."""
    return AbastecimientoService(db, ctx).resumen()


# ---- avisos de remisión ----
@router.post("/lotes", response_model=schemas.LoteOut, status_code=201)
def enviar_aviso_de_remision(datos: schemas.LoteIn, ctx: Contexto = Depends(admin_o_proveedor), db: Session = Depends(get_db)):
    return AbastecimientoService(db, ctx).crear_lote(datos)


@router.get("/lotes", response_model=list[schemas.LoteOut])
def listar_lotes(estado: str | None = None, proveedor_id: int | None = None, ctx: Contexto = Depends(admin_o_proveedor), db: Session = Depends(get_db)):
    return AbastecimientoService(db, ctx).listar_lotes(estado, proveedor_id)


@router.get("/lotes/{lote_id}", response_model=schemas.LoteOut)
def consultar_lote(lote_id: int, ctx: Contexto = Depends(admin_o_proveedor), db: Session = Depends(get_db)):
    return AbastecimientoService(db, ctx).obtener_lote(lote_id)


@router.post("/lotes/{lote_id}/cancelar", response_model=schemas.LoteOut)
def cancelar_lote(lote_id: int, ctx: Contexto = Depends(admin_o_proveedor), db: Session = Depends(get_db)):
    return AbastecimientoService(db, ctx).cancelar_lote(lote_id)


# ---- propuestas de producto ----
@router.post("/propuestas", response_model=schemas.PropuestaOut, status_code=201)
def proponer_producto(datos: schemas.PropuestaIn, ctx: Contexto = Depends(solo_proveedor), db: Session = Depends(get_db)):
    return AbastecimientoService(db, ctx).crear_propuesta(datos)


@router.get("/propuestas", response_model=list[schemas.PropuestaOut])
def listar_propuestas(estado: str | None = None, ctx: Contexto = Depends(admin_o_proveedor), db: Session = Depends(get_db)):
    return AbastecimientoService(db, ctx).listar_propuestas(estado)


@router.post("/propuestas/{propuesta_id}/aprobar", response_model=schemas.PropuestaOut)
def aprobar_propuesta(propuesta_id: int, datos: schemas.RevisionIn, ctx: Contexto = Depends(solo_admin), db: Session = Depends(get_db)):
    return AbastecimientoService(db, ctx).revisar_propuesta(propuesta_id, True, datos.notas)


@router.post("/propuestas/{propuesta_id}/rechazar", response_model=schemas.PropuestaOut)
def rechazar_propuesta(propuesta_id: int, datos: schemas.RevisionIn, ctx: Contexto = Depends(solo_admin), db: Session = Depends(get_db)):
    return AbastecimientoService(db, ctx).revisar_propuesta(propuesta_id, False, datos.notas)

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.constantes import ADMIN, ENCARGADO
from app.core.database import get_db
from app.modules.acceso.dependencias import Contexto
from app.modules.plataforma.publico import contexto_operativo
from app.primer_parcial.catalogo.publico import ColeccionOut
from app.primer_parcial.proveedores.cu15_proveedores import schemas
from app.primer_parcial.proveedores.cu15_proveedores.service import ProveedorService

router = APIRouter(tags=["CU-15 Proveedores"])
solo_admin = contexto_operativo(ADMIN)
admin_o_encargado = contexto_operativo(ADMIN, ENCARGADO)  # el Encargado consulta a los proveedores al recibir mercadería


@router.get("/proveedores", response_model=list[schemas.ProveedorOut])
def listar_proveedores(solo_activos: bool = False, q: str | None = None, ctx: Contexto = Depends(admin_o_encargado), db: Session = Depends(get_db)):
    return ProveedorService(db, ctx.empresa_id).listar(solo_activos or ctx.rol != ADMIN, q)


@router.post("/proveedores", response_model=schemas.ProveedorOut, status_code=201)
def crear_proveedor(datos: schemas.ProveedorIn, ctx: Contexto = Depends(solo_admin), db: Session = Depends(get_db)):
    return ProveedorService(db, ctx.empresa_id).crear(datos)


@router.get("/proveedores/{proveedor_id}", response_model=schemas.ProveedorOut)
def consultar_proveedor(proveedor_id: int, ctx: Contexto = Depends(admin_o_encargado), db: Session = Depends(get_db)):
    return ProveedorService(db, ctx.empresa_id).obtener(proveedor_id)


@router.put("/proveedores/{proveedor_id}", response_model=schemas.ProveedorOut)
def editar_proveedor(proveedor_id: int, datos: schemas.ProveedorUpdate, ctx: Contexto = Depends(solo_admin), db: Session = Depends(get_db)):
    return ProveedorService(db, ctx.empresa_id).editar(proveedor_id, datos)


@router.post("/proveedores/{proveedor_id}/activar", response_model=schemas.ProveedorOut)
def activar_proveedor(proveedor_id: int, ctx: Contexto = Depends(solo_admin), db: Session = Depends(get_db)):
    return ProveedorService(db, ctx.empresa_id).cambiar_estado(proveedor_id, True)


@router.post("/proveedores/{proveedor_id}/desactivar", response_model=schemas.ProveedorOut)
def desactivar_proveedor(proveedor_id: int, ctx: Contexto = Depends(solo_admin), db: Session = Depends(get_db)):
    return ProveedorService(db, ctx.empresa_id).cambiar_estado(proveedor_id, False)


@router.post("/proveedores/{proveedor_id}/acceso", response_model=schemas.ProveedorOut, status_code=201)
def crear_acceso_del_proveedor(proveedor_id: int, datos: schemas.AccesoIn, ctx: Contexto = Depends(solo_admin), db: Session = Depends(get_db)):
    return ProveedorService(db, ctx.empresa_id).crear_acceso(proveedor_id, datos)


@router.put("/colecciones/{coleccion_id}/proveedor", response_model=ColeccionOut)
def vincular_coleccion_con_proveedor(coleccion_id: int, datos: schemas.VincularColeccionIn, ctx: Contexto = Depends(solo_admin), db: Session = Depends(get_db)):
    """Asocia una colección con el proveedor que la provee (o la deja sin proveedor)."""
    return ProveedorService(db, ctx.empresa_id).vincular_coleccion(coleccion_id, datos.proveedor_id)

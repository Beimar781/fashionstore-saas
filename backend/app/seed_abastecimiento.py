"""Datos de ejemplo de la Fase B para las dos empresas de prueba: un proveedor con acceso al portal, un lote en tránsito
y una propuesta de producto pendiente. Lo llama `app.seed`; es idempotente."""
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.acceso.models import Usuario
from app.modules.sucursales.models import Sucursal
from app.primer_parcial.catalogo.models import Coleccion, Variante
from app.primer_parcial.proveedores.models import Lote, LoteItem, Propuesta, Proveedor

PROVEEDORES = {
    "EMP-A": dict(razon_social="Textiles del Oriente S.R.L.", nombre_comercial="Textiles del Oriente", nit="1015566020", email="ventas@textilesoriente.com", telefono="3-3345566"),
    "EMP-B": dict(razon_social="Hilos Andinos Ltda.", nombre_comercial="Hilos Andinos", nit="2027788030", email="contacto@hilosandinos.com", telefono="2-2456677"),
}


def cargar(db: Session, empresa, rol_proveedor_id: int, password_hash: str) -> None:
    datos = PROVEEDORES.get(empresa.codigo)
    if datos is None or db.scalar(select(Proveedor.id).where(Proveedor.empresa_id == empresa.id).limit(1)):
        return
    eid = empresa.id
    usuario = Usuario(
        empresa_id=eid, rol_id=rol_proveedor_id, nombre=datos["nombre_comercial"], apellidos="", email="proveedor@tienda.com",
        password_hash=password_hash, activo=True,
    )
    db.add(usuario)
    db.flush()
    proveedor = Proveedor(empresa_id=eid, usuario_id=usuario.id, **datos)
    db.add(proveedor)
    db.flush()

    coleccion = db.scalar(select(Coleccion).where(Coleccion.empresa_id == eid).order_by(Coleccion.id))
    if coleccion is not None:
        coleccion.proveedor_id = proveedor.id
        db.add(Propuesta(
            empresa_id=eid, proveedor_id=proveedor.id, coleccion_id=coleccion.id, nombre="Chaqueta Impermeable", genero="UNISEX",
            descripcion="Chaqueta ligera para lluvia, con capucha.", precio_base=Decimal("260"), material="Poliéster reciclado",
        ))

    sucursal = db.scalar(select(Sucursal).where(Sucursal.empresa_id == eid, Sucursal.activa.is_(True)).order_by(Sucursal.id))
    variantes = list(db.scalars(select(Variante).where(Variante.empresa_id == eid).order_by(Variante.id).limit(3)))
    if sucursal is not None and variantes:
        lote = Lote(empresa_id=eid, proveedor_id=proveedor.id, sucursal_id=sucursal.id, codigo=f"LOT-E{eid:05d}", referencia="REM-0001", creado_por=usuario.id)
        db.add(lote)
        db.flush()
        for v in variantes:
            db.add(LoteItem(empresa_id=eid, lote_id=lote.id, variante_id=v.id, cantidad=12, costo_unitario=Decimal("45")))

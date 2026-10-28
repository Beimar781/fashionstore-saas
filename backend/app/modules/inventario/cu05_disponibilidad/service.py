"""CU-05 · Consultar tallas, colores y disponibilidad por sucursal (RN01, RN02). Capa de negocio."""
from sqlalchemy.orm import Session

from app.core.errors import NoEncontrado
from app.modules.inventario.cu05_disponibilidad import schemas
from app.modules.inventario.cu05_disponibilidad.repository import DisponibilidadRepository
from app.modules.sucursales.publico import sucursales_activas


class DisponibilidadService:
    def __init__(self, db: Session, empresa_id: int):
        self.db = db
        self.empresa_id = empresa_id
        self.repo = DisponibilidadRepository(db, empresa_id)

    def por_sucursal(self, producto_id: int) -> schemas.DisponibilidadOut:
        producto = self.repo.producto_visible(producto_id)
        if producto is None:
            raise NoEncontrado("Producto no encontrado.")  # inactivo o de otra empresa
        variantes = sorted((v for v in producto.variantes if v.activa), key=lambda v: (v.talla.orden, v.color.nombre))
        unidades = self.repo.unidades_por_sucursal([v.id for v in variantes])

        sucursales = []
        for s in sucursales_activas(self.db, self.empresa_id):
            filas = [
                schemas.VarianteDisponible(variante_id=v.id, talla=v.talla.codigo, color=v.color.nombre, cantidad=unidades.get((s["id"], v.id), 0))
                for v in variantes
            ]
            con_stock = [f for f in filas if f.cantidad > 0]
            sucursales.append(schemas.SucursalDisponibilidad(
                sucursal_id=s["id"], sucursal=s["nombre"], ciudad=s["ciudad"], direccion=s["direccion"], horario=s["horario"],
                total=sum(f.cantidad for f in filas), disponible=bool(con_stock),
                tallas=list(dict.fromkeys(f.talla for f in con_stock)), colores=sorted({f.color for f in con_stock}), variantes=filas,
            ))
        sucursales.sort(key=lambda s: (-s.total, s.sucursal))  # primero donde hay más unidades
        return schemas.DisponibilidadOut(producto_id=producto.id, producto=producto.nombre, sucursales=sucursales)

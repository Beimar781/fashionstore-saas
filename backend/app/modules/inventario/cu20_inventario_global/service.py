"""CU-20 · Consultar inventario global (RN01, RN02). Capa de negocio.

Muestra las existencias de todas las sucursales de la empresa: disponibles, reservadas, vendidas, agotadas y próximas a ingresar.
CU-26 reutiliza esta misma consulta fijando la sucursal del Encargado.
"""
from sqlalchemy.orm import Session

from app.core.errors import NoEncontrado
from app.modules.inventario.cu20_inventario_global import schemas
from app.modules.inventario.cu20_inventario_global.repository import ConsultaInventarioRepository
from app.modules.sucursales.publico import nombres_de_sucursales, sucursal_de_empresa
from app.primer_parcial.proveedores.publico import en_transito_por_variante


class InventarioGlobalService:
    def __init__(self, db: Session, empresa_id: int):
        self.db = db
        self.empresa_id = empresa_id
        self.consulta = ConsultaInventarioRepository(db, empresa_id)

    def consultar(self, f: schemas.FiltrosInventario) -> schemas.InventarioPagina:
        if f.sucursal is not None and not sucursal_de_empresa(self.db, self.empresa_id, f.sucursal):
            raise NoEncontrado("Sucursal no encontrada.")  # también si es de otra empresa
        en_transito = en_transito_por_variante(self.db, self.empresa_id, f.sucursal)  # «próxima a ingresar»: lotes en tránsito
        totales, proximas, por_sucursal, pagina = self.consulta.buscar(f, en_transito)
        disponibles, reservadas, vendidas, agotadas, total = totales
        nombres = nombres_de_sucursales(self.db, self.empresa_id)
        return schemas.InventarioPagina(
            resumen=schemas.ResumenInventario(
                disponibles=int(disponibles), reservadas=int(reservadas), vendidas=int(vendidas), agotadas=agotadas, proximas_a_ingresar=proximas
            ),
            por_sucursal=[
                schemas.ResumenSucursal(sucursal_id=i, sucursal=nombres.get(i, ""), disponibles=int(d), reservadas=int(r), vendidas=int(v))
                for i, d, r, v in sorted(por_sucursal, key=lambda x: nombres.get(x[0], ""))
            ],
            total=total, pagina=f.pagina, tamano=f.tamano,
            items=[
                schemas.FilaInventario(
                    variante_id=r.variante_id, sku=r.sku, producto_id=r.producto_id, producto=r.producto, categoria=r.categoria, talla=r.talla,
                    color=r.color, disponible=int(r.disponible), reservada=int(r.reservada), vendida=int(r.vendida),
                    proxima=en_transito.get(r.variante_id, 0), umbral_minimo=int(r.umbral) if f.sucursal is not None else None,
                    bajo_minimo=r.umbral > 0 and r.disponible <= r.umbral and f.sucursal is not None, agotada=r.disponible == 0,
                )
                for r in pagina
            ],
        )

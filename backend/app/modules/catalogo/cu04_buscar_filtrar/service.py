"""CU-04 · Buscar y filtrar prendas (RN01, RN02). Capa de negocio."""
from sqlalchemy.orm import Session

from app.modules.catalogo.cu03_consultar_catalogo import schemas
from app.modules.catalogo.cu03_consultar_catalogo.service import CatalogoService
from app.modules.catalogo.cu04_buscar_filtrar.repository import BusquedaRepository
from app.modules.catalogo.cu04_buscar_filtrar.schemas import FiltrosBusqueda


class BusquedaService(CatalogoService):
    def __init__(self, db: Session, empresa_id: int):
        super().__init__(db, empresa_id)
        self.busqueda = BusquedaRepository(db, empresa_id)

    def buscar(self, filtros: FiltrosBusqueda) -> schemas.PrendasPagina:
        self.validar_sucursal(filtros.sucursal)
        total, productos = self.busqueda.buscar(filtros)
        return self.pagina(total, productos, filtros.sucursal, filtros.pagina, filtros.tamano)

from typing import Literal

from pydantic import BaseModel, Field

EstadoExistencia = Literal["DISPONIBLE", "AGOTADA", "RESERVADA", "VENDIDA", "PROXIMA"]


class FiltrosInventario(BaseModel):
    q: str | None = Field(default=None, max_length=100)  # producto o SKU
    categoria_id: int | None = None
    temporada_id: int | None = None
    estado: EstadoExistencia | None = None
    sucursal: int | None = None
    solo_bajo_minimo: bool = False  # requiere sucursal: usa el umbral de reposición de esa sucursal
    pagina: int = Field(default=1, ge=1)
    tamano: int = Field(default=25, ge=1, le=100)


class FilaInventario(BaseModel):
    variante_id: int
    sku: str
    producto_id: int
    producto: str
    categoria: str
    talla: str
    color: str
    disponible: int
    reservada: int
    vendida: int
    proxima: int  # unidades en lotes en tránsito
    umbral_minimo: int | None  # solo cuando se consulta una sucursal
    bajo_minimo: bool
    agotada: bool


class ResumenInventario(BaseModel):
    """Totales de lo filtrado: unidades disponibles, reservadas, vendidas y próximas a ingresar, y variantes agotadas."""

    disponibles: int
    reservadas: int
    vendidas: int
    agotadas: int
    proximas_a_ingresar: int


class ResumenSucursal(BaseModel):
    sucursal_id: int
    sucursal: str
    disponibles: int
    reservadas: int
    vendidas: int


class InventarioPagina(BaseModel):
    resumen: ResumenInventario
    por_sucursal: list[ResumenSucursal]  # vacío cuando se consulta una sola sucursal
    total: int
    pagina: int
    tamano: int
    items: list[FilaInventario]

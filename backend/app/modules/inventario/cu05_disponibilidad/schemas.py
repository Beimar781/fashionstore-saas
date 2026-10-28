from pydantic import BaseModel


class VarianteDisponible(BaseModel):
    variante_id: int
    talla: str
    color: str
    cantidad: int


class SucursalDisponibilidad(BaseModel):
    sucursal_id: int
    sucursal: str
    ciudad: str
    direccion: str | None
    horario: str | None
    total: int
    disponible: bool
    tallas: list[str]  # tallas con unidades en esta sucursal, en orden
    colores: list[str]
    variantes: list[VarianteDisponible]


class DisponibilidadOut(BaseModel):
    producto_id: int
    producto: str
    sucursales: list[SucursalDisponibilidad]

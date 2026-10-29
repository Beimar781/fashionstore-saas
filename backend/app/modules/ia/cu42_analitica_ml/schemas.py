from datetime import date

from pydantic import BaseModel


class RotacionOut(BaseModel):
    producto: str
    unidades_30d: int
    stock: int
    tasa_diaria: float  # unidades vendidas por día en los últimos 30 días
    clase: str  # ALTA | MEDIA | BAJA


class PronosticoOut(BaseModel):
    producto: str
    semanas_con_ventas: int
    historial: list[int]  # unidades por semana, de la más antigua a la más reciente
    proyeccion: list[int]  # las próximas semanas
    tendencia: str  # SUBE | ESTABLE | BAJA
    r2: float  # qué tan bien se ajusta el modelo a la historia (0 a 1)
    stock: int
    recomendacion: str


class PuntoSerieOut(BaseModel):
    semana_inicio: date
    unidades: int
    proyectada: bool


class AnaliticaOut(BaseModel):
    sucursal_id: int | None
    desde: date
    hasta: date
    semanas_historia: int
    semanas_proyeccion: int
    rotacion: list[RotacionOut]
    pronostico: list[PronosticoOut]
    serie_total: list[PuntoSerieOut]
    sin_historial_suficiente: int  # productos con muy pocas semanas de ventas para pronosticar
    mensaje: str | None
    modelos: dict[str, str]

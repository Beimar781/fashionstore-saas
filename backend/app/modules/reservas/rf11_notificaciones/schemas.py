from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NotificacionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tipo: str
    titulo: str
    mensaje: str
    sucursal_id: int | None
    referencia_tipo: str
    referencia_id: int | None
    leida: bool
    creada_en: datetime


class ResumenNotificaciones(BaseModel):
    no_leidas: int

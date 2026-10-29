from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


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


class DispositivoIn(BaseModel):
    canal: Literal["WEB", "MOVIL"]
    token: str = Field(min_length=1, max_length=4000)  # WEB: la suscripción del navegador en JSON; MOVIL: el token de FCM


class DispositivoOut(BaseModel):
    id: int
    canal: str
    activo: bool


class ConfigPush(BaseModel):
    vapid_public_key: str  # la web la necesita para suscribirse; vacía = modo simulado
    web_real: bool
    movil_real: bool

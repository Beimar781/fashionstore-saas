from datetime import datetime

from pydantic import BaseModel, Field


class PromptIn(BaseModel):
    prompt: str = Field(default="", max_length=500)  # escrito o dictado por voz (la web lo transcribe con la Web Speech API)


class ReporteGenerativoOut(BaseModel):
    id: int
    prompt: str
    origen: str  # IA (API externa) o REGLAS (modo de respaldo)
    especificacion: dict  # cómo se interpretó la petición
    texto: str  # el reporte redactado
    datos: dict  # las cifras en las que se basa
    creado_en: datetime

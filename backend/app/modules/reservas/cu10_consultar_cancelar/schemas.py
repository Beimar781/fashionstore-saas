from pydantic import BaseModel, Field


class CancelacionIn(BaseModel):
    motivo: str = Field(default="", max_length=200)

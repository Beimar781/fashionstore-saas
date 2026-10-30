from pydantic import BaseModel, Field


class Anclaje(BaseModel):
    """Dónde está la prenda dentro de su PNG (proporciones de 0 a 1). El móvil la coloca sobre el cuerpo haciendo coincidir estos puntos con los hombros y las caderas."""

    y_hombros: float = Field(default=0.10, ge=0, le=0.5)  # altura de la línea de hombros
    ancho_hombros: float = Field(default=0.85, ge=0.3, le=1.0)  # ancho que ocupan los hombros respecto al ancho del PNG
    y_cadera: float = Field(default=0.92, ge=0.4, le=1.0)  # altura donde termina el torso (la cadera)
    ajuste: float = Field(default=1.0, ge=0.5, le=1.5)  # ajuste fino de la escala


class ColorVestidorOut(BaseModel):
    color_id: int
    color: str
    codigo_hex: str
    listo: bool  # tiene imagen para el vestidor
    imagen_url: str | None
    ancho: int | None
    alto: int | None
    anclaje: Anclaje | None


class VestidorProductoOut(BaseModel):
    producto_id: int
    producto: str
    admite: bool  # solo las prendas superiores (camisas, polos, chaquetas)
    mensaje: str | None
    colores: list[ColorVestidorOut]
    escala_tallas: dict[str, float]  # por código de talla; las que no figuran usan 1.0

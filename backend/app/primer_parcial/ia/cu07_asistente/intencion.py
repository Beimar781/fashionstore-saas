"""CU-07 · Entiende lo que pide el cliente: la IA externa (si hay clave) o reglas locales de respaldo, basadas en `ai/intent.py` del primer parcial."""
import re
import unicodedata
from decimal import Decimal, InvalidOperation
from typing import Literal

from pydantic import BaseModel, Field

from app.core.ia import ClienteIA


class Intencion(BaseModel):
    saludo: bool = False
    colores: list[str] = Field(default_factory=list)  # nombres tal como están en el catálogo de la empresa
    categorias: list[str] = Field(default_factory=list)
    talla: str | None = None
    precio_min: Decimal | None = None
    precio_max: Decimal | None = None
    genero: Literal["MASCULINO", "FEMENINO", "UNISEX", "NINOS"] | None = None
    ocasion: str | None = None  # palabra que se busca en nombre, descripción o material
    outfit: bool = False  # pide un conjunto de prendas que combinen
    ofertas: bool = False
    recomendar: bool = False  # pide que el sistema le sugiera algo según sus gustos

    def vacia(self) -> bool:
        return not (self.colores or self.categorias or self.talla or self.precio_min or self.precio_max or self.genero or self.ocasion or self.outfit or self.ofertas)


def normalizar(texto: str) -> str:
    descompuesto = unicodedata.normalize("NFKD", texto.lower().strip())
    return "".join(c for c in descompuesto if not unicodedata.combining(c))


def _numero(crudo: str) -> Decimal | None:
    try:
        return Decimal(crudo.replace(",", "."))
    except InvalidOperation:
        return None


def _palabra(texto: str, termino: str) -> bool:
    base = normalizar(termino)
    variantes = {base, base.rstrip("s"), base.removesuffix("es"), base + "s", base + "es", base.rstrip("o") + "a"}  # camisas/camisa, pantalones/pantalón
    return any(re.search(rf"\b{re.escape(v)}\b", texto) for v in variantes if v)


OCASIONES = ("formal", "casual", "deportiv", "fiesta", "oficina", "playa", "invierno", "verano", "elegante")
GENEROS = (
    ("NINOS", ("nino", "nina", "ninos", "ninas", "infantil", "kids")),
    ("FEMENINO", ("mujer", "dama", "femenin", "chica", "senora")),
    ("MASCULINO", ("hombre", "varon", "masculin", "caballero", "chico", "senor")),
    ("UNISEX", ("unisex",)),
)


def parsear_con_reglas(mensaje: str, colores: list[str], categorias: list[str]) -> Intencion:
    t = normalizar(mensaje)
    i = Intencion(
        colores=[c for c in colores if _palabra(t, c)], categorias=[c for c in categorias if _palabra(t, c)],
        outfit=bool(re.search(r"\b(outfit|conjunto|combinar|combina|combinacion|atuendo|look)\b", t)),
        ofertas=bool(re.search(r"\b(oferta|ofertas|promocion|promociones|descuento|descuentos|rebaja|rebajas)\b", t)),
    )
    talla = re.search(r"\btalla\s+([a-z0-9]{1,3})\b", t) or re.search(r"\b(xs|xl|xxl)\b", t)
    i.talla = talla.group(1).upper() if talla else None
    i.recomendar = bool(re.search(r"\b(recomiend\w*|recomend\w*|sugier\w*|sugerenc\w*|sorprend\w*|algo para mi)\b", t))
    entre = re.search(r"entre\s+(\d+(?:[.,]\d+)?)\s+y\s+(\d+(?:[.,]\d+)?)", t)
    if entre:
        a, b = _numero(entre.group(1)), _numero(entre.group(2))
        if a is not None and b is not None:
            i.precio_min, i.precio_max = min(a, b), max(a, b)
    else:
        tope = re.search(r"(?:menos de|hasta|maximo|no mas de|por debajo de|bajo)\s+(?:bs\.?\s*)?(\d+(?:[.,]\d+)?)", t)
        piso = re.search(r"(?:mas de|desde|minimo|por encima de)\s+(?:bs\.?\s*)?(\d+(?:[.,]\d+)?)", t)
        cerca = re.search(r"(?:alrededor de|cerca de|unos|aproximadamente)\s+(?:bs\.?\s*)?(\d+(?:[.,]\d+)?)", t)
        i.precio_max = _numero(tope.group(1)) if tope else None
        i.precio_min = _numero(piso.group(1)) if piso else None
        if cerca and _numero(cerca.group(1)):
            centro = _numero(cerca.group(1))
            i.precio_min, i.precio_max = (centro * Decimal("0.8")).quantize(Decimal("0.01")), (centro * Decimal("1.2")).quantize(Decimal("0.01"))
    for genero, claves in GENEROS:
        if any(re.search(rf"\b{k}", t) for k in claves):
            i.genero = genero
            break
    i.ocasion = next((o for o in OCASIONES if o in t), None)
    i.saludo = i.vacia() and not i.recomendar and bool(re.match(r"^\W*(hola|buenas|buen dia|buenos dias|buenas tardes|buenas noches|hey|que tal)\b", t))
    return i


def combinar(anterior: Intencion | None, actual: Intencion) -> Intencion:
    """Lo que el cliente dice ahora completa lo que pidió antes («y en azul»): lo nuevo reemplaza, lo demás se conserva."""
    if anterior is None or actual.vacia() or actual.recomendar:
        return actual
    datos = anterior.model_dump()
    for campo, valor in actual.model_dump().items():
        if valor not in (None, [], False):
            datos[campo] = valor
    datos["saludo"] = False
    return Intencion.model_validate(datos)


SISTEMA_IA = (
    "Eres el asistente de una tienda de ropa. Extrae del último mensaje del cliente (usando la conversación como contexto) los filtros de búsqueda y "
    "responde SOLO un JSON con: saludo (bool), recomendar (bool: pide que le sugieran algo según sus gustos), colores (lista, solo de los colores disponibles), categorias (lista, solo de las categorías disponibles), "
    "talla (texto o null), precio_min y precio_max (números o null), genero ('MASCULINO','FEMENINO','UNISEX','NINOS' o null), ocasion (una palabra o null), "
    "outfit (bool: pide un conjunto que combine) y ofertas (bool: pide promociones)."
)


def parsear_con_ia(ia: ClienteIA, mensajes: list[tuple[str, str]], colores: list[str], categorias: list[str]) -> Intencion | None:
    conversacion = "\n".join(f"{rol}: {texto}" for rol, texto in mensajes[-6:])
    crudo = ia.json_estructurado(SISTEMA_IA, f"Colores disponibles: {colores}\nCategorías disponibles: {categorias}\nConversación:\n{conversacion}")
    if crudo is None:
        return None
    try:
        i = Intencion.model_validate(crudo)
    except Exception:
        return None
    i.colores = [c for c in i.colores if c in colores]  # lo que la IA invente fuera del catálogo se descarta
    i.categorias = [c for c in i.categorias if c in categorias]
    return i

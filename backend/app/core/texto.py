"""Utilidades de texto compartidas: slugs y códigos cortos (únicos por empresa en cada módulo que los use)."""
import re
import unicodedata


def slugify(texto: str) -> str:
    sin_tildes = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", sin_tildes.lower()).strip("-")


def codigo_corto(texto: str, ocupado, largo: int = 3, maximo: int = 6) -> str:
    """Código en mayúsculas de `largo` letras o números; si `ocupado(codigo)` agrega un número (ROJ, ROJ2, ROJ3...)."""
    base = re.sub(r"[^A-Z0-9]", "", slugify(texto).upper())[:largo] or "X"
    codigo, n = base, 1
    while ocupado(codigo):
        n += 1
        codigo = f"{base[: maximo - len(str(n))]}{n}"
    return codigo

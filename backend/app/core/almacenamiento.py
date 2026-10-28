"""Imágenes de productos en disco: una carpeta por empresa (`<media_dir>/<empresa_id>/productos/<producto_id>/`)."""
import uuid
from pathlib import Path

from app.core.config import get_settings


def _carpeta_media() -> Path:
    return Path(get_settings().media_dir).resolve()


def tipo_imagen(datos: bytes) -> str | None:
    """Extensión según la firma del archivo (no se confía en el nombre ni en el Content-Type)."""
    if datos[:3] == b"\xff\xd8\xff":
        return "jpg"
    if datos[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if datos[:4] == b"RIFF" and datos[8:12] == b"WEBP":
        return "webp"
    return None


def guardar_imagen(empresa_id: int, producto_id: int, datos: bytes, extension: str) -> str:
    ruta = f"{empresa_id}/productos/{producto_id}/{uuid.uuid4().hex}.{extension}"
    destino = _carpeta_media() / ruta
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(datos)
    return ruta


def borrar_imagen(ruta: str) -> None:
    destino = (_carpeta_media() / ruta).resolve()
    if _carpeta_media() in destino.parents:  # nunca borra fuera de la carpeta de imágenes
        destino.unlink(missing_ok=True)


def url_media(ruta: str) -> str:
    return f"/media/{ruta}"

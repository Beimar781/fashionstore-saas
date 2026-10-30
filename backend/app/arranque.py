"""Arranque en la nube (Railway): comprobaciones de la configuración y carga de los datos de demostración.

Uso (lo llama el Dockerfile después de las migraciones):  python -m app.arranque
"""
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import SECRET_KEY_POR_DEFECTO, Settings, get_settings

logger = logging.getLogger("fashionstore.arranque")
MSG_SECRET_KEY = "En producción la SECRET_KEY no puede ser la de por defecto. Defina una clave larga y secreta en las variables del servicio (ver docs/DESPLIEGUE.md)."


def validar_configuracion(cfg: Settings | None = None) -> None:
    """El backend se niega a arrancar en producción con la SECRET_KEY por defecto: con ella cualquiera podría fabricar tokens de acceso."""
    cfg = cfg or get_settings()
    if cfg.es_produccion and cfg.secret_key == SECRET_KEY_POR_DEFECTO:
        raise RuntimeError(MSG_SECRET_KEY)


def base_vacia(db: Session) -> bool:
    from app.modules.acceso.models import Usuario
    from app.modules.plataforma.models import Empresa

    return db.scalar(select(Empresa.id).limit(1)) is None and db.scalar(select(Usuario.id).limit(1)) is None


def cargar_datos_demo(db: Session) -> str:
    """Carga el seed solo si la base está vacía (nunca duplica). Si la base ya tiene datos pero el volumen de imágenes está vacío, repone las imágenes de demostración."""
    from app import seed
    from app.seed_prendas import reponer_imagenes

    if base_vacia(db):
        seed.ejecutar(db)
        return "Datos de demostración cargados."
    repuestas = reponer_imagenes(db)
    return f"La base ya tiene datos: no se carga el seed. Imágenes de demostración repuestas: {repuestas}."


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    validar_configuracion()
    cfg = get_settings()
    if not cfg.cargar_datos_demo:
        logger.info("CARGAR_DATOS_DEMO no está activo: no se cargan datos de demostración.")
        return
    from app.core.database import SessionLocal

    with SessionLocal() as db:
        logger.info(cargar_datos_demo(db))


if __name__ == "__main__":
    main()

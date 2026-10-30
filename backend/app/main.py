"""FashionStore SaaS · API REST (FastAPI). Punto de entrada.

Cada paquete de casos de uso (plataforma, acceso, sucursales, ...) expone sus routers; para agregar
un paquete nuevo basta con registrar su router en `app/api.py`.
"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

import app.db_models  # noqa: F401  (registra los modelos)
from app.api import api_router
from app.arranque import validar_configuracion
from app.core.config import get_settings
from app.core.database import engine
from app.core.errors import registrar_manejadores
from app.modules.plataforma.publico import BitacoraMiddleware


def create_app() -> FastAPI:
    validar_configuracion()
    app = FastAPI(
        title="FashionStore SaaS API",
        description="Plataforma de comercio electrónico multitenant (SI2 · Examen parcial 2).",
        version="0.1.0",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_settings().cors_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(BitacoraMiddleware)  # Fase J: registra inicios de sesión y operaciones de escritura
    registrar_manejadores(app)
    carpeta_media = Path(get_settings().media_dir)
    carpeta_media.mkdir(parents=True, exist_ok=True)
    app.mount("/media", StaticFiles(directory=carpeta_media), name="media")  # imágenes de productos
    app.include_router(api_router, prefix="/api")

    @app.get("/salud", tags=["salud"])
    def salud() -> JSONResponse:
        """Health check de la nube: responde 200 solo si la base de datos contesta."""
        try:
            with engine.connect() as conexion:
                conexion.execute(text("SELECT 1"))
        except Exception:  # noqa: BLE001
            return JSONResponse({"estado": "sin_base_de_datos"}, status_code=503)
        return JSONResponse({"estado": "ok"})

    return app


app = create_app()

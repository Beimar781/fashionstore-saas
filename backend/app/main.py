"""FashionStore SaaS · API REST (FastAPI). Punto de entrada.

Cada paquete de casos de uso (plataforma, acceso, sucursales, ...) expone sus routers; para agregar
un paquete nuevo basta con registrar su router en `app/api.py`.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.db_models  # noqa: F401  (registra los modelos)
from app.api import api_router
from app.core.config import get_settings
from app.core.errors import registrar_manejadores


def create_app() -> FastAPI:
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
    registrar_manejadores(app)
    app.include_router(api_router, prefix="/api")
    return app


app = create_app()

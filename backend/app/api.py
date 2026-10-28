"""Registro de routers por paquete de casos de uso (P1..P10 del documento)."""
from fastapi import APIRouter

from app.modules.acceso.cu02_login.router import router as cu02_login
from app.modules.acceso.cu13_usuarios.router import router as cu13_usuarios
from app.modules.plataforma.cu33_empresas.router import router as cu33_empresas
from app.modules.plataforma.cu34_planes.router import router as cu34_planes
from app.modules.plataforma.cu35_suscripciones.router import router as cu35_suscripciones
from app.modules.sucursales.cu14_sucursales.router import router as cu14_sucursales

api_router = APIRouter()


@api_router.get("/health", tags=["Sistema"])
def health():
    return {"estado": "ok"}


# P2 · Usuarios y acceso
api_router.include_router(cu02_login)
api_router.include_router(cu13_usuarios)
# P1 · Plataforma SaaS
api_router.include_router(cu33_empresas)
api_router.include_router(cu34_planes)
api_router.include_router(cu35_suscripciones)
# P3 · Sucursales y proveedores
api_router.include_router(cu14_sucursales)

# Aquí se registran, a medida que se construyen (docs/PLAN_PRIMER_PARCIAL.md), los routers de:
# SaaS (app/modules): P4 catalogo, P5 inventario, P6 reservas, P7 ventas, P8 offline, P9 ia, P10 reportes.
# Primer parcial (app/primer_parcial): P3 proveedores, P4 catalogo, P6 reservas, P7 ventas, P9 ia, P10 reportes.

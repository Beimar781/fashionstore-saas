"""Registro de routers por paquete de casos de uso (P1..P10 del documento)."""
from fastapi import APIRouter

from app.modules.acceso.cu01_registro_cliente.router import router as cu01_registro
from app.modules.acceso.cu02_login.router import router as cu02_login
from app.modules.acceso.cu13_usuarios.router import router as cu13_usuarios
from app.modules.catalogo.cu03_consultar_catalogo.router import router as cu03_catalogo
from app.modules.catalogo.cu04_buscar_filtrar.router import router as cu04_buscar
from app.modules.inventario.cu05_disponibilidad.router import router as cu05_disponibilidad
from app.modules.inventario.cu20_inventario_global.router import router as cu20_inventario_global
from app.modules.inventario.cu26_inventario_sucursal.router import router as cu26_inventario_sucursal
from app.modules.reservas.cu09_reservar.router import router as cu09_reservar
from app.modules.reservas.cu10_consultar_cancelar.router import router as cu10_reservas
from app.modules.reservas.rf11_notificaciones.router import router as rf11_notificaciones
from app.modules.plataforma.cu33_empresas.router import router as cu33_empresas
from app.modules.plataforma.cu34_planes.router import router as cu34_planes
from app.modules.plataforma.cu35_suscripciones.router import router as cu35_suscripciones
from app.modules.sucursales.cu14_sucursales.router import router as cu14_sucursales
from app.modules.ventas.cu29_venta_presencial.router import router as cu29_venta_presencial
from app.primer_parcial.ventas.cu28_productos_en_caja.router import router as cu28_productos_en_caja
from app.primer_parcial.ventas.cu30_pago_en_caja.router import router as cu30_pago_en_caja
from app.primer_parcial.reportes.cu27_ventas_sucursal.router import router as cu27_ventas_sucursal
from app.modules.ventas.cu41_devoluciones.router import router as cu41_devoluciones
from app.primer_parcial.reservas.cu08_carrito.router import router as cu08_carrito
from app.primer_parcial.ventas.cu11_compra_digital.router import router as cu11_compra
from app.primer_parcial.ventas.cu12_historial_compras.router import router as cu12_historial
from app.primer_parcial.ventas.cu32_pago_electronico.router import router as cu32_pagos
from app.primer_parcial.reservas.cu24_gestionar_reservas_sucursal.router import router as cu24_reservas_sucursal
from app.primer_parcial.reservas.cu25_confirmar_atencion.router import router as cu25_atencion
from app.primer_parcial.proveedores.cu15_proveedores.router import router as cu15_proveedores
from app.primer_parcial.proveedores.cu31_abastecimiento.router import router as cu31_abastecimiento
from app.primer_parcial.catalogo.cu16_categorias_tallas_colores.router import router as cu16_atributos
from app.primer_parcial.catalogo.cu17_temporadas_colecciones.router import router as cu17_temporadas
from app.primer_parcial.catalogo.cu18_productos.router import router as cu18_productos
from app.primer_parcial.catalogo.cu19_promociones.router import router as cu19_promociones

api_router = APIRouter()


@api_router.get("/health", tags=["Sistema"])
def health():
    return {"estado": "ok"}


# P2 · Usuarios y acceso
api_router.include_router(cu01_registro)
api_router.include_router(cu02_login)
api_router.include_router(cu13_usuarios)
# P1 · Plataforma SaaS
api_router.include_router(cu33_empresas)
api_router.include_router(cu34_planes)
api_router.include_router(cu35_suscripciones)
# P3 · Sucursales y proveedores
api_router.include_router(cu14_sucursales)
# P4 · Catálogo: consulta del cliente (SaaS) y administración (primer parcial)
api_router.include_router(cu03_catalogo)
api_router.include_router(cu04_buscar)
api_router.include_router(cu16_atributos)
api_router.include_router(cu17_temporadas)
api_router.include_router(cu18_productos)
api_router.include_router(cu19_promociones)
# P3 · Proveedores y abastecimiento (primer parcial)
api_router.include_router(cu15_proveedores)
api_router.include_router(cu31_abastecimiento)
# P5 · Inventario por sucursal
api_router.include_router(cu05_disponibilidad)
api_router.include_router(cu20_inventario_global)
api_router.include_router(cu26_inventario_sucursal)
# P6 · Reservas: el cliente reserva y consulta (SaaS); la sucursal prepara y atiende (primer parcial); avisos (RF11)
api_router.include_router(cu09_reservar)
api_router.include_router(cu10_reservas)
api_router.include_router(cu24_reservas_sucursal)
api_router.include_router(cu25_atencion)
api_router.include_router(rf11_notificaciones)
# P6/P7 · Compra digital (primer parcial): carrito, checkout, historial y pago
api_router.include_router(cu08_carrito)
api_router.include_router(cu11_compra)
api_router.include_router(cu12_historial)
api_router.include_router(cu32_pagos)
# P7/P10 · Punto de venta: productos en caja (CU-28), venta presencial (CU-29, SaaS), cobro y comprobante (CU-30), ventas de la sucursal (CU-27)
api_router.include_router(cu28_productos_en_caja)
api_router.include_router(cu29_venta_presencial)
api_router.include_router(cu30_pago_en_caja)
api_router.include_router(cu27_ventas_sucursal)
# P7 · Devoluciones y cambios de prendas (CU-41, nuevo)
api_router.include_router(cu41_devoluciones)

# Aquí se registran, a medida que se construyen (docs/PLAN_PRIMER_PARCIAL.md), los routers de:
# SaaS (app/modules): P8 offline, P9 ia, P10 reportes.
# Primer parcial (app/primer_parcial): P9 ia.

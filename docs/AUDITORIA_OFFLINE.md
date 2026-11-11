# Auditoría de las funciones sin conexión

Generada por `python scripts/auditar_offline.py` (revisión del código; la prueba con el service worker real se hace a mano, ver `PRUEBAS_SISTEMA.md` §17 a §20).

**Resumen:** 46 pantallas web revisadas (46 OK, 0 con aviso, 0 con falla) · 57 puntos del móvil revisados (57 OK, 0 por revisar).

## Web: actor × pantalla × resultado

| Actor | Pantalla | Resultado | Detalle |
|---|---|---|---|
| Administrador | `/empresa/(inicio)` | OK | carga con lecturas guardadas o copia local; sin «Cargando…» eterno |
| Administrador | `/empresa/bitacora` | OK | carga con lecturas guardadas o copia local; sin «Cargando…» eterno |
| Administrador | `/empresa/catalogo` | OK | carga con lecturas guardadas o copia local; sin «Cargando…» eterno |
| Administrador | `/empresa/conflictos` | OK | carga con lecturas guardadas o copia local; sin «Cargando…» eterno |
| Administrador | `/empresa/devoluciones` | OK | carga con lecturas guardadas o copia local; sin «Cargando…» eterno |
| Administrador | `/empresa/ia/analitica` | OK | carga con lecturas guardadas o copia local; sin «Cargando…» eterno |
| Administrador | `/empresa/ia/reportes` | OK | carga con lecturas guardadas o copia local; sin «Cargando…» eterno |
| Administrador | `/empresa/indicadores` | OK | carga con lecturas guardadas o copia local; sin «Cargando…» eterno |
| Administrador | `/empresa/inventario` | OK | carga con lecturas guardadas o copia local; sin «Cargando…» eterno |
| Administrador | `/empresa/plan` | OK | carga con lecturas guardadas o copia local; sin «Cargando…» eterno |
| Administrador | `/empresa/reportes` | OK | carga con lecturas guardadas o copia local; sin «Cargando…» eterno |
| Administrador | `/empresa/sucursales` | OK | carga con lecturas guardadas o copia local; sin «Cargando…» eterno |
| Administrador | `/empresa/usuarios` | OK | carga con lecturas guardadas o copia local; sin «Cargando…» eterno |
| Cajero | `/pos/caja` | OK | carga con lecturas guardadas o copia local; sin «Cargando…» eterno |
| Cajero | `/pos/devoluciones` | OK | carga con lecturas guardadas o copia local; sin «Cargando…» eterno |
| Cajero | `/pos/offline` | OK | carga con lecturas guardadas o copia local; sin «Cargando…» eterno |
| Cliente | `/tienda/asistente` | OK | responde con el catálogo descargado sin leer del servidor al abrir |
| Cliente | `/tienda/carrito` | OK | carga con lecturas guardadas o copia local; sin «Cargando…» eterno |
| Cliente | `/tienda/catalogo` | OK | carga con lecturas guardadas o copia local; sin «Cargando…» eterno |
| Cliente | `/tienda/catalogo/:id` | OK | carga con lecturas guardadas o copia local; sin «Cargando…» eterno |
| Cliente | `/tienda/catalogo/:id/vestidor` | OK | trabaja con la cámara y las imágenes guardadas, no con listas del servidor |
| Cliente | `/tienda/checkout` | OK | sin conexión guarda la compra en la cola; con red escribe en el servidor |
| Cliente | `/tienda/compras` | OK | carga con lecturas guardadas o copia local; sin «Cargando…» eterno |
| Cliente | `/tienda/compras/:id` | OK | carga con lecturas guardadas o copia local; sin «Cargando…» eterno |
| Cliente | `/tienda/offline` | OK | carga con lecturas guardadas o copia local; sin «Cargando…» eterno |
| Cliente | `/tienda/reservar` | OK | formulario: la reserva sin conexión se guarda en la cola (RN11) |
| Cliente | `/tienda/reservas` | OK | carga con lecturas guardadas o copia local; sin «Cargando…» eterno |
| Encargado | `/sucursal/atencion` | OK | carga con lecturas guardadas o copia local; sin «Cargando…» eterno |
| Encargado | `/sucursal/caja` | OK | carga con lecturas guardadas o copia local; sin «Cargando…» eterno |
| Encargado | `/sucursal/conflictos` | OK | carga con lecturas guardadas o copia local; sin «Cargando…» eterno |
| Encargado | `/sucursal/devoluciones` | OK | carga con lecturas guardadas o copia local; sin «Cargando…» eterno |
| Encargado | `/sucursal/global` | OK | carga con lecturas guardadas o copia local; sin «Cargando…» eterno |
| Encargado | `/sucursal/inventario` | OK | carga con lecturas guardadas o copia local; sin «Cargando…» eterno |
| Encargado | `/sucursal/movimientos` | OK | carga con lecturas guardadas o copia local; sin «Cargando…» eterno |
| Encargado | `/sucursal/movimientos` | OK | carga con lecturas guardadas o copia local; sin «Cargando…» eterno |
| Encargado | `/sucursal/offline` | OK | carga con lecturas guardadas o copia local; sin «Cargando…» eterno |
| Encargado | `/sucursal/recepciones` | OK | carga con lecturas guardadas o copia local; sin «Cargando…» eterno |
| Encargado | `/sucursal/reservas` | OK | carga con lecturas guardadas o copia local; sin «Cargando…» eterno |
| Encargado | `/sucursal/ventas` | OK | carga con lecturas guardadas o copia local; sin «Cargando…» eterno |
| Proveedor | `/proveedor/(inicio)` | OK | carga con lecturas guardadas o copia local; sin «Cargando…» eterno |
| Proveedor | `/proveedor/abastecimiento` | OK | carga con lecturas guardadas o copia local; sin «Cargando…» eterno |
| Proveedor | `/proveedor/proveedores` | OK | carga con lecturas guardadas o copia local; sin «Cargando…» eterno |
| SuperAdministrador | `/plataforma/bitacora` | OK | carga con lecturas guardadas o copia local; sin «Cargando…» eterno |
| SuperAdministrador | `/plataforma/empresas` | OK | carga con lecturas guardadas o copia local; sin «Cargando…» eterno |
| SuperAdministrador | `/plataforma/empresas/:id/suscripcion` | OK | carga con lecturas guardadas o copia local; sin «Cargando…» eterno |
| SuperAdministrador | `/plataforma/planes` | OK | carga con lecturas guardadas o copia local; sin «Cargando…» eterno |

## Móvil: indicadores de carga y manejo de `ApiException`

| Archivo | Patrón | Resultado |
|---|---|---|
| (todos con salida sin conexión) | | OK |

Total de puntos del móvil con salida sin conexión: 57 de 57.


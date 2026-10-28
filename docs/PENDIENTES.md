# Pendientes por lote

El Lote 1 (núcleo multitenant) está implementado y probado. El resto del documento se construye sobre esta base:
**toda tabla nueva lleva `empresa_id`, todo repositorio nuevo hereda de `TenantRepository`, y toda ruta de empresa usa `contexto_operativo(...)`.**

## Lote 2 — Operación comercial por empresa y offline
~~CU-01, CU-03, CU-04~~ (hechos en la Fase A), ~~CU-05~~ (hecho en la Fase B), CU-09, CU-29, CU-36, CU-37, CU-38, CU-39 → paquetes P4 catálogo, P5 inventario, P6 reservas, P7 ventas, P8 offline/sincronización.
- Web: IndexedDB ya tiene los almacenes `catalogo`, `operaciones` y `cache_meta` (`core/offline/local-db.service.ts`).
- Móvil: SQLite ya tiene las tablas `productos_locales` y `operaciones_pendientes` con los estados de RN11 (`lib/core/db/local_database.dart`).
- Gancho existente: `sucursales/cu14_sucursales/service.py::tiene_pendientes()` (CU-14, excepción de desactivar con pendientes).

## Lote 3 — Gestión avanzada
CU-10, ~~CU-20~~, CU-21, CU-22, CU-23, ~~CU-26~~ (hechos en la Fase B), CU-40, CU-41, CU-42 → P7 devoluciones, P9 IA/analítica, P10 reportes.
- RN07 ya está resuelta: proteger los endpoints de IA con `Depends(exigir_funcionalidad("reportes_ia"))`.

## Casos de uso conservados del primer parcial (deben funcionar dentro de cada empresa)
El código base del primer parcial es Django/React Native; se **porta** a FastAPI/Flutter agregando `empresa_id`:

| CU conservados | App del backend base (Django) | Paquete destino (FastAPI) |
|---|---|---|
| ~~CU-15, CU-31 proveedores~~ (hechos en la Fase B) | `suppliers` | `primer_parcial/proveedores` |
| ~~CU-16, CU-17, CU-18, CU-19 catálogo y promociones~~ (hechos en la Fase A) | `catalog`, `promotions` | `primer_parcial/catalogo` |
| CU-08, CU-11, CU-12, CU-32 carrito, compra y pagos | `orders`, `payments` | P6/P7 |
| CU-24, CU-25 reservas de sucursal | `reservations` | P6 |
| CU-27, CU-28, CU-30 ventas y punto de venta | `pos`, `orders` | P7 |
| CU-06, CU-07 vestidor virtual (RA) y asistente IA | `infer_service`, `ai` | P9 |

Riesgo a planificar: el vestidor virtual del móvil está en React Native; en Flutter requiere cámara + estimación de pose
(el servicio de inferencia en Python puede reutilizarse tal cual detrás de la API).

# Pendientes por lote

El Lote 1 (núcleo multitenant) está implementado y probado. El resto del documento se construye sobre esta base:
**toda tabla nueva lleva `empresa_id`, todo repositorio nuevo hereda de `TenantRepository`, y toda ruta de empresa usa `contexto_operativo(...)`.**

## Lote 2 — Operación comercial por empresa y offline
~~CU-01, CU-03, CU-04~~ (hechos en la Fase A), ~~CU-05~~ (hecho en la Fase B), ~~CU-09~~ (hecho en la Fase C), ~~CU-29~~ (hecho en la Fase E), ~~CU-36~~ (hecho en la Fase G), ~~CU-37, CU-38, CU-39~~ (hechos en la Fase H) → paquetes P4 catálogo, P5 inventario, P6 reservas, P7 ventas, P8 offline/sincronización.
- Web: IndexedDB ya tiene los almacenes `catalogo`, `operaciones` y `cache_meta` (`core/offline/local-db.service.ts`).
- Móvil: SQLite ya tiene las tablas `productos_locales` y `operaciones_pendientes` con los estados de RN11 (`lib/core/db/local_database.dart`).
- Gancho de CU-14 (desactivar con pendientes): ya cubre las reservas; la cola offline (CU-38) debe registrar el suyo con `sucursales/publico.py::registrar_verificador_de_pendientes`.

## Lote 3 — Gestión avanzada
~~CU-10~~, ~~CU-20~~, ~~CU-21~~, ~~CU-22~~, ~~CU-23~~, ~~CU-26~~ (hechos en la Fase B), ~~CU-41~~ (hecho en la Fase F), ~~CU-40~~ (hecho en la Fase H), ~~CU-42~~ (hecho en la Fase G) → P7 devoluciones, P9 IA/analítica, P10 reportes.
- RN07 ya está resuelta: proteger los endpoints de IA con `Depends(exigir_funcionalidad("reportes_ia"))`.

## Casos de uso conservados del primer parcial (deben funcionar dentro de cada empresa)
El código base del primer parcial es Django/React Native; se **porta** a FastAPI/Flutter agregando `empresa_id`:

| CU conservados | App del backend base (Django) | Paquete destino (FastAPI) |
|---|---|---|
| ~~CU-15, CU-31 proveedores~~ (hechos en la Fase B) | `suppliers` | `primer_parcial/proveedores` |
| ~~CU-16, CU-17, CU-18, CU-19 catálogo y promociones~~ (hechos en la Fase A) | `catalog`, `promotions` | `primer_parcial/catalogo` |
| ~~CU-08, CU-11, CU-12, CU-32 carrito, compra y pagos~~ (hechos en la Fase D) | `orders`, `payments` | `primer_parcial/reservas` y `primer_parcial/ventas` |
| ~~CU-24, CU-25 reservas de sucursal~~ (hechos en la Fase C) | `reservations` | `primer_parcial/reservas` |
| ~~CU-27, CU-28, CU-30 ventas y punto de venta~~ (hechos en la Fase E) | `pos`, `orders` | `primer_parcial/ventas` y `primer_parcial/reportes` |
| ~~CU-06 vestidor virtual (RA)~~ (hecho en la Fase I; falta medir FPS en un celular); ~~CU-07 asistente IA~~ (hecho en la Fase G) | `infer_service`, `ai` | P9 |

Riesgo a planificar: el vestidor virtual del móvil está en React Native; en Flutter requiere cámara + estimación de pose
(el servicio de inferencia en Python puede reutilizarse tal cual detrás de la API).

## Despliegue (Prompt L): lo que falta del lado del equipo

El código y la guía están listos (`docs/DESPLIEGUE.md`). Falta: crear las cuentas y las claves (Railway, Brevo, Stripe de prueba, Google AI Studio, Firebase), desplegar, y comprobar con las claves reales el correo, el pago de prueba, la IA y el push (web y móvil). Sin cada clave, esa función sigue en modo simulado.

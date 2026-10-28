# Trazabilidad requisitos → casos de uso → código → pruebas

Los mensajes de error, reglas (RN) y rutas REST del código son los del documento (fichas de CU, 2.4 y 5.2.1).
Las pruebas replican los pasos de las secciones 5.2.1 y 5.3.1.

Hay dos tablas, igual que las dos zonas de código: **SaaS** (`backend/app/modules`) y **Primer parcial (Anexo B)**
(`backend/app/primer_parcial`). El plan por fases está en `docs/PLAN_PRIMER_PARCIAL.md`.

## SaaS (CU nuevos o modificados)

| CU | Backend (`backend/app/modules/…`) | Rutas REST | Web (`frontend/src/app/features/…`) | Móvil | Pruebas (`backend/tests/`) |
|---|---|---|---|---|---|
| CU-02 Iniciar sesión | `acceso/cu02_login` | `POST /api/auth/login`, `POST /api/auth/refresh`, `GET /api/auth/me` | `auth/login.page.ts` + `core/auth/*` | `features/auth/*` | `test_cu02_login.py` (7 pasos + inactiva, refresh) |
| CU-13 Usuarios y roles | `acceso/cu13_usuarios` | `GET/POST /api/usuarios`, `PUT /api/usuarios/{id}`, `POST …/desactivar` | `administracion/usuarios.page.ts` | — | `test_cu13_usuarios.py` (7 pasos) |
| CU-14 Ciudades y sucursales | `sucursales/cu14_sucursales` | `GET/POST /api/sucursales`, `PUT …/{id}`, `POST …/activar`, `…/desactivar`, `GET/POST /api/ciudades` | `administracion/sucursales.page.ts` | — | `test_cu14_sucursales.py` (7 pasos) |
| CU-33 Empresas (tenants) | `plataforma/cu33_empresas` | `GET/POST /api/plataforma/empresas`, `PUT …/{id}`, `POST …/suspender`, `…/reactivar` (+ `DELETE` rechazado) | `plataforma/empresas.page.ts` | — | `test_cu33_empresas.py` (6 pasos) |
| CU-34 Planes | `plataforma/cu34_planes` | `GET/POST /api/plataforma/planes`, `PUT …/{id}`, `POST …/inactivar` | `plataforma/planes.page.ts` | — | `test_cu34_planes.py` (5 pasos) |
| CU-35 Suscripciones | `plataforma/cu35_suscripciones` | `GET …/empresas/{id}/suscripcion`, `POST …/suscripciones`, `POST …/suscripcion/suspender` | `plataforma/suscripcion.page.ts` | — | `test_cu35_suscripciones.py` (6 pasos) |
| Aislamiento multitenant (5.3.1) | `core/tenant.py` (`TenantRepository`) | todas las rutas de empresa | — | — | `test_aislamiento_multitenant.py` (4 pruebas + 3 flujos) |

Pendientes del SaaS, por fase (se agregan a esta tabla al construirlos):
CU-01 (A) · CU-03, CU-04 (A) · CU-05, CU-20, CU-26 (B) · CU-09, CU-10 (C) · CU-29 (E) · CU-41 (F) ·
CU-21, CU-22, CU-23, CU-42, CU-36 (G) · CU-37 a CU-40 (H).

## Primer parcial (Anexo B)

Casos de uso conservados; solo se les agrega `empresa_id`. Backend en `backend/app/primer_parcial/<paquete>/cuNN_<nombre>/`,
web en `frontend/src/app/features/primer-parcial/<paquete>/`, móvil en `movil/lib/primer_parcial/<paquete>/`,
pruebas en `backend/tests/primer_parcial/`.

| Paquete | CU | Backend | Rutas REST | Web | Móvil | Pruebas |
|---|---|---|---|---|---|---|
| proveedores (P3) | CU-15 Proveedores | — | — | — | — | — |
| proveedores (P3) | CU-31 Productos y abastecimiento | — | — | — | — | — |
| catalogo (P4) | CU-16 Categorías, tallas y colores | — | — | — | — | — |
| catalogo (P4) | CU-17 Temporadas y colecciones | — | — | — | — | — |
| catalogo (P4) | CU-18 Productos con variantes | — | — | — | — | — |
| catalogo (P4) | CU-19 Promociones | — | — | — | — | — |
| reservas (P6) | CU-08 Carrito | — | — | — | — | — |
| reservas (P6) | CU-24 Reservas de la sucursal | — | — | — | — | — |
| reservas (P6) | CU-25 Recepción y atención | — | — | — | — | — |
| ventas (P7) | CU-11 Compra digital | — | — | — | — | — |
| ventas (P7) | CU-12 Historial de compras | — | — | — | — | — |
| ventas (P7) | CU-28 Productos en caja | — | — | — | — | — |
| ventas (P7) | CU-30 Pago en caja y comprobante | — | — | — | — | — |
| ventas (P7) | CU-32 Pago electrónico | — | — | — | — | — |
| reportes (P10) | CU-27 Ventas de la sucursal | — | — | — | — | — |
| ia (P9) | CU-06 Vestidor virtual (RA) | — | — | — | — | — |
| ia (P9) | CU-07 Asistente y recomendador | — | — | — | — | — |

## Reglas de dependencia entre paquetes

Los paquetes se hablan solo por `publico.py` y sin ciclos; lo verifica `tests/test_arquitectura_paquetes.py`.
Excepción conocida del lote 1: `acceso`, `plataforma` y `sucursales` se importan entre sí (token, empresa y suscripción).
Ningún paquete nuevo puede volver hacia ellos ni importar archivos internos de otro paquete.

## Arquitectura (RNF07: presentación / negocio / persistencia / sincronización)
Cada caso de uso es una carpeta con `router.py` (presentación REST), `service.py` (reglas de negocio), `repository.py`
(persistencia) y `schemas.py` (contratos de entrada/salida). Los paquetes se comunican por su interfaz pública
(`plataforma/publico.py`, `sucursales/publico.py`), nunca por sus repositorios.

## Mecanismo de aislamiento por empresa (4.2.4)
1. El token JWT (firmado) lleva `empresa_id`; se resuelve el usuario contra la base en cada petición (`acceso/dependencias.py`).
2. `contexto_operativo(rol)` verifica rol, empresa activa y suscripción vigente (RN05) antes de ejecutar el caso de uso.
3. `TenantRepository` agrega `empresa_id = <empresa del token>` a **toda** consulta: un recurso de otra empresa devuelve 404.

## Reglas verificadas por pruebas automáticas
RN02 aislamiento · RN03 único administrador · RN05 suscripción vigente/vencimiento automático · RN06 límite de sucursales ·
RN07 funcionalidad por plan (`exigir_funcionalidad("reportes_ia")`) · RN08 cambio de plan vs. sucursales activas · RN09 código de empresa y correo único por empresa.

## Extensión de CU-02: recuperación de contraseña (fuera del documento aprobado)

| Ruta | Código | Pruebas |
|---|---|---|
| `POST /api/auth/olvide-password` (respuesta siempre genérica, no revela si la cuenta existe) | `backend/app/modules/acceso/cu02_login/service.py`, `backend/app/core/correo.py` (Brevo; sin `BREVO_API_KEY` imprime el enlace en consola) | `tests/test_cu02_login.py` (07–10) |
| `POST /api/auth/restablecer-password` (token de un solo uso, vence en 60 min, se guarda solo su hash) | tabla `restablecimientos_password` (migración 0002) | ídem |
| Web: `/olvide-password`, `/restablecer-password?token=…` y ojito de mostrar contraseña | `frontend/src/app/features/auth/*`, `core/ui/password-field.component.ts` | prueba en navegador |

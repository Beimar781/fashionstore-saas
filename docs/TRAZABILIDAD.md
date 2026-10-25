# Trazabilidad requisitos → casos de uso → código → pruebas (Lote 1)

Los mensajes de error, reglas (RN) y rutas REST del código son los del documento (fichas de CU, 2.4, 4.4.3 y 5.2.1).
El backend implementa **todas** las rutas de la tabla 4.4.3 del documento (26) y las pruebas replican los pasos de la sección 5.2.1 y 5.3.1.

| CU | Backend (`backend/app/modules/…`) | Rutas REST | Web (`frontend/src/app/features/…`) | Móvil | Pruebas (`backend/tests/`) |
|---|---|---|---|---|---|
| CU-02 Iniciar sesión | `acceso/cu02_login` | `POST /api/auth/login`, `POST /api/auth/refresh`, `GET /api/auth/me` | `auth/login.page.ts` + `core/auth/*` | `features/auth/*` | `test_cu02_login.py` (7 pasos + inactiva, refresh) |
| CU-13 Usuarios y roles | `acceso/cu13_usuarios` | `GET/POST /api/usuarios`, `PUT /api/usuarios/{id}`, `POST …/desactivar` | `administracion/usuarios.page.ts` | — | `test_cu13_usuarios.py` (7 pasos) |
| CU-14 Ciudades y sucursales | `sucursales/cu14_sucursales` | `GET/POST /api/sucursales`, `PUT …/{id}`, `POST …/activar`, `…/desactivar`, `GET/POST /api/ciudades` | `administracion/sucursales.page.ts` | — | `test_cu14_sucursales.py` (7 pasos) |
| CU-33 Empresas (tenants) | `plataforma/cu33_empresas` | `GET/POST /api/plataforma/empresas`, `PUT …/{id}`, `POST …/suspender`, `…/reactivar` (+ `DELETE` rechazado) | `plataforma/empresas.page.ts` | — | `test_cu33_empresas.py` (6 pasos) |
| CU-34 Planes | `plataforma/cu34_planes` | `GET/POST /api/plataforma/planes`, `PUT …/{id}`, `POST …/inactivar` | `plataforma/planes.page.ts` | — | `test_cu34_planes.py` (5 pasos) |
| CU-35 Suscripciones | `plataforma/cu35_suscripciones` | `GET …/empresas/{id}/suscripcion`, `POST …/suscripciones`, `POST …/suscripcion/suspender` | `plataforma/suscripcion.page.ts` | — | `test_cu35_suscripciones.py` (6 pasos) |
| Aislamiento multitenant (5.3.1) | `core/tenant.py` (`TenantRepository`) | todas las rutas de empresa | — | — | `test_aislamiento_multitenant.py` (4 pruebas + 3 flujos) |

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

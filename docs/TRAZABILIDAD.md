# Trazabilidad requisitos → casos de uso → código → pruebas

Los mensajes de error, reglas (RN) y rutas REST del código son los del documento (fichas de CU, 2.4 y 5.2.1).
Las pruebas replican los pasos de las secciones 5.2.1 y 5.3.1.

Hay dos tablas, igual que las dos zonas de código: **SaaS** (`backend/app/modules`) y **Primer parcial (Anexo B)**
(`backend/app/primer_parcial`). El plan por fases está en `docs/PLAN_PRIMER_PARCIAL.md`.

## SaaS (CU nuevos o modificados)

| CU | Backend (`backend/app/modules/…`) | Rutas REST | Web (`frontend/src/app/features/…`) | Móvil | Pruebas (`backend/tests/`) |
|---|---|---|---|---|---|
| CU-01 Registrar cuenta de cliente | `acceso/cu01_registro_cliente` | `POST /api/auth/registro` | `auth/registro.page.ts` | — | `test_cu01_registro_cliente.py` (7 pruebas) |
| CU-02 Iniciar sesión | `acceso/cu02_login` | `POST /api/auth/login`, `POST /api/auth/refresh`, `GET /api/auth/me` | `auth/login.page.ts` + `core/auth/*` | `features/auth/*` | `test_cu02_login.py` (7 pasos + inactiva, refresh) |
| CU-03 Consultar catálogo de prendas | `catalogo/cu03_consultar_catalogo` | `GET /api/catalogo/productos`, `…/productos/{id}`, `…/productos/{id}/opciones?sucursal=`, `…/sucursales` | `catalogo/catalogo.page.ts`, `catalogo/prenda.page.ts` | — | `test_cu03_consultar_catalogo.py` (12 pruebas: orden de tallas, disponibilidad en una consulta, aislamiento) |
| CU-04 Buscar y filtrar prendas | `catalogo/cu04_buscar_filtrar` | `GET /api/catalogo/buscar` (q, categoría, marca, género, temporada, colección, talla, color, precio, sucursal, orden, paginación) | `catalogo/catalogo.page.ts` | — | `test_cu04_buscar_filtrar.py` (10 pruebas: talla+color sobre la misma variante, sucursal con stock) |
| CU-05 Tallas, colores y disponibilidad por sucursal | `inventario/cu05_disponibilidad` | `GET /api/inventario/productos/{id}/disponibilidad` | `catalogo/prenda.page.ts` (sección «Disponibilidad por sucursal») | — | `test_cu05_disponibilidad.py` (7 pruebas: una consulta agrupada, orden de tallas, aislamiento) |
| CU-13 Usuarios y roles | `acceso/cu13_usuarios` | `GET/POST /api/usuarios`, `PUT /api/usuarios/{id}`, `POST …/desactivar` | `administracion/usuarios.page.ts` | — | `test_cu13_usuarios.py` (7 pasos) |
| CU-14 Ciudades y sucursales | `sucursales/cu14_sucursales` | `GET/POST /api/sucursales`, `PUT …/{id}`, `POST …/activar`, `…/desactivar`, `GET/POST /api/ciudades` | `administracion/sucursales.page.ts` | — | `test_cu14_sucursales.py` (7 pasos) |
| CU-20 Consultar inventario global | `inventario/cu20_inventario_global` | `GET /api/inventario/global` (q, categoría, temporada, estado, sucursal, paginación) | `inventario/inventario.page.ts` (Administrador) | — | `test_cu20_inventario_global.py` (8 pruebas: disponibles, reservadas, vendidas, agotadas, próximas a ingresar) |
| CU-26 Gestionar disponibilidad e inventario de la sucursal | `inventario/cu26_inventario_sucursal` (+ `publico.py::aplicar_movimientos`, único camino para cambiar existencias) | `GET /api/inventario/sucursal`, `POST …/sucursal/movimientos`, `PUT …/sucursal/variantes/{id}/umbral`, `GET /api/inventario/movimientos`, `GET /api/inventario/recepciones`, `POST …/recepciones/{lote}/recibir` | `inventario/inventario.page.ts`, `recepciones.page.ts`, `movimientos.page.ts` (Encargado) | — | `test_cu26_inventario_sucursal.py` (15 pruebas: ajustes, bitácora, recepción de lotes, núcleo de movimientos) |
| CU-33 Empresas (tenants) | `plataforma/cu33_empresas` | `GET/POST /api/plataforma/empresas`, `PUT …/{id}`, `POST …/suspender`, `…/reactivar` (+ `DELETE` rechazado) | `plataforma/empresas.page.ts` | — | `test_cu33_empresas.py` (6 pasos) |
| CU-34 Planes | `plataforma/cu34_planes` | `GET/POST /api/plataforma/planes`, `PUT …/{id}`, `POST …/inactivar` | `plataforma/planes.page.ts` | — | `test_cu34_planes.py` (5 pasos) |
| CU-35 Suscripciones | `plataforma/cu35_suscripciones` | `GET …/empresas/{id}/suscripcion`, `POST …/suscripciones`, `POST …/suscripcion/suspender` | `plataforma/suscripcion.page.ts` | — | `test_cu35_suscripciones.py` (6 pasos) |
| Aislamiento multitenant (5.3.1) | `core/tenant.py` (`TenantRepository`) | todas las rutas de empresa | — | — | `test_aislamiento_multitenant.py` (4 pruebas + 3 flujos) |

Pendientes del SaaS, por fase (se agregan a esta tabla al construirlos):
CU-09, CU-10 (C) · CU-29 (E) · CU-41 (F) ·
CU-21, CU-22, CU-23, CU-42, CU-36 (G) · CU-37 a CU-40 (H).

## Primer parcial (Anexo B)

Casos de uso conservados; solo se les agrega `empresa_id`. Backend en `backend/app/primer_parcial/<paquete>/cuNN_<nombre>/`,
web en `frontend/src/app/features/primer-parcial/<paquete>/`, móvil en `movil/lib/primer_parcial/<paquete>/`,
pruebas en `backend/tests/primer_parcial/`.

| Paquete | CU | Backend | Rutas REST | Web | Móvil | Pruebas |
|---|---|---|---|---|---|---|
| proveedores (P3) | CU-15 Proveedores | `proveedores/cu15_proveedores` | `GET/POST /api/proveedores`, `GET/PUT …/{id}`, `POST …/{id}/activar`, `…/desactivar`, `POST …/{id}/acceso`; `PUT /api/colecciones/{id}/proveedor` | `primer-parcial/proveedores/proveedores.page.ts` | — | `primer_parcial/test_cu15_proveedores.py` (5 pasos + 5) |
| proveedores (P3) | CU-31 Productos y abastecimiento | `proveedores/cu31_abastecimiento` (+ `publico.py`: lotes en tránsito y recepción) | `POST/GET /api/abastecimiento/lotes`, `GET …/lotes/{id}`, `POST …/lotes/{id}/cancelar`, `POST/GET …/propuestas`, `POST …/propuestas/{id}/aprobar`, `…/rechazar`, `GET …/resumen`, `…/mi-proveedor`, `…/sucursales`, `…/variantes` | `primer-parcial/proveedores/abastecimiento.page.ts` (Administrador y portal del Proveedor) | — | `primer_parcial/test_cu31_abastecimiento.py` (5 pasos + 9) |
| catalogo (P4) | CU-16 Categorías, tallas y colores | `catalogo/cu16_categorias_tallas_colores` | `GET/POST /api/categorias`, `PUT/DELETE …/{id}`; `GET/POST /api/grupos-talla`, `DELETE …/{id}`; `POST /api/tallas`, `PUT/DELETE …/{id}`; `GET/POST /api/colores`, `PUT/DELETE …/{id}`; `GET/POST /api/marcas`, `DELETE …/{id}` | `primer-parcial/catalogo/atributos.page.ts` | — | `primer_parcial/test_cu16_categorias_tallas_colores.py` (5 pasos + 6) |
| catalogo (P4) | CU-17 Temporadas y colecciones | `catalogo/cu17_temporadas_colecciones` | `GET/POST /api/temporadas`, `PUT/DELETE …/{id}`; `GET/POST /api/colecciones`, `PUT/DELETE …/{id}` | `primer-parcial/catalogo/temporadas.page.ts` | — | `primer_parcial/test_cu17_temporadas_colecciones.py` (5 pasos + 3) |
| catalogo (P4) | CU-18 Productos con variantes | `catalogo/cu18_productos` | `GET/POST /api/productos`, `GET/PUT …/{id}`, `POST …/{id}/activar`, `…/desactivar`, `POST …/{id}/variantes`, `PUT …/{id}/variantes/{vid}`, `POST …/{id}/imagenes`, `…/imagenes/{iid}/principal`, `DELETE …/imagenes/{iid}` | `primer-parcial/catalogo/productos.page.ts`, `producto-detalle.page.ts` | — | `primer_parcial/test_cu18_productos.py` (5 pasos + 6: SKU corto, talla de otro grupo, imagen por contenido) |
| catalogo (P4) | CU-19 Promociones | `catalogo/cu19_promociones` (+ `publico.py::descuentos_vigentes` para catálogo y POS) | `GET/POST /api/promociones`, `PUT/DELETE …/{id}` | `primer-parcial/catalogo/promociones.page.ts` | — | `primer_parcial/test_cu19_promociones.py` (6 pasos + 6) |
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

## Esquema de la Fase A (migración 0003)

`grupos_talla`, `tallas`, `categorias`, `marcas`, `colores`, `temporadas`, `colecciones`, `productos`, `variantes`, `imagenes_producto`,
`promociones` (+ `promocion_categorias`, `promocion_colecciones`, `promocion_productos`) y `existencias`. Todas llevan `empresa_id`
y los únicos son por empresa (`slug`, `sku`, `codigo`, `nombre`). `existencias` es la base de CU-05 (la Fase B la amplía con movimientos).
`colecciones.proveedor_id` queda sin FK hasta CU-15 (Fase B). Las imágenes se guardan en `backend/media/<empresa_id>/productos/<producto_id>/`.

## Esquema de la Fase B (migración 0004)

`proveedores`, `lotes_abastecimiento` + `lote_items` (aviso de remisión: EN_TRANSITO → RECIBIDO | CANCELADO), `propuestas_producto`
(PENDIENTE → APROBADA | RECHAZADA) y `movimientos_inventario` (bitácora: solo se agregan filas). `existencias` gana `umbral_minimo`,
`colecciones.proveedor_id` recibe su FK y se agrega el rol **Proveedor** (actor con portal propio).

Estados de existencias: *disponible*, *reservada* y *vendida* son columnas de `existencias`; *agotada* es disponible = 0; *próxima a ingresar*
sale de los lotes EN_TRANSITO (`proveedores/publico.py::en_transito_por_variante`). Cada tipo de movimiento mueve unidades entre esos estados
(`cu26…/service.py::EFECTOS`): reserva, venta y devolución ya quedan listos para las fases C a F.

Flujo del abastecimiento: el Proveedor (o el Administrador) crea el aviso con SKUs reales → el lote queda *En tránsito* y aparece en el resumen
de la administración → el Encargado de la sucursal destino cuenta lo que llegó y lo recibe → `aplicar_movimientos` suma las unidades
(tipo ENTRADA_RECEPCION, referencia RECEPCION) y el lote pasa a *Recibido*. Las propuestas de producto las aprueba o rechaza el Administrador.

## Errores del primer parcial que se corrigieron (sección 9 del plan) y su prueba

| Error | Dónde se resuelve | Prueba |
|---|---|---|
| Talla y color filtrados sobre variantes distintas | `cu04…/repository.py`: una sola condición `EXISTS` sobre la variante activa | `test_cu04…::test_04_talla_y_color_se_aplican_a_la_misma_variante` |
| Disponibilidad ignoraba variantes inactivas y hacía una consulta por variante | `inventario/publico.py::disponible_por_variante` (una consulta agrupada) | `test_cu04…::test_05…`, `test_cu03…::test_06…` y `::test_07…` |
| SKU frágil (slug editable, 32 caracteres) | SKU `P{id}-{talla}-{código corto del color}`, único por empresa | `test_cu18…::test_sku_corto_y_unico_aunque_los_nombres_sean_largos` |
| Tallas de otro grupo | `cu18…/service.py::_validar_variantes` | `test_cu18…::test_talla_de_otro_grupo_se_rechaza` |
| Tallas fuera de orden | siempre por `orden` (display_order) | `test_cu03…::test_04…` |
| Web y móvil con lógica distinta de disponibilidad | un solo `GET /api/catalogo/productos/{id}/opciones?sucursal=`; la web solo dibuja | `test_cu03…::test_04…` a `::test_06…` |
| Selección que se perdía al cambiar de color / color agotado elegible | `prenda.page.ts` (talla por código; colores y tallas sin stock deshabilitados) | prueba en navegador |

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

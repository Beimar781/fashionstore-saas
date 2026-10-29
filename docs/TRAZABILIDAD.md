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
| CU-09 Realizar reserva de múltiples prendas | `reservas/cu09_reservar` (+ motor del ciclo de vida de la reserva: `cambiar_estado`, `liberar`, `expirar_vencidas`) | `POST /api/reservas` | `reservas/reservar.page.ts`, botón «Agregar a mi reserva» en `catalogo/prenda.page.ts` | — | `test_cu09_reservar.py` (15 pruebas: stock todo o nada, horario, aislamiento, gancho de CU-14) |
| CU-10 Consultar y cancelar reservas | `reservas/cu10_consultar_cancelar` | `GET /api/reservas`, `GET …/{id}`, `POST …/{id}/cancelar` | `reservas/mis-reservas.page.ts` | — | `test_cu10_reservas_cliente.py` (11 pruebas: cancelar devuelve stock, expiración, reserva ajena) |
| RF11 Notificar las reservas a la sucursal | `reservas/rf11_notificaciones` (`notificar()` la usan CU-09, 10, 24 y 25) | `GET /api/notificaciones`, `GET …/resumen`, `POST …/{id}/leer`, `POST …/leer-todas` | `core/ui/notificaciones.component.ts` (campana de la barra superior) | — | `test_rf11_notificaciones.py` (8 pruebas: quién ve qué, lectura, aislamiento) |
| CU-13 Usuarios y roles | `acceso/cu13_usuarios` | `GET/POST /api/usuarios`, `PUT /api/usuarios/{id}`, `POST …/desactivar` | `administracion/usuarios.page.ts` | — | `test_cu13_usuarios.py` (7 pasos) |
| CU-14 Ciudades y sucursales | `sucursales/cu14_sucursales` | `GET/POST /api/sucursales`, `PUT …/{id}`, `POST …/activar`, `…/desactivar`, `GET/POST /api/ciudades` | `administracion/sucursales.page.ts` | — | `test_cu14_sucursales.py` (7 pasos) |
| CU-20 Consultar inventario global | `inventario/cu20_inventario_global` | `GET /api/inventario/global` (q, categoría, temporada, estado, sucursal, paginación) | `inventario/inventario.page.ts` (Administrador) | — | `test_cu20_inventario_global.py` (8 pruebas: disponibles, reservadas, vendidas, agotadas, próximas a ingresar) |
| CU-26 Gestionar disponibilidad e inventario de la sucursal | `inventario/cu26_inventario_sucursal` (+ `publico.py::aplicar_movimientos`, único camino para cambiar existencias) | `GET /api/inventario/sucursal`, `POST …/sucursal/movimientos`, `PUT …/sucursal/variantes/{id}/umbral`, `GET /api/inventario/movimientos`, `GET /api/inventario/recepciones`, `POST …/recepciones/{lote}/recibir` | `inventario/inventario.page.ts`, `recepciones.page.ts`, `movimientos.page.ts` (Encargado) | — | `test_cu26_inventario_sucursal.py` (15 pruebas: ajustes, bitácora, recepción de lotes, núcleo de movimientos) |
| CU-29 Registrar venta presencial | `ventas/cu29_venta_presencial` (usa `primer_parcial/ventas/publico.py`) | `POST /api/caja/ventas`, `GET …/ventas/pendientes`, `GET/DELETE …/ventas/{id}`, `GET /api/caja/reservas/{codigo}` | `primer-parcial/ventas/caja.page.ts` (Cajero en `/pos/caja`, Encargado en `/sucursal/caja`) | — | `test_cu29_venta_presencial.py` (15 pruebas: stock de la sucursal del cajero, desde una reserva, aislamiento) |
| CU-41 Gestionar devoluciones y cambios | `ventas/cu41_devoluciones` (+ `nota.py`, PDF; reembolso por `pasarela_para` del CU-32) | `GET /api/devoluciones/venta?comprobante=`, `POST /api/devoluciones`, `GET /api/devoluciones`, `GET …/{id}`, `GET …/{id}/nota`, `POST …/diferencia` (cobro con tarjeta de la diferencia de un cambio), `GET/PUT …/configuracion` (plazo) | `ventas/devoluciones.page.ts` (Cajero en `/pos/devoluciones`, Encargado en `/sucursal/devoluciones`), `ventas/devoluciones-admin.page.ts` (Administrador) | — | `test_cu41_devoluciones.py` (20 pruebas: comprobante, plazo, parcial y repetida, reembolso por medio, fallo de pasarela, aislamiento, roles), `test_cu41_cambios.py` (13: diferencia en efectivo o con tarjeta, tarjeta rechazada, sin stock, Stripe simulado, reporte) |
| CU-21 Reportes de ventas y reservas | `reportes/cu21_ventas_y_reservas` (+ `reportes/base.py` y `repository.py`, que comparten CU-22 y CU-23) | `GET /api/reportes/ventas`, `…/reservas`, `…/pagos`, `…/exportar/{ventas,reservas,pagos}` (CSV) | `reportes/reportes.page.ts` | — | `test_cu21_reportes.py` (9 pruebas: netas de devoluciones, canal, periodo, reservas, vista de pagos, CSV, plan, aislamiento) |
| CU-22 Indicadores empresariales | `reportes/cu22_indicadores` | `GET /api/reportes/indicadores?dias=&sucursal=` | `reportes/indicadores.page.ts` | — | `test_cu22_indicadores.py` (5 pruebas: KPIs, variación contra el periodo anterior, stock bajo, plan, aislamiento) |
| CU-23 Reportes generativos por prompt y por voz | `ia/cu23_reportes_generativos` (`interprete.py`: IA externa o reglas; `core/ia.py`: adaptador de Claude) | `POST /api/ia/reportes`, `GET /api/ia/reportes`, `GET …/{id}` | `ia/reporte-generativo.page.ts` (voz con la Web Speech API) | — | `test_cu23_reportes_generativos.py` (12 pruebas: reglas, IA con doble en memoria, respaldo, validación, historial, plan, aislamiento) |
| CU-36 Plan, límites y uso de la empresa | `plataforma/cu36_plan_y_uso` (+ registro de medidores en `plataforma/publico.py`) | `GET /api/mi-plan` | `administracion/mi-plan.page.ts` | — | `test_cu36_plan_y_uso.py` (6 pruebas: plan, límite de sucursales, consumo, vencimiento, suscripción vencida, aislamiento) |
| CU-42 Dashboard analítico con Machine Learning | `ia/cu42_analitica_ml` (scikit-learn: KMeans y regresión lineal) | `GET /api/ia/analitica?sucursal=` | `ia/analitica.page.ts` | — | `test_cu42_analitica_ml.py` (8 pruebas: rotación, pronóstico, recomendación, sin datos, plan, aislamiento) |
| CU-33 Empresas (tenants) | `plataforma/cu33_empresas` | `GET/POST /api/plataforma/empresas`, `PUT …/{id}`, `POST …/suspender`, `…/reactivar` (+ `DELETE` rechazado) | `plataforma/empresas.page.ts` | — | `test_cu33_empresas.py` (6 pasos) |
| CU-34 Planes | `plataforma/cu34_planes` | `GET/POST /api/plataforma/planes`, `PUT …/{id}`, `POST …/inactivar` | `plataforma/planes.page.ts` | — | `test_cu34_planes.py` (5 pasos) |
| CU-35 Suscripciones | `plataforma/cu35_suscripciones` | `GET …/empresas/{id}/suscripcion`, `POST …/suscripciones`, `POST …/suscripcion/suspender` | `plataforma/suscripcion.page.ts` | — | `test_cu35_suscripciones.py` (6 pasos) |
| Aislamiento multitenant (5.3.1) | `core/tenant.py` (`TenantRepository`) | todas las rutas de empresa | — | — | `test_aislamiento_multitenant.py` (4 pruebas + 3 flujos) |

Pendientes del SaaS, por fase (se agregan a esta tabla al construirlos):
CU-37 a CU-40 (H).

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
| reservas (P6) | CU-08 Carrito | `reservas/cu08_carrito` (+ `publico.py`: `CarritoService` para el checkout) | `GET /api/carrito`, `POST …/items`, `PUT/DELETE …/items/{id}`, `PUT …/sucursal`, `DELETE /api/carrito` | `primer-parcial/reservas/carrito.page.ts`, botón «Agregar al carrito» en `catalogo/prenda.page.ts` | — | `primer_parcial/test_cu08_carrito.py` (6 pasos + 10) |
| reservas (P6) | CU-24 Reservas de la sucursal | `reservas/cu24_gestionar_reservas_sucursal` | `GET /api/reservas-sucursal`, `GET …/{id}`, `POST …/{id}/preparar`, `POST …/{id}/items/{item}/no-encontrado` | `primer-parcial/reservas/reservas-sucursal.page.ts` | — | `primer_parcial/test_cu24_gestionar_reservas_sucursal.py` (5 pasos + 5) |
| reservas (P6) | CU-25 Recepción y atención | `reservas/cu25_confirmar_atencion` | `POST /api/atencion-reservas/validar`, `POST …/{id}/atender`, `POST …/{id}/completar` | `primer-parcial/reservas/atencion.page.ts` | — | `primer_parcial/test_cu25_confirmar_atencion.py` (5 pasos + 4) |
| ventas (P7) | CU-11 Compra digital | `ventas/cu11_compra_digital` (+ `finalizar()`: stock, comprobante y carrito al aprobarse el pago) | `POST /api/compras/checkout` | `primer-parcial/ventas/checkout.page.ts` | — | `primer_parcial/test_cu11_compra_digital.py` (5 pasos + 9: stock al pagar, no se cobra sin stock) |
| ventas (P7) | CU-12 Historial de compras | `ventas/cu12_historial_compras` (+ `comprobante.py`, PDF) | `GET /api/compras`, `GET …/{id}`, `GET …/{id}/comprobante` | `primer-parcial/ventas/mis-compras.page.ts`, `compra-detalle.page.ts` | — | `primer_parcial/test_cu12_historial_compras.py` (5 pasos + 5) |
| ventas (P7) | CU-28 Productos en caja | `ventas/cu28_productos_en_caja` | `GET /api/caja/productos?q=`, `GET /api/caja/productos/codigo/{codigo}` | `primer-parcial/ventas/caja.page.ts` | — | `primer_parcial/test_cu28_productos_en_caja.py` (5 pasos + 2) |
| ventas (P7) | CU-30 Pago en caja y comprobante | `ventas/cu30_pago_en_caja` (+ `core/impuestos.py`, adaptador del servicio de impuestos; tarjeta por `cu32_pago_electronico`) | `POST /api/caja/ventas/{id}/cobrar` (efectivo), `GET …/{id}/comprobante`; con tarjeta `POST /api/pagos/pedidos/{id}/iniciar` y `…/{pago}/confirmar` | `primer-parcial/ventas/caja.page.ts`, `pago-tarjeta.component.ts` | — | `primer_parcial/test_cu30_pago_en_caja.py` (5 pasos + 11: sin stock a mitad del cobro, desde una reserva) |
| ventas (P7) | CU-32 Pago electrónico | `ventas/cu32_pago_electronico` (+ `pasarela.py`: Stripe de prueba o simulada) | `GET /api/pagos/config`, `GET/DELETE …/tarjetas`, `POST …/pedidos/{id}/iniciar`, `POST …/{id}/confirmar`, `POST …/{id}/reconciliar`, `GET …/{id}` | `primer-parcial/ventas/checkout.page.ts` (formulario de tarjeta y resultado), `core/pagos/stripe-js.service.ts` | — | `primer_parcial/test_cu32_pago_electronico.py` (5 pasos + 11), `test_cu32_pasarela_stripe.py` (10, con Stripe simulado en memoria) |
| reportes (P10) | CU-27 Ventas de la sucursal | `reportes/cu27_ventas_sucursal` | `GET /api/reportes/sucursal/resumen`, `GET …/ventas`, `GET …/ventas/{id}` | `primer-parcial/reportes/ventas-sucursal.page.ts` (Encargado) | — | `primer_parcial/test_cu27_ventas_sucursal.py` (5 pasos + 4) |
| ia (P9) | CU-06 Vestidor virtual (RA) | — | — | — | — | — |
| ia (P9) | CU-07 Asistente y recomendador | `ia/cu07_asistente` (usa la búsqueda del CU-04 vía `modules/catalogo/publico.py`) | `POST /api/asistente/chat`, `GET /api/asistente/recomendaciones`, `GET …/outfit`, `POST …/interacciones`, `GET/PUT …/privacidad`, `DELETE …/historial` | `primer-parcial/ia/asistente.page.ts`, `core/ia/aprendizaje.service.ts` (avisa lo que el cliente busca y mira desde `catalogo.page.ts` y `prenda.page.ts`) | — | `primer_parcial/test_cu07_asistente.py` (12 pruebas: reglas, IA con doble en memoria, stock, contexto, plan, aislamiento), `test_cu07_perfil.py` (13: perfil de gustos, motivos, ofertas, outfits, IA que elige y se valida, privacidad) |

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

## Esquema de la Fase C (migración 0005)

`reservas`, `reserva_items` y `notificaciones`. La reserva tiene un código `RSV-XXXXXXXX` único por empresa (sin 0, O, 1, I para dictarlo sin
errores), el horario aproximado de visita (`programada_para`) y su vigencia (`vence_en` = visita + 24 h, configurable).

Ciclo de vida de la reserva (todo cambio de estado y de stock pasa por `ReservaService`):

| Estado | Cómo se llega | Stock |
|---|---|---|
| PENDIENTE | CU-09 al reservar | pasa de *disponible* a *reservada* (movimiento RESERVA) |
| PREPARADA | CU-24 «Prendas preparadas» (avisa al cliente) | sigue reservada |
| EN_PROBADOR | CU-25 entrega las prendas y envía al probador | sigue reservada |
| COMPLETADA | CU-25 cuando el cliente no lleva nada (o CU-29 tras cobrar) | vuelve a disponible (LIBERA_RESERVA) |
| CANCELADA | CU-10 (cliente) o CU-24 si no queda ninguna prenda | vuelve a disponible |
| EXPIRADA | pasó `vence_en` sin atenderse | vuelve a disponible |

No hay tareas programadas: la expiración se aplica al consultar las reservas (cliente, sucursal, validar código) y al desactivar una sucursal,
así que el stock nunca queda apartado de más. Interpretación de CU-25: la ficha termina en «completado», pero también dice que si el cliente
lleva las prendas pasa a CU-29; por eso «completar» con *llevará prendas* deja la reserva en el probador con su stock apartado hasta el cobro.
CU-24, excepción «No encontrado en físico»: se libera la reserva y se descuenta la prenda del inventario (AJUSTE_SALIDA), con aviso de ajuste
de stock a la sucursal y disculpas al cliente. El gancho de CU-14 quedó activo: una sucursal con reservas activas no se desactiva
(`sucursales/publico.py::registrar_verificador_de_pendientes`, sin dependencia circular).

## Esquema de la Fase D (migración 0006)

`carritos` y `carrito_items` (un carrito por cliente y empresa, con su sucursal), `pedidos` y `pedido_items` (un solo pedido para todos los canales: la venta
de caja, CU-29, lo reutiliza; precios y nombres congelados), `pagos` (cada intento queda registrado, aprobado o no, para los reportes de pago),
`clientes_pasarela`, `tarjetas_guardadas` (marca, últimos 4 y vencimiento; nunca el número ni el CVC) y `secuencias_comprobante` (numeración por sucursal).
La migración también agrega `PEDIDO` como referencia válida de la bitácora de inventario.

Flujo de la compra digital:

| Paso | Qué ocurre | Dónde |
|---|---|---|
| 1 | El cliente agrega prendas; el stock se valida al agregar (no se aparta) | CU-08 `CarritoService.agregar` |
| 2 | «Proceder al pago»: el carrito se congela en un pedido PENDIENTE_PAGO con entrega y NIT/CI | CU-11 `CompraService.checkout` |
| 3 | Se vuelve a verificar el stock y se crea el intento de pago (Stripe: PaymentIntent de captura manual) | CU-32 `PagoService.iniciar` |
| 4 | El cliente ingresa la tarjeta y se ve si la pasarela aprueba (la tarjeta queda *autorizada*), rechaza (402) o no responde | CU-32 `PagoService.confirmar` |
| 5 | Si autorizó: se descuenta el stock de la sucursal (movimiento VENTA), se numera el comprobante y se vacía el carrito; **recién entonces se cobra** | CU-11 `finalizar` + `pasarela.capturar` |
| 5b | Si el stock se agotó mientras pagaba: se anula la autorización, el pago y el pedido quedan CANCELADOS y no se cobra | CU-32 `_aplicar` |

Sin `STRIPE_SECRET_KEY` y `STRIPE_PUBLISHABLE_KEY` en `backend/.env` se usa la pasarela simulada (solo tarjetas de prueba, ver `docs/MENSAJES_PENDIENTES_WORD.md`).
Con las dos claves de prueba, la web carga Stripe.js y el número de la tarjeta lo captura Stripe: nunca pasa por nuestro servidor. **El adaptador de Stripe
se probó con un Stripe simulado en memoria; no se probó contra Stripe real porque no hay claves en este entorno.**

## Esquema de la Fase E (migración 0007)

Sin tablas nuevas: la venta de caja es un **pedido** de canal PRESENCIAL y entrega EN_TIENDA (regla 15). La migración agrega `pedidos.reserva_id` (venta nacida de una
reserva, con un índice único para que una reserva tenga una sola venta abierta), `pedidos.comprobante_tipo` y `autorizacion_fiscal` (FACTURA o INTERNO_TEMPORAL),
`pagos.monto_recibido` y `cambio` (arqueo de caja) y amplía el `CHECK` de `pagos.metodo` con `QR` (la Fase F dejó de usar el QR: en tienda solo hay efectivo y tarjeta; el valor sigue permitido en la restricción).

Flujo de la venta de caja:

| Paso | Qué ocurre | Dónde |
|---|---|---|
| 1 | El cajero escanea el código de barras (o el SKU) o busca por nombre; ve talla, color, precio con promoción y el stock de **su** sucursal | CU-28 |
| 2 | Arma la pre-factura y registra la venta: queda PENDIENTE_PAGO, sin tocar el stock. Puede venir de una reserva preparada o en probador | CU-29 `VentaPresencialService.crear` |
| 3 | Cobra: efectivo (calcula el cambio) o tarjeta con la pasarela del CU-32 | CU-30 `CobroCajaService.cobrar` / CU-32 |
| 4 | `CompraService.finalizar`: descuenta el stock de la sucursal (movimiento VENTA, referencia VENTA; desde una reserva, VENTA_RESERVA), numera el comprobante `CMP-<sucursal>-<número>` y pide la autorización al servicio de impuestos | CU-11 `finalizar` |
| 4b | Si el stock se agotó a mitad del cobro: no se descuenta nada y no se registra ningún cobro (con tarjeta se anula la autorización) | `SinStock` |
| 5 | Si el servicio de impuestos no responde, la venta no se pierde: queda un comprobante interno temporal y se muestra el aviso de la ficha | `core/impuestos.py` |

El Encargado consulta el día en CU-27 (resumen, cierre de caja por método, efectivo esperado en caja, reservas completadas y tickets). El servicio de impuestos es
simulado; con `IMPUESTOS_SIMULAR_FALLA=true` en `backend/.env` se ve el comprobante interno temporal.

## Esquema de la Fase F (migración 0008)

Tablas nuevas: `intentos_diferencia` (cobro con tarjeta de la diferencia de un cambio: monto fijado por el servidor), `configuracion_ventas` (plazo de devolución por empresa, 15 días por defecto), `secuencias_nota_devolucion`, `devoluciones` (nota `NDV-<sucursal>-<número>`, tipo
DEVOLUCION o CAMBIO, montos, medio y referencia del reembolso, cobro de la diferencia) y `devolucion_items` (prendas DEVUELTAS y ENTREGADAS con su precio al momento de la venta).
No se tocó el CHECK de inventario: la referencia `DEVOLUCION` y el tipo `DEVOLUCION` ya existían (regla 14).

Flujo de una devolución o cambio:

| Paso | Qué ocurre | Dónde |
|---|---|---|
| 1 | Se busca la venta por su comprobante, solo de la sucursal del empleado (RN10); se ve lo ya devuelto, el plazo y con qué se pagó | CU-41 `DevolucionService.venta` |
| 2 | Se validan motivo, plazo, cantidades (nunca más de lo vendido menos lo ya devuelto) y, en un cambio, las prendas nuevas y la diferencia | `registrar`, `_a_devolver`, `_nuevas`, `_cobro_adicional` |
| 3 | Inventario: la prenda devuelta vuelve a *disponible* (DEVOLUCION) y la nueva sale (VENTA, referencia DEVOLUCION); sin stock para el cambio no se registra nada | `_mover_inventario` / `aplicar_movimientos` |
| 4 | Reembolso en el mismo medio del pago: efectivo en caja; tarjeta por la pasarela (Stripe de prueba o simulada), repartiendo los centavos para que la suma sea exacta. Si la pasarela falla, nada se registra | `_reembolsar` / `pasarela.reembolsar` |
| 4b | Cambio que vale más: la diferencia se paga en efectivo (con cambio) o con tarjeta: se inicia el cobro (`POST /diferencia`), la pasarela autoriza, se registra el cambio y recién entonces se captura; si falta stock se anula la autorización | `iniciar_diferencia`, `_autorizar_tarjeta`, `_anular_cobro` |
| 5 | Se emite la nota en PDF y CU-27 resta lo devuelto en las ventas netas y en el efectivo de caja | `nota.py`, CU-27 `devoluciones()` |

## Esquema de la Fase G (migración 0009)

Tablas nuevas: `reportes_generados` (cada reporte generativo: petición, especificación interpretada, resultado y si lo interpretó la IA o las reglas) y `uso_ia` (cada consulta a una
función de IA, que CU-36 muestra como consumo del plan). Los reportes (CU-21, CU-22) no tienen tablas propias: leen pedidos, pagos, devoluciones, reservas e inventario por los `publico.py`.

Planes (RN07): CU-21 y CU-22 exigen `reportes_convencionales`; CU-23, CU-42 y CU-07 exigen `reportes_ia` (plan Profesional). En el seed EMP-A es Básico y EMP-B es Profesional.

| Paso | Qué ocurre | Dónde |
|---|---|---|
| 1 | El Administrador escribe o dicta («ventas del último mes y el producto más vendido») | web `reporte-generativo.page.ts` (Web Speech API del navegador) |
| 2 | La petición se interpreta: con `ANTHROPIC_API_KEY` la IA devuelve la especificación en JSON y se **valida**; sin clave, o si falla o propone algo inválido, se usan las reglas locales | CU-23 `interprete.py` / `core/ia.py` |
| 3 | Con la especificación se consultan los datos con las mismas consultas del CU-21 (ventas netas de devoluciones, ranking, reservas, pagos, inventario) | `ReportesBase`, `ReportesRepository` |
| 4 | Se redacta el reporte, se guarda en `reportes_generados` y se anota el uso de IA | CU-23 `ReporteGenerativoService.generar` |
| 5 | CU-42: KMeans clasifica la rotación de cada producto y una regresión lineal pronostica 4 semanas de demanda; compara con el stock y recomienda reponer o promocionar | CU-42 `AnaliticaMLService` |

## Perfil de gustos del cliente (ajuste de la Fase G, migración 0010)

Tablas: `interacciones_cliente` (búsquedas, prendas vistas y pedidos al asistente; se conservan las últimas 200) y `preferencias_cliente` (si el cliente permite que el sistema aprenda; por defecto, sí).

| Paso | Qué ocurre | Dónde |
|---|---|---|
| 1 | La web avisa lo que el cliente busca en el catálogo y las prendas que mira; el asistente anota lo que le pide. Si apagó la personalización, no se registra nada | `AprendizajeService`, `POST /asistente/interacciones`, `AsistenteService._recordar_pedido` |
| 2 | Se arma el perfil: compras (peso 3), búsquedas y pedidos al asistente (2), prendas vistas (1); lo reciente pesa más (la mitad cada 30 días). Da categorías, colores, tallas y rango de precio | `perfil.py::construir_perfil` |
| 3 | Se puntúan las prendas con stock contra el perfil (categoría, color, talla, precio, oferta, ya la miró) y se descartan las que ya compró | `perfil.py::puntuar`, `Recomendador._puntuadas` |
| 4 | Con IA (si hay clave) la IA elige entre las mejores y explica cada una; el servidor valida que solo elija candidatas reales. Sin IA, el motivo se redacta con reglas | `recomendador.py::elegir_con_ia` |
| 5 | Ofertas: las promociones que encajan con el perfil. Outfits: prendas de otras categorías que combinan en tono con una prenda base | `Recomendador.recomendar` / `outfit` |

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

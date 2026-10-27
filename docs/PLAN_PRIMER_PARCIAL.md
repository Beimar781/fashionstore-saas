# Plan: casos de uso del primer parcial dentro del SaaS

Base: el monorepo `fashionstore-saas` (FastAPI + Angular PWA + Flutter), con aislamiento por `empresa_id`. Ya están hechos CU-02, 13, 14, 33, 34 y 35.
Quedan **36 casos de uso** del documento, repartidos en las fases de abajo.

Fuentes (todo en `D:\proyectos\1er parcial si2\`):
- `1er-parcialSI2\backend-ecommerce-si2`: Django (apps catalog, inventory, orders, payments, pos, promotions, reservations, suppliers, reports, ai, notifications).
- `1er-parcialSI2-Frontend`: Angular (paneles admin, branch, pos, supplier, tienda).
- `1er-parcialSI2-Movil-Flutter`: a pesar del nombre es React Native con Expo; hay que reescribirlo en Flutter.
- `Examen1-Ecommerce-Si2-s2-26.pdf`: el enunciado del primer parcial.

## 1. Quién lo hace

**Claude Code en tu PC**, con este plan y los prompts del punto 7.
- Lee el código viejo directamente del disco; yo tendría que traerlo archivo por archivo.
- Corre Flutter, hace `git push` y ve los errores reales de tu máquina.
- El `CLAUDE.md` del repo ya le da las reglas de arquitectura, y las pruebas le avisan si rompe algo.

Mi parte: revisar cada entrega (clono el repo, corro pruebas y build), ajustar el plan y actualizar el documento y la trazabilidad.

## 2. Qué hay que construir

Origen: **Portar** (existe en el código viejo y se pasa a FastAPI con `empresa_id`), **Ampliar** (existe parcialmente) o **Nuevo** (no existe en ningún código).

| Fase | CU | Qué es | Origen | Referencia vieja |
|---|---|---|---|---|
| A Catálogo | CU-16 | Categorías, tallas y colores | Portar | `catalog/`: Category, SizeGroup, Size, Color, Brand |
| | CU-17 | Temporadas y colecciones | Portar | Season, Collection |
| | CU-18 | Productos con variantes talla×color e imágenes | Portar | Product, ProductVariant, ProductImage |
| | CU-19 | Promociones y descuentos | Portar | `promotions/` |
| | CU-01 | Registrar cuenta de cliente | Portar | `accounts/` (registro) |
| | CU-03, 04, 05 | Consultar catálogo, buscar y filtrar, tallas y colores con disponibilidad por sucursal | Portar | `catalog/views.py` |
| B Proveedores e inventario | CU-15 | Proveedores | Portar | `suppliers/` |
| | CU-31 | Información de productos y abastecimiento (el Proveedor envía productos; el Administrador los revisa; recepción de compra suma stock) | Portar | ProductSubmission, PurchaseReceipt |
| | CU-26 | Disponibilidad e inventario de la sucursal (Encargado) | Ampliar | `inventory/` BranchStock, InventoryMovement |
| | CU-20 | Inventario global: disponibles, reservadas, vendidas, agotadas y próximas a ingresar | Ampliar | `inventory/` (falta "próximas a ingresar") |
| C Reservas | CU-09 | Reservar varias prendas en una sucursal | Portar | `reservations/` |
| | CU-10 | Consultar y cancelar reservas | Ampliar | `reservations/` |
| | CU-24, 25 | Gestionar reservas de la sucursal; confirmar recepción y atención | Portar | `reservations/`, `notifications/` |
| | | Notificar la reserva a la sucursal (RF11) | Ampliar | `notifications/` |
| D Compra digital | CU-08 | Carrito | Portar | `orders/` Cart |
| | CU-11, 12 | Compra digital e historial | Portar | `orders/` Order |
| | CU-32 | Pago electrónico (Stripe en modo prueba) | Portar | `payments/` |
| E Punto de venta | CU-28 | Consultar productos en caja | Portar | `pos/` |
| | CU-29 | Registrar venta presencial | Portar | `pos/` |
| | CU-30 | Pago en caja y comprobante | Portar | `payments/` Receipt |
| | CU-27 | Ventas de la sucursal | Portar | `pos/` daily-summary |
| F Devoluciones | CU-41 | **Devoluciones y cambios de prendas** | **Nuevo** | no existe |
| G Reportes e IA | CU-21 | Ventas y reservas | Portar | `reports/` |
| | CU-22 | Indicadores empresariales (dashboard) | Portar | `reports/`, dashboard admin |
| | CU-23 | **Reportes generativos por prompt y por voz** | Ampliar | `reports/prompt_interpreter.py`; voz solo en el móvil viejo |
| | CU-07 | Asistente y recomendador de prendas | Portar | `ai/` |
| | CU-42 | Dashboard analítico con Machine Learning | **Nuevo** | no existe |
| | CU-36 | Plan, límites y uso de la empresa | **Nuevo** | no existe |
| H Móvil y offline | CU-37 | Descargar catálogo para uso offline | **Nuevo** | no existe |
| | CU-38, 39 | Sincronizar operaciones pendientes; consultar estado local | **Nuevo** | no existe |
| | CU-40 | Gestionar conflictos de sincronización | **Nuevo** | no existe |
| | CU-06 | Vestidor virtual con realidad aumentada | Portar | `infer_service/`, `catalog/` ARAsset, módulo `fitting` del móvil |

## 3. Cómo se organiza el código

Dos zonas, igual que el documento: lo que es del **SaaS multitenant** queda a simple vista, y los casos de uso **conservados del primer parcial** (los del Anexo B: 06, 07, 08, 11, 12, 15 a 19, 24, 25, 27, 28, 30, 31, 32) van en una subcarpeta `primer_parcial` en cada parte. Dentro de ambas zonas se mantiene un paquete por carpeta y un caso de uso por subcarpeta.

| Parte | SaaS (a simple vista) | Primer parcial (en segundo plano) |
|---|---|---|
| Backend | `backend/app/modules/<paquete>/cuNN_<nombre>/` | `backend/app/primer_parcial/<paquete>/cuNN_<nombre>/` |
| Web | `frontend/src/app/features/<paquete>/` | `frontend/src/app/features/primer-parcial/<paquete>/` |
| Móvil | `movil/lib/features/<paquete>/` | `movil/lib/primer_parcial/<paquete>/` |
| Pruebas | `backend/tests/` | `backend/tests/primer_parcial/` |

**SaaS** (CU nuevos o modificados, 2.5.2 del documento):

| Paquete | CU |
|---|---|
| `plataforma` (P1) | 33, 34, 35 (hechos) y **36** |
| `acceso` (P2) | 02, 13 (hechos) y **01** |
| `sucursales` (P3) | 14 (hecho) |
| `catalogo` (P4) | **03, 04** |
| `inventario` (P5) | **05, 20, 26** |
| `reservas` (P6) | **09, 10** |
| `ventas` (P7) | **29, 41** |
| `offline` (P8) | **37, 38, 39, 40** |
| `ia` (P9) | **23, 42** |
| `reportes` (P10) | **21, 22** |

**Primer parcial** (CU conservados; solo se les agrega `empresa_id`):

| Paquete | CU |
|---|---|
| `proveedores` (P3) | 15, 31 |
| `catalogo` (P4) | 16, 17, 18, 19 |
| `reservas` (P6) | 08, 24, 25 |
| `ventas` (P7) | 11, 12, 28, 30, 32 |
| `reportes` (P10) | 27 |
| `ia` (P9) | 06, 07 |

Reglas de dependencia:
- Los paquetes se hablan solo por `publico.py`; nunca tocan las tablas de otro. Por ejemplo, `ventas` pide stock a `inventario` mediante su `publico.py`.
- Las dependencias van en un solo sentido, sin ciclos. Por ejemplo: `primer_parcial/catalogo` ← `modules/inventario` ← `primer_parcial/ventas` ← `modules/ventas`.
- Para el usuario final no hay diferencia: los menús y las pantallas muestran todo junto. La separación es solo de carpetas y de documentación.
- Las migraciones y el `docs/TRAZABILIDAD.md` siguen siendo uno solo; este último tiene dos tablas: «SaaS» y «Primer parcial (Anexo B)».

## 4. Qué pide el enunciado y no estaba en el código del primer parcial

Los puntos 1 a 4 los cubre la tabla de arriba; no hace falta documento nuevo, porque estos CU ya están en el Word.

1. **Devoluciones** (objetivo 11: el inventario se actualiza tras reservas, ventas, **devoluciones** y recepciones). Es CU-41.
2. **Estados de existencias** (enunciado, página 1): disponibles, reservadas, vendidas, agotadas y próximas a ingresar. Va en CU-20 y CU-26.
3. **Reportes generativos por comando de voz** (actor Servicio de IA). CU-23: el prompt ya existe en el backend viejo; la voz va con el micrófono del navegador (web) y de Flutter (móvil).
4. **Notificar la reserva a la sucursal** (RF11) y **cancelar reservas** (actor Cliente).
5. **Registro de clientes** (RF01), **proveedor como actor** (registra productos y su disponibilidad) y **comprobantes** (actor Cajero).
6. **Despliegue en la nube** (no localhost): pendiente aparte, después de las fases.

## 5. Reglas para cada caso de uso (iguales a las del lote 1)

1. Un paquete por carpeta y un caso de uso por subcarpeta, en la zona que le toca según la sección 3 (SaaS o `primer_parcial`): `<zona>/<paquete>/cuNN_<nombre>/{router,service,repository,schemas}.py`. Nada de lógica suelta fuera de un CU.
2. Modelo con `empresa_id` y repositorio que hereda de `TenantRepository`; la empresa sale siempre del token.
3. Únicos por empresa: `slug`, `sku`, `codigo`, `nombre`. Imágenes en una carpeta por empresa. Stock por sucursal de la empresa.
4. Migración Alembic nueva (0003 en adelante); no se edita la 0001 ni la 0002.
5. Textos de error iguales a los de la ficha del CU en el documento (Anexo B para los conservados).
6. Pruebas en `backend/tests/test_cuNN_*.py`, una por paso de la ficha, más una de aislamiento entre empresas.
7. Funciones por plan (IA, reportes) con `exigir_funcionalidad(...)`.
8. Web: rutas lazy por paquete y llamadas HTTP en `core/api/*.api.ts`. Móvil: una carpeta por paquete.
9. Al terminar cada fase: actualizar `docs/TRAZABILIDAD.md`, correr `python -m pytest -q` y `npm run build`, y hacer commit.
10. Cada fase agrega datos de ejemplo al seed para EMP-A y EMP-B.

## 6. Orden recomendado

**Ruta mínima para una demo sólida:** A, B, C, D y E. Muestra las cinco figuras (SuperAdmin, Administrador, Encargado, Cajero, Cliente) con datos reales.
Después, por prioridad de lo que el enunciado exige: F (devoluciones), G (reportes e IA), H (móvil y offline). El vestidor virtual (CU-06) va al final: es lo más riesgoso porque necesita cámara y estimación de pose.

## 7. Prompts para Claude Code

**Cómo usarlos:** Claude Code sigue la «Forma de trabajo» de `CLAUDE.md`: responde en español, corre las pruebas al terminar y, si todo pasa, hace commit y push con tu usuario de git. Una fase por vez, no todas de golpe. Al terminar cada una: revisar, probar a mano, hacer commit y push, y abrir una sesión nueva para la siguiente (así Claude Code no arrastra contexto viejo y los errores no se acumulan). Si algo falla, el commit anterior permite volver atrás.

Antes del primero: abrir la carpeta `fashionstore-saas` en VS Code y dar acceso a las carpetas viejas y al PDF del enunciado.

**Prompt 0 (contexto y estructura, una sola vez)**
```
Lee CLAUDE.md, README.md y docs/TRAZABILIDAD.md de este repo. Luego lee, SIN modificar, el código del primer parcial en
D:\proyectos\1er parcial si2: 1er-parcialSI2\backend-ecommerce-si2 (Django), 1er-parcialSI2-Frontend (Angular) y
1er-parcialSI2-Movil-Flutter (es React Native/Expo; el móvil nuevo es Flutter), el enunciado Examen1-Ecommerce-Si2-s2-26.pdf
y docs/PLAN_PRIMER_PARCIAL.md. Vamos a construir los casos de uso que faltan del SaaS multitenant: unos se portan del código
viejo y otros son nuevos. Respeta la arquitectura de CLAUDE.md y del lote 1 (carpeta por caso de uso, TenantRepository,
contexto_operativo, empresa_id en todo, migraciones Alembic, pruebas por paso).
Estructura obligatoria (sección 3 del plan): el SaaS queda a simple vista en backend/app/modules, frontend features/ y
movil/lib/features; los casos de uso conservados del primer parcial van en subcarpetas separadas: backend/app/primer_parcial,
frontend features/primer-parcial, movil/lib/primer_parcial y backend/tests/primer_parcial. Actualiza CLAUDE.md con esta regla,
crea las carpetas vacías necesarias, registra todo en app/api.py y app/db_models.py y deja docs/TRAZABILIDAD.md con dos
tablas (SaaS y Primer parcial). Verifica que no haya dependencias circulares entre paquetes.
Sigue la sección «Forma de trabajo» de CLAUDE.md: habla siempre en español, corre las pruebas y haz commit y push con mi usuario de git solo si todo pasa.
Resume en 10 líneas cómo vas a hacerlo y espera mi OK.
```

**Prompt A (catálogo)**
```
Implementa la Fase A. En el SaaS (backend/app/modules): CU-03 y CU-04 (consultar catálogo, buscar y filtrar) en catalogo
y CU-01 (registro de cliente) en acceso. Del primer parcial (backend/app/primer_parcial/catalogo): CU-16 (categorías,
grupos de talla, tallas, colores, marcas), CU-17 (temporadas y colecciones), CU-18 (productos con variantes talla×color,
SKU automático, imágenes) y CU-19 (promociones). Porta modelos y reglas de catalog/ y promotions/ del backend viejo.
Únicos por empresa: slug, sku, codigo. Solo el Administrador escribe; los demás roles leen el catálogo activo. Migración 0003.
Pruebas por paso y de aislamiento entre EMP-A y EMP-B. Lee la sección 9 del plan («Tallas, colores y catálogo») y evita esos errores: filtro talla+color sobre la misma variante, SKU corto único por empresa, tallas validadas contra el grupo de la categoría, orden por display_order y endpoint único de opciones color×talla con disponibilidad, con una prueba por cada punto. Web: páginas del Administrador (basadas en features/admin/pages del
Angular viejo, con el estilo del frontend actual) en features/primer-parcial/catalogo y el catálogo público para el Cliente
en features/catalogo. Agrega productos de ejemplo al seed. Al terminar corre pytest y npm run build, actualiza
docs/TRAZABILIDAD.md y haz commit.
```

**Prompt B (proveedores e inventario)**
```
Implementa la Fase B. Del primer parcial: CU-15 (proveedores) y CU-31 (el Proveedor envía productos, el Administrador los
aprueba o rechaza, la recepción de compra suma stock) en backend/app/primer_parcial/proveedores. En el SaaS (modules/inventario):
CU-05 (tallas, colores y disponibilidad por sucursal), CU-26 (el Encargado gestiona disponibilidad e inventario de su
sucursal) y CU-20 (inventario global del Administrador). Basándote en suppliers/ e inventory/ del backend viejo. Estados de
existencias: disponible, reservada, vendida, agotada y próxima a ingresar (esta última sale de recepciones de compra
pendientes). Todo movimiento de inventario se registra con tipo, referencia y usuario. Mismas reglas del plan.
```

**Prompt C (reservas)**
```
Implementa la Fase C. En el SaaS (modules/reservas): CU-09 (reservar varias prendas en una sucursal con horario aproximado)
y CU-10 (consultar y cancelar reservas, el Cliente). Del primer parcial (primer_parcial/reservas): CU-24 y CU-25 (el
Encargado ve las reservas de su sucursal, prepara las prendas y confirma la recepción del cliente). La reserva pasa stock de
disponible a reservado; cancelar o expirar lo devuelve. Notifica la reserva a la sucursal (RF11). Basándote en reservations/
y notifications/ del backend viejo. Mismas reglas.
```

**Prompt D (compra digital)**
```
Implementa la Fase D, todo del primer parcial: CU-08 (carrito, en primer_parcial/reservas) y CU-11 (compra digital), CU-12
(historial de compras) y CU-32 (pago electrónico con Stripe en modo prueba; si no hay clave configurada, pago de simulación),
en primer_parcial/ventas. Basándote en orders/ y payments/ del backend viejo. Al confirmar el pago se descuenta el stock
de la sucursal elegida. Mismas reglas.
```

**Prompt E (punto de venta)**
```
Implementa la Fase E. Del primer parcial: CU-28 (consultar productos en caja) y CU-30 (cobro en efectivo o tarjeta y comprobante
con número por sucursal) en primer_parcial/ventas, y CU-27 (ventas de la sucursal) en primer_parcial/reportes. En el SaaS
(modules/ventas): CU-29 (registrar venta presencial, también desde una reserva). Basándote en pos/ y payments/ del backend viejo.
Cada venta descuenta el stock de la sucursal del Cajero. Mismas reglas.
```

**Prompt F (devoluciones, nuevo)**
```
Implementa la Fase F: CU-41 (devoluciones y cambios de prendas), en modules/ventas (cu41_devoluciones). Es un caso de uso
NUEVO, no existe en el código viejo. Lee su ficha en el documento y el objetivo 11 del enunciado. El Cajero o Encargado
registra la devolución de una venta o pedido existente (parcial o total), con motivo; la prenda vuelve al stock de la sucursal
y se registra el movimiento de inventario; si es un cambio, se descuenta la prenda nueva. No se puede devolver más de lo
vendido ni una venta de otra empresa. Mismas reglas del plan.
```

**Prompt G (reportes e IA)**
```
Implementa la Fase G. En el SaaS: CU-21 (ventas y reservas) y CU-22 (indicadores empresariales) en modules/reportes; CU-23
(reportes generativos: el Administrador escribe o dicta por voz una petición y el sistema interpreta y genera el reporte,
basándote en reports/prompt_interpreter.py del backend viejo; la voz usa la Web Speech API del navegador) y CU-42 (dashboard
analítico con Machine Learning, por ejemplo pronóstico de demanda o clasificación de rotación con scikit-learn) en modules/ia;
CU-36 (plan, límites y uso de la empresa) en plataforma. Del primer parcial: CU-07 (asistente y recomendador, basándote en ai/)
en primer_parcial/ia. Las funciones de IA y reportes se protegen con exigir_funcionalidad según el plan. La IA externa se
consume por API con clave en .env; sin clave, responde con un modo de respaldo. Mismas reglas.
```

**Prompt H (móvil y offline)**
```
Implementa la Fase H en el paquete offline del SaaS (backend: endpoint de sincronización por lotes; web y móvil: features/offline):
CU-37 (descargar catálogo para uso offline), CU-38 (sincronizar operaciones pendientes), CU-39 (consultar operaciones locales y su
estado) y CU-40 (conflictos de sincronización, en web). Móvil en Flutter + SQLite, con UUID generado en el cliente y los estados
REGISTRADA_LOCAL, ENVIADA, CONFIRMADA, RECHAZADA y EN_CONFLICTO (RN11/RN12); el reenvío debe ser idempotente. Después reescribe en
Flutter, dentro de movil/lib/primer_parcial, las pantallas del cliente del móvil viejo (catálogo, reserva, carrito, pedidos).
Compila con flutter analyze y flutter test.
```

**Prompt I (vestidor virtual, al final)**
```
Implementa CU-06 (vestidor virtual con realidad aumentada) en Flutter, dentro de movil/lib/primer_parcial/ia y backend
primer_parcial/ia, portando la idea del módulo features/fitting del móvil viejo y los ARAsset de catalog/ e infer_service/ del
backend. Lee la sección 9 del plan («Vestidor virtual») y aplica sus mejoras de rendimiento (meta: prenda visible en menos de 1 segundo y 15 FPS o más). Primero dime qué librerías de cámara y detección de pose usarías en Flutter (plan A y plan B) y qué riesgos ves; espera mi OK antes de programar.
```

## 8. Cómo probar el móvil

- **Emulador de Android Studio:** sirve para pantallas, login, catálogo, carrito, reservas y modo sin conexión. Para la cámara se puede usar la webcam de la PC (en el AVD, *Camera → Back → Webcam*), pero no sirve para validar el vestidor virtual.
- **Teléfono Android real por USB (recomendado para el vestidor virtual):** activar *Depuración USB* y correr `flutter run`. Cámara, rendimiento y detección de pose se prueban con el hardware real. El teléfono y la PC deben estar en la misma red Wi‑Fi: `flutter run --dart-define=API_URL=http://IP_DE_LA_PC:8000/api`.
- **App descargable:** no se crea otra aplicación; es el mismo proyecto `movil/`. `flutter build apk --release` genera un `.apk` que se instala en cualquier Android (pasándolo por Drive o GitHub Releases). Cuando el backend esté desplegado, solo se cambia `API_URL`.

**Vestidor virtual (CU-06).** El móvil viejo ya hace la detección de pose en el propio teléfono con **MoveNet Thunder** (modelo `movenet_thunder_int8.tflite`), suaviza los puntos con un filtro One Euro y ancla la prenda con el `anchor_config` de cada `ARAsset`. En Flutter se puede **reutilizar el mismo modelo `.tflite`** con `camera` + `tflite_flutter`, y portar el filtro y el cálculo de anclaje, que son matemática pura. La alternativa más rápida es `google_mlkit_pose_detection`. Es la parte más riesgosa del plan: por eso va al final y con aprobación previa.

## 9. Lecciones del primer parcial (errores a no repetir)

Salen de revisar el código viejo. Claude Code debe leer esta sección antes de las Fases A y I.

### Tallas, colores y catálogo

1. **Filtro talla + color sobre la misma variante.** Hoy `size` y `color` se filtran con dos `filter()` encadenados sobre `variants`, y Django los une por separado: un producto con una variante talla M y otra en rojo aparece como "M y rojo" aunque no exista la combinación. Debe ser una sola condición sobre la variante activa (y con stock, si se filtra por sucursal).
2. **Disponibilidad por sucursal.** El filtro de sucursal no exige que la variante esté activa ni que coincida con la talla o el color filtrados. Además, el endpoint de disponibilidad hace una consulta por variante. Debe calcularse en una sola consulta agrupada, solo con variantes activas.
3. **SKU frágil.** Se arma con el slug del color, que se puede editar, y el campo admite solo 32 caracteres: colores o tallas largos rompen con error 500. Debe usar un código corto, único **por empresa**, y tener una prueba de longitud máxima.
4. **Tallas que no corresponden.** Al generar variantes no se valida que la talla pertenezca al grupo de tallas de la categoría del producto, y se pueden mezclar S/M con 28/30. Hay que validarlo.
5. **Orden de tallas.** Las tallas se mostraban en el orden en que se crearon las variantes, no por `display_order` (salía L, M, S, XL). Debe ordenar siempre por `display_order`.
6. **Dos lógicas distintas.** La web deshabilita colores y tallas agotados y el móvil no. Solución: un único endpoint `GET /api/catalogo/productos/{id}/opciones?sucursal=` que devuelve la matriz color × talla con `disponible`, `cantidad` y `orden`. Web y móvil solo dibujan, no recalculan.
7. **Selección en pantalla.**
   - Al cambiar de color se perdía la talla elegida. Debe conservarse si existe y tiene stock; si no, pasar a la primera con stock.
   - Se podía elegir un color agotado y agregar al carrito una variante sin stock.
   - La talla preferida se guardaba por id; debe guardarse por código, porque cambia entre grupos de tallas.
   - La selección se reinicia en cada actualización de datos; debe reiniciarse solo al cambiar de producto.
8. **Pruebas obligatorias** para cada punto anterior (filtro combinado, SKU largo, talla de otro grupo, orden, variante agotada).

### Vestidor virtual (CU-06)

El móvil viejo tardaba en detectar hombros y torso por estas causas, todas en `useBodyTracking.ts`:

1. **Modelo pesado y sin aceleración.** Usa MoveNet **Thunder** (256×256) y lo carga sin delegado (`loadTensorflowModel(url, [])`), es decir, en CPU. Para ubicar solo hombros y caderas alcanza **Lightning** (192×192), unas 2 o 3 veces más rápido, o ML Kit.
2. **Recorte central.** Recorta el cuadro de la cámara a un cuadrado central. En un cuadro vertical se pierde cerca de la mitad de la altura, y si los hombros quedan arriba o la persona está cerca, el modelo no los ve. Debe usar encuadre completo con relleno o recortar alrededor de la persona detectada en el cuadro anterior.
3. **Umbrales estrictos.** Pide puntaje ≥ 0.42 en ambos hombros, torso casi de frente (inclinación ≤ 0.22), ancho entre 14 % y 82 % de la pantalla y 3 cuadros seguidos buenos antes de mostrar la prenda. Una pose algo girada o más lejos nunca "engancha".
4. **Doble suavizado.** Filtro One Euro con corte 1.35 más una segunda mezcla de 0.5 a 0.62 por cuadro. Con un modelo rápido se puede quitar la segunda mezcla.
5. **Conversión de imagen en CPU** de YUV a RGB en cada cuadro.

Mejoras para la versión en Flutter:
- Plan A: `camera` + `google_mlkit_pose_detection` (modo *stream*), que maneja YUV, rotación y modelo optimizado. Plan B: `tflite_flutter` con MoveNet Lightning y delegado GPU/NNAPI, en un `Isolate`.
- Resolución de cámara media (por ejemplo 640×480) y pose detectada solo en hombros y caderas.
- Bloqueo con 1 o 2 cuadros buenos, umbral cerca de 0.30, y refinamiento después.
- Guía en pantalla con mensajes ("acércate", "ponte de frente", "sube la cámara").
- Reutilizar sin cambios: el filtro One Euro, el cálculo de anclaje (`anchor_config`) y el cache del PNG de la prenda, que son lógica pura.
- Overlay precargado al abrir la ficha del producto y PNG de máximo 800 px de ancho.
- Tallas numéricas: `size_scale` por código con valor por defecto, no solo S, M, L.
- Meta: la prenda aparece en menos de 1 segundo y se mantiene a 15 FPS o más en un teléfono de gama media. Una vista de depuración muestra FPS y latencia.

## 10. Pendientes que necesito de ti

- Claves de prueba de Stripe, solo si quieres CU-32 con tarjeta real (si no, queda en simulación).
- Cuenta de Brevo para el correo de restablecer contraseña, cuando se despliegue.
- Decidir dónde desplegar (Render, Railway, un VPS) cuando terminen las fases.

## 11. Correcciones que le tocan al repo antes de seguir

- Quitar `package-lock.json` suelto de la raíz.
- `docs/TRAZABILIDAD.md` aún cita la tabla 4.4.3 del documento (ya no existe): quitar esa frase.

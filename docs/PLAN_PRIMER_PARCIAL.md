# Plan: casos de uso del primer parcial dentro del SaaS

Base: el monorepo `fashionstore-saas` (FastAPI + Angular PWA + Flutter), con aislamiento por `empresa_id`. Ya están hechos CU-02, 13, 14, 33, 34 y 35.
Todos los casos de uso del plan están hechos. La clase del 29/10 agregó las fases **J** (bitácora) y **K** (tres ajustes de la ingeniera). Lo que sigue es la **Fase L (preparar el despliegue)**, el despliegue en la nube, la prueba conjunta web y móvil y el documento.

| Fase | Estado | Commit | CU |
|---|---|---|---|
| A Catálogo | Hecha | `0f151cd` | 01, 03, 04, 16, 17, 18, 19 |
| B Proveedores e inventario | Hecha | `e474c8f` | 05, 15, 20, 26, 31 |
| C Reservas | Hecha | `6b64a86` | 09, 10, 24, 25 y RF11 |
| D Compra digital | Hecha | `60831af` | 08, 11, 12, 32 |
| E Punto de venta | Hecha | `039cc45` | 27, 28, 29, 30 |
| F Devoluciones | Hecha | `b1bc631` | 41 |
| G Reportes e IA | Hecha | `192228b`, `5a27222` | 07, 21, 22, 23, 36, 42 |
| H Offline | Hecha | `062d933` | 37, 38, 39, 40 |
| J Bitácora | Hecha | `8589413` | transversal, sin CU |
| K Ajustes de la clase | Hecha | `8e286b5` | 3 planes (prueba gratuita) · push de devoluciones · compra offline en conflicto |
| Android y APK | Hecho | `94d33f2` | carpeta `movil/android/` y flujo `.github/workflows/apk.yml` |
| I Vestidor virtual | Hecha (falta medir FPS en un celular) | `d7bb3f7` | 06 |
| **L Preparar el despliegue** | **Siguiente** | | Railway, claves reales, push móvil con Firebase, prendas de demostración, guía paso a paso |

Hasta la Fase I: 544 pruebas del backend y 47 de Flutter pasando, la web compila y la última migración es la 0015.

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

Mi parte: revisar cada entrega (clono el repo, corro pruebas y build en una copia limpia), ajustar el plan y actualizar el documento y la trazabilidad. Después de cada fase me pasas el resumen que te da Claude Code.

## 2. Qué hay que construir

Origen: **Portar** (existe en el código viejo y se pasa a FastAPI con `empresa_id`), **Ampliar** (existe parcialmente) o **Nuevo** (no existe en ningún código).

| Fase | CU | Qué es | Origen | Referencia vieja |
|---|---|---|---|---|
| A Catálogo | CU-16 | Categorías, tallas y colores | Portar | `catalog/`: Category, SizeGroup, Size, Color, Brand |
| | CU-17 | Temporadas y colecciones | Portar | Season, Collection |
| | CU-18 | Productos con variantes talla×color e imágenes | Portar | Product, ProductVariant, ProductImage |
| | CU-19 | Promociones y descuentos | Portar | `promotions/` |
| | CU-01 | Registrar cuenta de cliente | Portar | `accounts/` (registro) |
| | CU-03, 04 | Consultar catálogo, buscar y filtrar | Portar | `catalog/views.py` |
| B Proveedores e inventario | CU-15 | Proveedores | Portar | `suppliers/` |
| | CU-31 | Información de productos y abastecimiento (el Proveedor envía productos; el Administrador los revisa; recepción de compra suma stock) | Portar | ProductSubmission, PurchaseReceipt |
| | CU-05 | Tallas y colores con disponibilidad por sucursal | Portar | `catalog/views.py` |
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
| J Bitácora | Transversal | Bitácora de operaciones por empresa (Administrador) y general (SuperAdministrador) | **Nuevo** | proyecto de la clínica (referencia de diseño) |
| K Ajustes de la clase | CU-34, 35, 36 | Tercer plan: prueba gratuita de un mes | Ampliar | seed y planes |
| | CU-41, RF11 | Notificación push al devolver prendas | Ampliar | `rf11_notificaciones` |
| | CU-38, 40 | Compra sin conexión que ya no se puede cumplir: aviso push y devolución del dinero | Ampliar | `offline` |
| I Vestidor virtual | CU-06 | Vestidor virtual con realidad aumentada | Portar | `infer_service/`, `catalog/` ARAsset, módulo `fitting` del móvil |

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
| `plataforma` (P1) | 33, 34, 35, 36 (hechos) y la **bitácora** (transversal, no es un CU) |
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
- Las dependencias van en un solo sentido, sin ciclos. Cadena real hasta la Fase D: `primer_parcial/catalogo` ← `modules/inventario` ← `modules/reservas` ← `primer_parcial/reservas` (carrito) ← `primer_parcial/ventas`. Lo que sigue se apoya en esa cadena: `modules/ventas` (CU-29, CU-41) usará `primer_parcial/ventas`, y los reportes leerán de ventas y reservas, nunca al revés.
- Un paquete SaaS puede depender de uno del primer parcial (por ejemplo, el catálogo del SaaS usa los modelos de `primer_parcial/catalogo`); lo que no puede haber son ciclos.
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
4. Una migración Alembic nueva por fase (0003 fue la A; la última subida es la 0015; la siguiente es la 0016). **Nunca se edita una migración ya subida**: si hay que corregir una restricción, va en la nueva (como hizo la 0006 con las referencias de inventario).
5. Textos de error iguales a los de la ficha del CU en el documento (Anexo B para los conservados).
6. Pruebas en `backend/tests/test_cuNN_*.py`, una por paso de la ficha, más una de aislamiento entre empresas.
7. Funciones por plan (IA, reportes) con `exigir_funcionalidad(...)`.
8. Web: rutas lazy por paquete y llamadas HTTP en `core/api/*.api.ts`. Móvil: una carpeta por paquete.
9. Al terminar cada fase: actualizar `docs/TRAZABILIDAD.md`, correr `python -m pytest -q` y `npm run build`, y hacer commit.
10. Cada fase agrega datos de ejemplo al seed para EMP-A y EMP-B.
11. Al terminar cada fase, agregar a `docs/MENSAJES_PENDIENTES_WORD.md` los mensajes nuevos (con su código HTTP), las reglas de negocio y las decisiones que no están en las fichas del Word. De ahí sale la actualización del documento de la presentación 2.
12. Servicios externos (Stripe, correo, IA): un adaptador con modo simulado cuando no hay claves, probado con un doble en memoria, y las claves solo en `backend/.env`. Nunca claves en el código ni en el chat.
13. Librerías nuevas: se agregan a `requirements.txt` o `package.json` y se comprueba con una instalación limpia (`pip install -r requirements.txt`, `npm install`).
14. Antes de usar un valor nuevo en una columna con `CHECK` (tipos y referencias de inventario, estados), revisar la restricción existente y ampliarla en la migración nueva.
15. Reutilizar lo ya construido en vez de duplicarlo: pedidos (ya tienen `canal` DIGITAL o PRESENCIAL y entrega EN_TIENDA), numeración de comprobantes `CMP-<sucursal>-<número>`, generador de PDF del comprobante (`cu12_historial_compras/comprobante.py`), pasarela del CU-32 y bitácora de inventario (referencias `VENTA`, `PEDIDO` y `DEVOLUCION` ya permitidas).
16. **Bitácora** (desde la Fase J): toda operación de escritura nueva queda registrada; al crear un endpoint, se agrega su ruta a la tabla de etiquetas de `plataforma/bitacora`. Nunca se guardan contraseñas, tokens ni datos de tarjeta, y la bitácora no se edita ni se borra. La bitácora de inventario (`movimientos_inventario`) es otra cosa y no se toca.
17. **Push** (desde la Fase K): los avisos importantes al cliente usan el servicio de push de `rf11_notificaciones`; un fallo del push nunca deshace la operación que lo originó.

## 6. Orden recomendado

Las fases A a K e I están hechas. Sigue **L** (preparar el despliegue); después se despliega y se prueba todo junto (web y móvil).

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

**Prompt A (catálogo)** — *hecho*
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

**Prompt B (proveedores e inventario)** — *hecho*
```
Implementa la Fase B. Del primer parcial: CU-15 (proveedores) y CU-31 (el Proveedor envía productos, el Administrador los
aprueba o rechaza, la recepción de compra suma stock) en backend/app/primer_parcial/proveedores. En el SaaS (modules/inventario):
CU-05 (tallas, colores y disponibilidad por sucursal), CU-26 (el Encargado gestiona disponibilidad e inventario de su
sucursal) y CU-20 (inventario global del Administrador). Basándote en suppliers/ e inventory/ del backend viejo. Estados de
existencias: disponible, reservada, vendida, agotada y próxima a ingresar (esta última sale de recepciones de compra
pendientes). Todo movimiento de inventario se registra con tipo, referencia y usuario. Mismas reglas del plan.
```

**Prompt C (reservas)** — *hecho*
```
Implementa la Fase C. En el SaaS (modules/reservas): CU-09 (reservar varias prendas en una sucursal con horario aproximado)
y CU-10 (consultar y cancelar reservas, el Cliente). Del primer parcial (primer_parcial/reservas): CU-24 y CU-25 (el
Encargado ve las reservas de su sucursal, prepara las prendas y confirma la recepción del cliente). La reserva pasa stock de
disponible a reservado; cancelar o expirar lo devuelve. Notifica la reserva a la sucursal (RF11). Basándote en reservations/
y notifications/ del backend viejo. Mismas reglas.
```

**Prompt D (compra digital)** — *hecho*
```
Implementa la Fase D, todo del primer parcial: CU-08 (carrito, en primer_parcial/reservas) y CU-11 (compra digital), CU-12
(historial de compras) y CU-32 (pago electrónico con Stripe en modo prueba; si no hay clave configurada, pago de simulación),
en primer_parcial/ventas. Basándote en orders/ y payments/ del backend viejo. Al confirmar el pago se descuenta el stock
de la sucursal elegida. Mismas reglas.
```

**Prompt E (punto de venta)** — *hecho*
```
Antes de empezar, agrega a CLAUDE.md las reglas 11 a 15 de la sección 5 de docs/PLAN_PRIMER_PARCIAL.md (mensajes pendientes para el
Word, servicios externos con modo simulado, librerías nuevas, restricciones CHECK y reutilizar lo construido).
El archivo docs/PLAN_PRIMER_PARCIAL.md ya está actualizado en mi carpeta pero todavía no se subió: inclúyelo en el commit de esta fase
(no lo modifiques; solo agrégalo con git add).
Implementa la Fase E. Del primer parcial: CU-28 (consultar productos en caja: el Cajero busca prendas y ve talla, color y
stock de SU sucursal) y CU-30 (cobro en efectivo o con tarjeta y comprobante) en primer_parcial/ventas, y CU-27 (ventas de la
sucursal: resumen diario y listado) en primer_parcial/reportes. En el SaaS (modules/ventas): CU-29 (registrar venta presencial,
también desde una reserva ya preparada). Basándote en pos/ y payments/ del backend viejo.
Reutiliza lo de la Fase D (regla 15): la tabla de pedidos con canal PRESENCIAL y entrega EN_TIENDA, la numeración
CMP-<sucursal>-<número>, el PDF de comprobante, la pasarela del CU-32 para el cobro con tarjeta y la bitácora de inventario
con referencia VENTA. Cada venta descuenta el stock de la sucursal del Cajero; si viene de una reserva, pasa de reservado a
vendido. Si el cliente está registrado, la venta aparece en su historial (CU-12). Un Cajero solo vende en su sucursal.
Pruebas por paso y de aislamiento entre EMP-A y EMP-B; incluye una prueba de venta que se queda sin stock a mitad del cobro.
Web: pantalla de caja en features/primer-parcial/ventas. Seed: ventas presenciales de ejemplo. Termina con la sección de la
fase en docs/MENSAJES_PENDIENTES_WORD.md. Mismas reglas.
```

**Prompt F (devoluciones, nuevo)** — *hecho*
```
Implementa la Fase F: CU-41 (devoluciones y cambios de prendas), en modules/ventas (cu41_devoluciones). Es un caso de uso
NUEVO, no existe en el código viejo. Lee su ficha en el documento y el objetivo 11 del enunciado. El Cajero o Encargado
registra la devolución de una venta presencial o de una compra digital (parcial o total), con motivo; la prenda vuelve al
stock de la sucursal con referencia DEVOLUCION en la bitácora de inventario; si es un cambio, se descuenta la prenda nueva.
Si la compra se pagó con tarjeta, el reembolso pasa por la misma pasarela del CU-32 (en simulado se marca como reembolsado;
con Stripe, reembolso de prueba); si fue en efectivo, queda registrada la devolución del dinero. No se puede devolver más
de lo vendido, ni dos veces la misma prenda, ni una venta de otra empresa. Las devoluciones restan en las ventas netas de
los reportes. Pruebas por paso, de aislamiento y de devolución repetida. Termina con la sección de la fase en
docs/MENSAJES_PENDIENTES_WORD.md. Mismas reglas del plan.
```

**Prompt G (reportes e IA)** — *hecho*
```
Implementa la Fase G. En el SaaS: CU-21 (ventas y reservas) y CU-22 (indicadores empresariales) en modules/reportes; CU-23
(reportes generativos: el Administrador escribe o dicta por voz una petición y el sistema interpreta y genera el reporte,
basándote en reports/prompt_interpreter.py del backend viejo; la voz usa la Web Speech API del navegador) y CU-42 (dashboard
analítico con Machine Learning, por ejemplo pronóstico de demanda o clasificación de rotación con scikit-learn) en modules/ia;
CU-36 (plan, límites y uso de la empresa) en plataforma. CU-21 incluye ventas digitales y presenciales netas de devoluciones y una vista de pagos (aprobados, rechazados y pendientes de confirmación, desde la tabla pagos). Del primer parcial: CU-07 (asistente y recomendador, basándote en ai/)
en primer_parcial/ia. Las funciones de IA y reportes se protegen con exigir_funcionalidad según el plan. La IA externa se
consume por API con clave en .env; sin clave, responde con un modo de respaldo (regla 12). Termina con la sección de la fase en
docs/MENSAJES_PENDIENTES_WORD.md. Mismas reglas.
```

**Prompt H (móvil y offline)** — *hecho*
```
Implementa la Fase H en el paquete offline del SaaS (backend: endpoint de sincronización por lotes; web y móvil: features/offline):
CU-37 (descargar catálogo para uso offline), CU-38 (sincronizar operaciones pendientes), CU-39 (consultar operaciones locales y su
estado) y CU-40 (conflictos de sincronización, en web). Móvil en Flutter + SQLite, con UUID generado en el cliente y los estados
REGISTRADA_LOCAL, ENVIADA, CONFIRMADA, RECHAZADA y EN_CONFLICTO (RN11/RN12); el reenvío debe ser idempotente. Después reescribe en
Flutter, dentro de movil/lib/primer_parcial, las pantallas del cliente del móvil viejo (catálogo, reserva, carrito, pedidos).
Compila con flutter analyze y flutter test.
```

**Prompt J (bitácora)**
```
El archivo docs/PLAN_PRIMER_PARCIAL.md está actualizado en mi carpeta y todavía no se subió: inclúyelo en el commit de esta fase (solo git add, no lo modifiques).
Implementa la bitácora del sistema. No es un caso de uso: es una función transversal, como el aislamiento por empresa; la ingeniera
la da por sobreentendida en todos los proyectos. Va en backend/app/modules/plataforma/bitacora/ (modelo, repositorio, servicio, router
y middleware) y se expone a los demás paquetes solo por plataforma/publico.py.
Qué registra: cada inicio y cierre de sesión (y los intentos fallidos, sin guardar la contraseña) y cada operación de escritura
(POST, PUT, PATCH, DELETE) terminada con éxito por un usuario con sesión. Por cada una guarda quién (usuario, rol y empresa), la acción
(inicio de sesión, cierre de sesión, crear, modificar, eliminar, aprobar, cancelar, pagar, devolver, sincronizar...), la entidad
(usuario, sucursal, producto, reserva, pedido, devolución, plan, suscripción, empresa...), un detalle en español legible («Registró la
sucursal Centro», no «POST /sucursales») y la IP (usa X-Forwarded-For cuando haya proxy). Sin tocar cada caso de uso: un middleware o
una dependencia lee la sesión y una tabla de etiquetas (ruta → entidad y acción) arma el detalle; una ruta sin etiqueta se registra con
un texto genérico. Las consultas (GET) no se registran. Nunca se guardan contraseñas, tokens ni datos de tarjeta. La bitácora solo se
agrega: no existe ningún endpoint para editarla o borrarla. NO toques movimientos_inventario: es otra cosa y está bien.
Tabla `bitacora` (migración nueva): id, empresa_id (vacío en operaciones de plataforma), usuario_id, usuario (nombre guardado en ese
momento), rol, accion, entidad, entidad_id, detalle, ip, creado_en; índice por (empresa_id, creado_en). Las operaciones del SuperAdmin
sobre una empresa (suspender, asignar plan) se guardan con el empresa_id de esa empresa.
Quién la ve: el Administrador ve SOLO la bitácora de su empresa (el empresa_id sale del token); el SuperAdministrador ve la de TODAS las
empresas juntas, con filtro por empresa y una columna Empresa, más sus operaciones de plataforma. Encargado, Cajero y Cliente no tienen
acceso (403).
Pantalla web, con este diseño (el de la bitácora del proyecto de la clínica): título «Bitácora» con una etiqueta con el total de
registros; un panel «Operaciones registradas en el sistema» con los filtros Usuario, Entidad, Acción, Desde, Hasta y «Buscar en el
detalle o la IP», botones Filtrar y Limpiar; y una tabla paginada, de la más reciente a la más antigua, con Fecha y hora, Usuario,
Acción (etiqueta de color: verde para inicio de sesión, gris para cierre, y otros colores para crear, modificar y eliminar), Entidad,
Detalle e IP. Una pantalla para el Administrador (features/plataforma, opción «Bitácora» del menú) y otra para el SuperAdmin con el filtro
y la columna Empresa.
Pruebas: inicio y cierre de sesión quedan registrados; un alta cualquiera deja su fila con el detalle; un intento fallido se registra sin
la contraseña; el Administrador de EMP-A no ve nada de EMP-B; el SuperAdmin ve las dos; Encargado y Cajero reciben 403; no hay forma de
editar ni borrar; un GET no se registra. Seed: unas 40 filas de ejemplo repartidas entre EMP-A y EMP-B. Agrega la regla 16 del plan a
CLAUDE.md. Al final, la sección de la fase en docs/MENSAJES_PENDIENTES_WORD.md, con lo que hay que agregar al Word. Mismas reglas.
```

**Prompt K (ajustes de la clase del 29/10)**
```
Implementa tres ajustes que pidió la ingeniera. Una prueba por punto y un solo commit.
1. Tres planes de suscripción. Hoy solo hay Básico (2 sucursales, sin IA) y Profesional (10, con IA). Agrega el tercero: «Prueba
   gratuita» (0 Bs, un mes, 1 sucursal, reportes convencionales y offline, sin IA), en el seed. Reglas: al asignarla, la vigencia es de
   1 mes sin que el SuperAdmin tenga que indicarla; cada empresa puede usarla una sola vez («La empresa ya usó su mes de prueba.»); al
   vencer, la empresa pasa al modo restringido de RN05 y puede contratar Básico o Profesional con CU-35; el SuperAdmin puede asignarla al
   crear la empresa (CU-33). Si necesitas un campo nuevo en el plan (por ejemplo es_prueba), va en una migración nueva. Comprueba que
   CU-34 (planes), CU-35 (asignar suscripción y rechazar el cambio a un plan con límite inferior a las sucursales activas), CU-36 (plan y
   uso) y exigir_funcionalidad funcionan con los tres. Pruebas: listado con tres planes, prueba asignada con vigencia de 1 mes, segunda
   prueba rechazada, empresa con prueba vencida en modo restringido, paso de la prueba a Básico y a Profesional, y que la prueba siga
   bloqueando CU-23 (IA).
2. Notificación push al devolver prendas (CU-41). Al registrar una devolución o un cambio, el Cliente de esa compra (si tiene cliente)
   recibe un push: «Su devolución {número} fue registrada. Reembolso: Bs {monto} por {medio}.» (o «Su cambio {número} fue registrado.»
   si no hay reembolso). El aviso también queda en su campana (RF11) y en la bitácora. Construye un servicio de push reutilizable en
   modules/reservas/rf11_notificaciones, con adaptadores y modo simulado cuando no hay claves (regla 12):
   - Web (PWA): Web Push con VAPID (librería pywebpush). Las claves se generan con scripts/generar_vapid.py y van al .env; no hace falta
     ninguna cuenta. El service worker recibe el push y lo muestra; el permiso se pide al iniciar sesión el Cliente.
   - Móvil: Firebase Cloud Messaging si hay credenciales en el .env y google-services.json en el proyecto Flutter; si no, modo
     simulado: el backend deja el aviso pendiente y la app lo muestra como notificación local (flutter_local_notifications) al abrirse
     o al sincronizar.
   - Tabla nueva de dispositivos (usuario, canal WEB o MOVIL, token o suscripción), con endpoints para registrar el dispositivo al iniciar
     sesión y quitarlo al cerrarla.
   - Si el push falla, la devolución sigue (regla 17): se registra el error y nada más.
3. Compra sin conexión que ya no se puede cumplir. Escenario de la ingeniera: dos clientes quieren la última unidad de una prenda; uno
   compra con conexión y el otro sin conexión. El sistema deja al cliente sin conexión hacer la compra en su dispositivo (queda
   REGISTRADA_LOCAL); la compra real es la del cliente con conexión. Cuando el primero recupera internet y sincroniza, su operación queda
   EN_CONFLICTO o RECHAZADA sin descontar nada y le llega un push: «Su compra {referencia} no se pudo realizar porque la prenda se agotó.»
   Si ya se le había cobrado (venta de contado en caja con ese cliente identificado, o un pago aprobado), se registra la devolución del
   dinero (por la pasarela o en efectivo, reutilizando CU-41) y el aviso lo dice. Hoy el sistema solo avisa al personal de la sucursal
   (CONFLICTO_SYNC): conserva ese aviso y agrega el del cliente. Agrega la operación COMPRA del Cliente (hoy solo existen VENTA_CONTADO del
   personal y RESERVA del cliente) en backend, web y móvil. En «Conflictos de sincronización» (CU-40), el Encargado debe poder descartar
   una venta ya cobrada devolviendo el dinero. Prueba el escenario completo con dos clientes de EMP-A y una sola unidad, y una de
   aislamiento con EMP-B.
   ANTES de programar este punto 3, explícame en español cómo vas a resolver «compra del cliente sin conexión» y el cobro (la tarjeta no
   se puede cobrar sin internet) y espera mi OK.
Al final: secciones nuevas en docs/MENSAJES_PENDIENTES_WORD.md (RN06 pasa a tres planes; push; compra offline en conflicto) y el resumen
en español. Mismas reglas.
```

**Prompt I (vestidor virtual, al final)** — agrega también sus rutas a la bitácora (regla 16)
```
Implementa CU-06 (vestidor virtual con realidad aumentada) en Flutter, dentro de movil/lib/primer_parcial/ia y backend
primer_parcial/ia, portando la idea del módulo features/fitting del móvil viejo y los ARAsset de catalog/ e infer_service/ del
backend. Lee la sección 9 del plan («Vestidor virtual») y aplica sus mejoras de rendimiento (meta: prenda visible en menos de 1 segundo y 15 FPS o más). Primero dime qué librerías de cámara y detección de pose usarías en Flutter (plan A y plan B) y qué riesgos ves; espera mi OK antes de programar.
```

**Prompt L (preparar el despliegue en Railway, con todo funcional)**
```
Prepara el proyecto para desplegarlo TODO en Railway (el enunciado exige la nube) y que cada función quede real: correo con Brevo, pago
con Stripe de prueba, IA con la API GRATUITA de Google Gemini, push web y push móvil con Firebase. No agregues casos de uso nuevos. Arquitectura:
un proyecto de Railway con tres servicios: Postgres (plugin de Railway), backend (carpeta backend, Dockerfile) y frontend (carpeta
frontend, Dockerfile con nginx). Las cuentas y las claves las crea el usuario; tú nunca las pides en el chat ni las escribes en el
código: solo en variables de entorno (regla 12). Haz esto:
1. Backend en Railway:
   - El Dockerfile debe escuchar en el puerto de la variable PORT y arrancar con --proxy-headers para que la IP de la bitácora sea la real.
   - DATABASE_URL llega de Railway como postgresql://...: conviértela a postgresql+psycopg:// (app y alembic).
   - Las imágenes (productos y PNG del vestidor) siguen en disco, en MEDIA_DIR=/app/media, que en Railway será un Volume montado en esa
     ruta; el seed vuelve a crear las del demo si el volumen está vacío.
   - Un endpoint /salud (health check). El backend se niega a arrancar en producción con la SECRET_KEY por defecto.
   - CARGAR_DATOS_DEMO=true: al arrancar, después de las migraciones, carga el seed solo si la base está vacía (sin duplicar nunca).
   - Un script scripts/probar_correo.py que envía un correo de prueba por Brevo e imprime el error legible si el remitente no está
     verificado. Si Brevo rechaza un envío en producción, la API devuelve un error claro y lo registra.
   - IA gratuita (sin tarjeta): hoy core/ia.py solo habla con Anthropic, que es de pago. Agrega el proveedor Google Gemini y hazlo el
     predeterminado (IA_PROVEEDOR=gemini|anthropic; GEMINI_API_KEY; IA_MODELO con valor por defecto gemini-flash-latest (gemini-2.5-flash ya no está disponible para cuentas nuevas), cambiable sin tocar
     código). Llamada: POST https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent con el encabezado
     x-goog-api-key, systemInstruction, contents y generationConfig.responseMimeType="application/json"; si el modelo lo permite,
     desactiva el «pensamiento» (thinkingBudget 0) para no gastar tokens. La interfaz json_estructurado no cambia, así que CU-07, CU-23 y
     CU-42 siguen igual. Un error 429 (límite gratuito), 503 (modelo saturado) o cualquier fallo cae al modo de respaldo con reglas locales, como hoy. Pruebas con
     un doble en memoria para ambos proveedores. Si la clave no existe, todo sigue en modo de respaldo.
   - FCM_CREDENCIALES acepta también el contenido JSON de la cuenta de servicio (variable FCM_CREDENCIALES_JSON), porque en Railway no
     hay archivos.
2. Frontend en Railway: Dockerfile en dos etapas (compila con node, sirve con nginx en el puerto PORT). La dirección de la API no se
   graba al compilar: al arrancar el contenedor se genera /config.js con la variable API_URL (window.__API_URL__, que api.config.ts ya
   lee), y index.html lo carga primero (en desarrollo, un config.js vacío). nginx devuelve index.html en las rutas de la app y no guarda
   en caché ngsw.json, index.html ni config.js. CORS_ORIGINS y FRONTEND_URL del backend llevan la URL pública del frontend. Comprueba
   que el service worker, el manifest y el push web funcionan por HTTPS.
3. Móvil: quita usesCleartextTraffic del AndroidManifest. Integra Firebase Cloud Messaging (firebase_core, firebase_messaging, el plugin
   google-services de Gradle y el permiso POST_NOTIFICATIONS de Android 13): la app pide el permiso, registra el token como dispositivo
   MOVIL en el backend al iniciar sesión, lo quita al cerrar sesión y muestra la notificación nativa con la app cerrada, en segundo
   plano y abierta. Usa movil/android/app/google-services.json, que el usuario descarga de Firebase para el applicationId actual
   (com.example.fashionstore_movil) y deja en esa carpeta: si todavía no está, avísame en español y espera; no inventes uno. Sin
   Firebase el modo actual (avisos dentro de la app) sigue funcionando. El flujo apk.yml compila con ese archivo.
4. Prendas de demostración reales. En D:\proyectos\1er parcial si2\Imagenes PNG hay 7 PNG con fondo transparente. Cópialos a
   backend/app/seed_data/prendas/ reducidos a 1200 px de lado mayor, conservando la transparencia, con estos nombres y prendas:
   - pngwing.com (1).png → camiseta-raglan-gris.png: «Camiseta Raglán Gris» (manga 3/4, gris con mangas oscuras)
   - pngwing.com (2).png → chaqueta-cuero-negra.png: «Chaqueta de Cuero Negra»
   - pngwing.com (3).png → polo-blanco.png: «Polo Blanco»
   - pngwing.com (4).png → camiseta-mostaza.png: «Camiseta Mostaza»
   - pngwing.com.png → camiseta-beige.png: «Camiseta Beige»
   - —Pngtree—navy t-shirt template for branding_23265449.png → camiseta-azul-marino.png: «Camiseta Azul Marino»
   - —Pngtree—olive green t-shirt with dove_23735499.png → camiseta-verde-oliva.png: «Camiseta Verde Oliva Estampada»
   El seed agrega las 7 prendas a las dos empresas (con precios distintos, en Bs), cada una con su color real, tallas S, M, L y XL
   dentro del grupo de tallas de su categoría, stock en las sucursales y su imagen como foto del producto y como PNG del vestidor
   (anchor_config calculado a partir del recuadro visible del PNG: la línea de hombros cerca del borde superior de la prenda; la chaqueta
   y la manga 3/4 también son prendas superiores). Reemplazan a las prendas de demostración dibujadas con Pillow, que ya no se cargan.
   Mantén pruebas del seed y del vestidor con estas imágenes y comprueba que cada empresa solo ve sus archivos.
5. Arregla la prueba test_04_aviso_de_vencimiento_cercano de tests/test_cu36_plan_y_uso.py: falla entre las 20:00 y las 24:00 de Bolivia
   porque compara con current_date de la base (UTC) y la app usa la fecha de Bolivia (zona_horaria_horas). Usa en la prueba la misma
   fecha que usa la app.
6. Archivos de Railway: backend/railway.toml y frontend/railway.toml (builder Dockerfile, health check del backend), y un
   backend/.env.example completo y comentado con TODAS las variables (SECRET_KEY, DATABASE_URL, CORS_ORIGINS, FRONTEND_URL, MEDIA_DIR,
   CARGAR_DATOS_DEMO, BREVO_API_KEY, BREVO_SENDER_EMAIL, BREVO_SENDER_NAME, STRIPE_SECRET_KEY, STRIPE_PUBLISHABLE_KEY, IA_PROVEEDOR, GEMINI_API_KEY,
   ANTHROPIC_API_KEY (opcional), IA_MODELO, VAPID_PUBLIC_KEY, VAPID_PRIVATE_KEY, VAPID_SUBJECT, FCM_PROYECTO, FCM_CREDENCIALES_JSON).
7. Escribe docs/DESPLIEGUE.md en español, paso a paso para alguien que nunca usó Railway: crear el proyecto desde el repo de GitHub, el
   plugin de Postgres, los dos servicios con su «Root Directory», el Volume del backend en /app/media, las variables de cada servicio
   (con referencias como ${{Postgres.DATABASE_URL}}), generar el dominio público de cada servicio (Settings → Networking), el primer
   arranque con CARGAR_DATOS_DEMO=true, cómo ver los registros, y cómo crear la variable API_URL en GitHub (Settings → Secrets and
   variables → Actions → Variables) para compilar el APK. Incluye una tabla «Clave · dónde se genera · dónde se pone» con el paso exacto
   para: SECRET_KEY, Brevo (clave de API y remitente verificado), Stripe (claves de prueba), Google Gemini (clave de API de Google AI Studio: gratis y sin tarjeta),
   VAPID (scripts/generar_vapid.py) y Firebase (proyecto, app Android, google-services.json y clave privada de la cuenta de servicio).
   Aclara que Railway cobra por uso después de su crédito de prueba. Actualiza el README con un enlace a esa guía.
Corre pytest, npm run build, flutter analyze y flutter test, y haz commit. Si algo necesita una clave que aún no existe, ese punto
queda en modo simulado y me avisas qué falta. Mismas reglas.
```

## 8. Cómo probar el móvil

Decisión del equipo: **sin cable y sin emulador**. Mientras se desarrolla, el móvil se prueba con `flutter analyze` y `flutter test` (lógica, sincronización offline y pantallas). Al final, con el backend ya desplegado, se genera la app instalable y se prueba en los celulares de los dos integrantes.

- **Durante las fases:** Claude Code corre `flutter analyze` y `flutter test` al terminar cada una. Eso no prueba la cámara ni el rendimiento del vestidor virtual.
- **App instalable (`.apk`) sin Android Studio:** el repo tendrá un flujo de GitHub Actions (`.github/workflows/apk.yml`) que compila el `.apk` en la nube, con la dirección de la API en una variable del repositorio (`API_URL`). El `.apk` se descarga desde la pestaña *Actions* de GitHub y se pasa por WhatsApp o Drive; en el celular se acepta «instalar apps de origen desconocido». Hace falta la carpeta `movil/android/`, que se genera una sola vez con `flutter create --platforms=android .` (no necesita Android Studio). La alternativa local es `flutter build apk --release`, que sí necesita el SDK de Android.
- **Antes del despliegue (opcional, recomendado para el vestidor):** un `.apk` que apunte a la PC por Wi‑Fi (`API_URL=http://IP_DE_LA_PC:8000/api`), instalado en el celular, sirve para ver si la cámara y la detección de pose rinden bien sin esperar al despliegue.
- **Notificaciones push en el celular:** con Firebase (sección 10) llegan con la app cerrada; sin Firebase se muestran dentro de la app.

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

- **Claves de prueba de Stripe** (CU-32): crear la cuenta gratis, activar el *modo de prueba* y copiar `STRIPE_SECRET_KEY` y `STRIPE_PUBLISHABLE_KEY` a `backend/.env`. El adaptador solo se probó contra un Stripe simulado en memoria; con las claves hay que hacer una compra real de prueba (4242 4242 4242 4242) y ver el pago en el panel de Stripe. Sin claves todo funciona en modo simulado.
- Cuenta de Brevo para el correo de restablecer contraseña, cuando se despliegue.
- **Firebase (opcional, Fase K):** para que el push llegue al teléfono con la app cerrada hace falta un proyecto gratis de Firebase (agregar la app Android, bajar `google-services.json` y poner la credencial en `.env`). Sin eso, la app muestra el aviso como notificación local al abrirse o sincronizar. El push web no necesita cuenta, pero exige HTTPS al desplegar (en `localhost` funciona).
- Crear las cuentas de **Railway**, **Brevo**, **Stripe** (modo de prueba), **Firebase** y **Google AI Studio** (clave de Gemini, gratis y sin tarjeta) y generar las claves; la tabla «Clave · dónde se genera · dónde se pone» está en `docs/DESPLIEGUE.md` (la escribe el Prompt L). Las claves nunca se pegan en el chat ni en el código: solo en las variables de Railway y en `backend/.env`.
- Medir FPS y latencia del vestidor virtual en un celular (Fase I) y pasarme los números.

## 11. Para el final

- Pasar al Word de la presentación 2 todo lo de `docs/MENSAJES_PENDIENTES_WORD.md` (mensajes de CU-08, 09, 10, 11, 12, 24, 25, 32 y RF11, más lo que salga de las fases siguientes).
- `CLAUDE.md` y este plan nombran a Claude Code: decidir qué hacer con ellos antes de la entrega final.
- Revisar en Word los números de página del índice del documento.
- Al desplegar con HTTPS: quitar `usesCleartextTraffic` de `movil/android/app/src/main/AndroidManifest.xml` y poner la URL real en la variable `API_URL` de GitHub.
- Word: RN06 pasa a tres planes y se agregan la bitácora, el push y la compra offline en conflicto; todo queda listado en `docs/MENSAJES_PENDIENTES_WORD.md`.

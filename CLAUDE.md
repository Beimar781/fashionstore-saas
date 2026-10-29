# FashionStore SaaS — guía para Claude Code

Proyecto de la materia Sistemas de Información 2 (INF 412-SA), segundo parcial: FashionStore evolucionado a **SaaS multitenant**,
documentado con **ICONIX + UML 2.5+**. El documento Word aprobado manda: el código debe coincidir con él (RNF12).

## Stack (obligatorio por el enunciado)
Backend Python + **FastAPI** · Web **Angular** PWA (Service Worker, manifest, IndexedDB) · Móvil **Flutter + Dart + SQLite** ·
**PostgreSQL** compartida con aislamiento lógico por `empresa_id` · API REST · IA por API · despliegue en la nube.
Prohibido: Shopify/Magento/PrestaShop/WooCommerce. No usar Django/Celery/Redis (eran del primer parcial).

## Reglas de arquitectura
- Una carpeta por caso de uso dentro de su paquete: `backend/app/modules/<paquete>/cuNN_<nombre>/{router,service,repository,schemas}.py`.
  Presentación (router) → negocio (service) → persistencia (repository). Los routers no contienen reglas de negocio.
- **Multitenant:** todo modelo de empresa lleva `empresa_id`; su repositorio hereda de `app/core/tenant.py::TenantRepository`;
  el `empresa_id` sale SIEMPRE del token (`Contexto`), nunca del cuerpo de la petición. Recurso de otra empresa ⇒ 404.
- Rutas de empresa: `Depends(contexto_operativo(ROL))` (verifica rol + empresa activa + suscripción vigente).
  Rutas de plataforma: `Depends(requerir_roles(SUPERADMIN))`. Funcionalidades por plan: `exigir_funcionalidad("reportes_ia")`.
- Paquetes se hablan por `publico.py`, no por repositorios ajenos. Registrar routers en `app/api.py` y modelos en `app/db_models.py`.
- Esquema con **Alembic** (`alembic revision -m "..."`; nunca editar la migración 0001). Los textos de error son los de las fichas de CU.
- Web: `features/<paquete>/` con rutas lazy; llamadas HTTP en `core/api/*.api.ts`; estado con signals (la app es zoneless).
- Móvil: `lib/features/<paquete>/{data,presentation}`; SQLite en `lib/core/db`; operaciones offline con UUID generado en el cliente y estados
  REGISTRADA_LOCAL → ENVIADA → CONFIRMADA | RECHAZADA | EN_CONFLICTO (RN11/RN12); el reenvío es idempotente (RNF05).
- **Mensajes pendientes para el Word (regla 11):** al terminar cada fase, agregar a `docs/MENSAJES_PENDIENTES_WORD.md` los mensajes nuevos (con su
  código HTTP), las reglas de negocio y las decisiones que no están en las fichas del Word. De ahí sale la actualización del documento de la presentación 2.
- **Servicios externos (regla 12):** Stripe, correo, IA, servicio de impuestos: un adaptador con modo simulado cuando no hay claves, probado con un doble en
  memoria, y las claves solo en `backend/.env`. Nunca claves en el código ni en el chat.
- **Librerías nuevas (regla 13):** se agregan a `requirements.txt` o `package.json` y se comprueba con una instalación limpia
  (`pip install -r requirements.txt`, `npm install`).
- **Restricciones CHECK (regla 14):** antes de usar un valor nuevo en una columna con `CHECK` (tipos y referencias de inventario, estados, métodos de pago),
  revisar la restricción existente y ampliarla en la migración nueva. Una migración ya subida nunca se edita.
- **Reutilizar lo construido (regla 15):** pedidos (con `canal` DIGITAL o PRESENCIAL y entrega EN_TIENDA), numeración de comprobantes `CMP-<sucursal>-<número>`,
  generador de PDF del comprobante (`cu12_historial_compras/comprobante.py`), pasarela del CU-32 y bitácora de inventario (referencias `VENTA`, `PEDIDO` y
  `DEVOLUCION` ya permitidas) en vez de duplicarlos.
- **Bitácora (regla 16):** toda operación de escritura nueva (POST, PUT, PATCH, DELETE) queda registrada por el middleware de `plataforma/bitacora`; al crear un endpoint, se agrega su ruta a la tabla de
  etiquetas (`plataforma/bitacora/etiquetas.py`, con su detalle en español) y hay una prueba que falla si falta alguna. Nunca se guardan contraseñas, tokens ni datos de tarjeta, y la bitácora no se edita ni se borra
  (la bitácora de inventario `movimientos_inventario` es otra cosa y no se toca).

## Pruebas
`cd backend && python -m pytest -q` — una prueba por paso de las tablas 5.2.1/5.3.1 del documento (`tests/test_cuNN_*.py`).
Al agregar un caso de uso, agregar su archivo de pruebas con el mismo formato.

## Estructura: SaaS y primer parcial
Lo del SaaS multitenant va a simple vista (`backend/app/modules`, `frontend/.../features`, `movil/lib/features`, `backend/tests`).
Los casos de uso conservados del primer parcial (Anexo B del documento) van en subcarpetas aparte: `backend/app/primer_parcial`,
`frontend/.../features/primer-parcial`, `movil/lib/primer_parcial` y `backend/tests/primer_parcial`. En ambas zonas: un paquete por
carpeta y un caso de uso por subcarpeta. Los paquetes se hablan solo por `publico.py`, sin dependencias circulares.
El plan completo (casos de uso por fase, paquetes y prompts) está en `docs/PLAN_PRIMER_PARCIAL.md`; el enunciado del primer parcial,
en `D:\proyectos\1er parcial si2\Examen1-Ecommerce-Si2-s2-26.pdf`.

## Forma de trabajo (obligatoria)
- **Idioma:** todo lo que le escribas al usuario va en **español**: resúmenes, dudas, errores y explicaciones. Si algo sale mal o tienes una duda, pregúntale en español antes de decidir.
- **Al terminar cada tarea:** corre las pruebas (`cd backend && python -m pytest -q`, `cd frontend && npm run build`, y en el móvil `flutter analyze` y `flutter test`).
  - Si todo pasa: haz `git add`, `git commit` y `git push` con la identidad de git del usuario (no cambies `user.name` ni `user.email`). Mensaje corto en español, por ejemplo «Agrega catálogo por empresa (CU-16 a CU-19)», sin líneas de coautoría.
  - Si algo falla: **no hagas commit**; explica en español qué falló y propón la corrección.
- **Estilo del código:** debe poder explicarlo un estudiante en una defensa. Sigue el estilo del lote 1: nombres en español, funciones cortas, un servicio por caso de uso, sin abstracciones innecesarias. Comentarios solo donde expliquen una regla de negocio (RN o paso de la ficha del CU); nada de comentarios largos ni docstrings extensos.
- **Al final de cada fase**, muestra en la terminal un resumen en español: qué casos de uso quedaron, los archivos principales y, por cada CU, 3 líneas de cómo fluye (router → service → repository). Es para que el equipo lo estudie para la defensa.

## Dónde está cada cosa
`docs/TRAZABILIDAD.md` (CU → código → pruebas) · `docs/PENDIENTES.md` (lotes 2 y 3 y portado de los CU conservados) · `docs/PLAN_PRIMER_PARCIAL.md` (plan por fases) · `README.md` (arranque).

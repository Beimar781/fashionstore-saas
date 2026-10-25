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

## Pruebas
`cd backend && python -m pytest -q` — una prueba por paso de las tablas 5.2.1/5.3.1 del documento (`tests/test_cuNN_*.py`).
Al agregar un caso de uso, agregar su archivo de pruebas con el mismo formato.

## Dónde está cada cosa
`docs/TRAZABILIDAD.md` (CU → código → pruebas) · `docs/PENDIENTES.md` (lotes 2 y 3 y portado de los CU conservados) · `README.md` (arranque).

# Cobertura del enunciado del 2.º parcial

Una fila por requisito de las secciones 4 a 11 del enunciado y de los RNF01 a RNF12: dónde está implementado, qué lo prueba y su estado.
**Estado:** ✔ implementado y probado · ◐ implementado, con parte manual o parcial (se explica) · ✘ pendiente.
Las pruebas del backend están en `backend/tests/`, las del frontend en `frontend/src/app/**.spec.ts` y las del móvil en `movil/test/`.

## 4. ICONIX
| Requisito | Dónde | Estado |
|---|---|---|
| Aplicar ICONIX (casos de uso → robustez → secuencia → clases) | Documento Word aprobado; el código sigue su estructura: un paquete por caso de uso (`router → service → repository → schemas`) | ◐ el Word se actualiza con `docs/MENSAJES_PENDIENTES_WORD.md` |

## 5. PWA (web)
| Requisito | Dónde | Prueba | Estado |
|---|---|---|---|
| Instalable en navegadores compatibles | `frontend/public/manifest.webmanifest` (íconos 192, 512 y *maskable*, `standalone`), botón «Instalar aplicación» (`core/ui/instalar-app.component.ts`) | `core/ui/pwa.spec.ts` | ✔ (Lighthouse: ver nota 1) |
| Conservar los recursos para las funciones offline | `ngsw-config.json` (shell, rutas lazy, MediaPipe, imágenes) + `public/sin-conexion.html` | `pwa.spec.ts` | ◐ abrir sin red es prueba manual (PRUEBAS_SISTEMA §13.16) |
| Consultar información previamente almacenada | IndexedDB: `core/offline/local-db.service.ts`, `catalogo-local.service.ts` | `almacenamiento-local.spec.ts` | ✔ |
| Registrar operaciones localmente | `core/offline/cola-operaciones.service.ts` | `almacenamiento-local.spec.ts` | ✔ |
| Identificar operaciones pendientes | contador en el menú y franja «Sin conexión» (`layout/shell.component.ts`) | manual | ✔ |
| Sincronizar al recuperar conectividad | evento `online`, reintento con espera creciente, botón manual | `simulacion.spec.ts`, backend `test_cu38_sincronizar.py` | ✔ |
| Informar el estado de las operaciones | «Operaciones» y «Registro» en `features/offline/` | manual | ✔ |
| §5.3: consultar productos, precios, tallas, colores y disponibilidad descargados | `features/catalogo/` con el catálogo local | `test_cu37_cu39_cu40_offline.py` | ✔ |
| §5.3: registrar reserva y venta de contado; consultar pendientes; conservar tras cerrar | `features/offline/registrar-offline.component.ts`, IndexedDB | `almacenamiento-local.spec.ts` (migración y persistencia) | ✔ |
| Avisar información desactualizada | «Datos al dd/mm hh:mm; pueden estar desactualizados» + actualización automática a las 6 h (`catalogo-local.service.ts`) | manual | ✔ |
| §5.4: una operación enviada no desaparece | solo cambia de estado (`guardarOperacion`) | `almacenamiento-local.spec.ts` | ✔ |

## 6. Móvil Flutter + SQLite
| Requisito | Dónde | Prueba | Estado |
|---|---|---|---|
| Descargar un subconjunto del catálogo; consultar productos, precios y existencias | `movil/lib/features/offline/data/offline_repository.dart` | `offline_test.dart` | ✔ |
| Registrar reservas y ventas de contado sin conexión | `registrar_offline_screen.dart` | `offline_test.dart` | ✔ |
| Consultar pendientes; reiniciar sin perder datos | `modo_offline_screen.dart`, SQLite v5 (`core/db/local_database.dart`) | `almacenamiento_relacional_test.dart` | ✔ |
| Sincronizar al restablecer Internet; consultar el resultado | `connectivity_plus` → `offline_controller.dart`; pantalla «Registro de sincronización» | `conectividad_test.dart`, `almacenamiento_relacional_test.dart` | ✔ |
| §6.3 productos, sucursales, clientes mínimos | tablas `productos_locales`, `sucursales_autorizadas`, `clientes_locales` | `offline_test.dart` | ✔ |
| §6.3 ventas y detalles; reservas y detalles; operaciones pendientes; estados y resultados | `ventas_locales`, `detalle_venta_local`, `reservas_locales`, `detalle_reserva_local`, `operaciones_pendientes`, `resultados_sincronizacion`, con claves foráneas (`features/offline/data/detalle_local.dart`) | `almacenamiento_relacional_test.dart` (incluye migración v4 → v5) | ✔ |
| §6.4 identificación única, empresa y sucursal, reintentos, sin duplicados, confirmación, rechazo o conflicto | UUID del cliente (RN11), estados, `esperaRestante` (espera creciente), backend idempotente | `reintentos_test.dart`, `test_cu38_sincronizar.py` | ✔ |

## 7. Ventas offline
| Requisito | Dónde | Prueba | Estado |
|---|---|---|---|
| §7.2 identificador, empresa y sucursal, usuario, fecha y hora (con zona), productos, cantidades, precios usados, total, forma de pago, estado | `VentaOfflineIn` (`backend/app/modules/offline/schemas.py`), `ventas_locales`/`ventas` en el cliente | `test_r4_venta_completa.py` | ✔ |
| Precio distinto al sincronizar | regla: **la venta pasa a EN_CONFLICTO** con «El precio de una prenda cambió desde que se registró la venta.»; el Encargado la reintenta con el precio actual (`PrecioCambio` en `ejecucion.py`) | `test_r4_venta_completa.py` | ✔ |
| Reloj del dispositivo (> 5 min) | `hora_dispositivo` → `aviso_reloj` y `desfase_reloj_segundos` guardado (migración 0018) | `test_r4_venta_completa.py` | ✔ |
| Conflicto por existencias (RN14) | `cu38_sincronizar`, `cu40_conflictos` | `test_cu38_sincronizar.py`, `test_cu37_cu39_cu40_offline.py` | ✔ |
| Gestionar cambios de prendas en un tiempo | CU-41 (plazo configurable) y devolución offline `DEVOLUCION` | `test_cu41_*.py`, `test_r_operaciones_offline_sucursal.py` | ✔ servidor · ◐ falta la pantalla de captura en web y móvil |
| Aportes propios | vestidor virtual (móvil y web), asistente, pago con Stripe, push, comprobante provisional | varios | ✔ |

## 8. Reportes generativos y ML
| Requisito | Dónde | Prueba | Estado |
|---|---|---|---|
| Lenguaje natural escrito o por voz | `features/ia/reporte-generativo.page.ts` (Web Speech API) | manual (voz) | ◐ voz es prueba manual en Chrome/Edge |
| Interpretar el tipo, identificar filtros | `modules/ia/cu23_reportes_generativos/interprete.py` (IA por API con respaldo de reglas) | `test_cu23_reportes_generativos.py` | ✔ |
| Datos reales; más de una tabla | `service.py` (ventas, ranking, reservas, pagos, inventario, stock bajo) | `test_r10_reportes_seguros.py::test_05` (≥ 5 tipos) | ✔ |
| Tablas o gráficos; exportar a Excel o PDF | `core/exportar.py`, `GET /api/ia/reportes/{id}/exportar?formato=xlsx|pdf` | `test_r1_exportar_reportes.py` | ✔ |
| Restringir al tenant; solicitudes ambiguas, incompletas o no soportadas; evitar consultas arbitrarias | especificación cerrada validada (`EspecReporte`), sucursales de la empresa | `test_r10_reportes_seguros.py`, `test_cu23_*` | ✔ |
| Reportes convencionales en Excel, PDF y CSV; inventario por sucursal | `GET /api/reportes/exportar/{tipo}?formato=`, `GET /api/reportes/inventario` | `test_r1_exportar_reportes.py` (tests 06 a 09) | ✔ |
| §8.4 ML: datos sintéticos, supervisado, no supervisado, evaluación, integración, dashboard | `modules/ia/cu42_analitica_ml/` + `features/ia/analitica.page.ts` (exporta a PDF por impresión) | `test_cu42_analitica_ml.py` | ✔ |
| Datos para las demos | `python -m app.demo_historial` (3 meses por sucursal, idempotente, códigos `DEMO-`) | `test_r11_demo_historial.py` | ✔ (lo corre el equipo a mano) |

## 9. SaaS multitenant
| Requisito | Dónde | Prueba | Estado |
|---|---|---|---|
| Empresas, administrador por empresa, usuarios y sucursales | `modules/plataforma/cu33_empresas`, `acceso`, `sucursales` | `test_cu33_empresas.py`, `test_cu13_usuarios.py`, `test_cu14_sucursales.py` | ✔ |
| Planes Básico (2) y Profesional (10), configurables desde el backend | `cu34_planes` | `test_cu34_planes.py` | ✔ |
| Suscripciones: asignar, fechas, estado, cambiar, verificar y restringir | `cu35_suscripciones`, `exigir_funcionalidad` | `test_cu35_suscripciones.py`, `test_cu36_plan_y_uso.py` | ✔ |
| Al menos dos empresas de prueba | seed EMP-A y EMP-B | `test_aislamiento_multitenant.py` | ✔ |
| Seguridad multitenant en el backend | `TenantRepository` + `empresa_id` solo del token; otro tenant → 404 | `test_aislamiento_multitenant.py`, pruebas por caso de uso | ✔ |

## 10. Requisitos no funcionales
| RNF | Dónde | Prueba | Estado |
|---|---|---|---|
| RNF01 Seguridad | JWT, roles, `contexto_operativo`, argon2 | `test_cu02_login.py`, `test_cu13_usuarios.py` | ✔ |
| RNF02 Aislamiento | `core/tenant.py` | `test_aislamiento_multitenant.py` | ✔ |
| RNF03 Persistencia offline | IndexedDB y SQLite | `almacenamiento-local.spec.ts`, `almacenamiento_relacional_test.dart` | ✔ |
| RNF04 Integridad transaccional | una transacción por operación (`cu38_sincronizar`) | `test_cu38_sincronizar.py` | ✔ |
| RNF05 Idempotencia | UUID del cliente + `ya_procesada` | `test_cu38_sincronizar.py`, `test_r_operaciones_offline_sucursal.py` | ✔ |
| RNF06 Recuperación ante fallos | estado `ERROR` → se conserva y se reintenta con espera creciente | `reintentos_test.dart`, `test_cu38_sincronizar.py` | ✔ |
| RNF07 Mantenibilidad | presentación → negocio → persistencia; `publico.py` entre paquetes | `test_arquitectura_paquetes.py` | ✔ |
| RNF08 Compatibilidad | PWA Chrome/Edge; Flutter Android | manual | ◐ |
| RNF09 Rendimiento | índices (migración 0019), paginación, `docs/RENDIMIENTO.md` | `test_r9_indices.py` | ✔ |
| RNF10 Observabilidad | `registro_sincronizacion` (web y móvil) y logs del servidor sin datos personales | `test_r8_logs_sync.py`, `almacenamiento_relacional_test.dart`, `almacenamiento-local.spec.ts` | ✔ |
| RNF11 Calidad | 600+ pruebas del backend, 22+ del frontend, 130+ del móvil | todas | ✔ |
| RNF12 Coherencia documental | `docs/TRAZABILIDAD.md`, este archivo y `MENSAJES_PENDIENTES_WORD.md` | — | ◐ falta pasar al Word |

## 11. Tecnologías
| Componente | Tecnología usada | Estado |
|---|---|---|
| Backend | Python + FastAPI | ✔ |
| Frontend web | Angular (zoneless, signals) | ✔ |
| PWA | Service Worker (`ngsw`), Web App Manifest, IndexedDB (`idb`) | ✔ |
| Móvil | Flutter + Dart | ✔ |
| Persistencia móvil | SQLite (`sqflite`) | ✔ |
| Base central | PostgreSQL (aislamiento lógico por `empresa_id`) | ✔ |
| Integración | API REST | ✔ |
| IA | Gemini o Claude por API, con respaldo de reglas | ✔ |
| Despliegue | Railway (nube, accesible externamente) | ✔ |
| Conservar AR y comercio electrónico | vestidor virtual, catálogo, carrito, pagos | ✔ |

## Funciones adicionales sin conexión (Parte B del Prompt R)
| Función | Dónde | Estado |
|---|---|---|
| B1 Comprobante provisional `LOC-…` | móvil `comprobante_provisional.dart`; web `comprobante-provisional.ts` (jspdf, bajo demanda) | ✔ |
| B2 Resumen de mi turno · B11 Simular sin conexión | móvil y web | ✔ |
| B3 Devolución sin conexión (plazo guardado en la descarga) | móvil `tareas_sucursal_screen.dart`; web `tareas-sucursal.component.ts`; servidor `ejecucion.py` | ✔ |
| B4 Atención de reservas sin conexión (validar código, preparar, prenda no encontrada, atender; solo Encargado) | móvil, web y servidor | ✔ |
| B5 Recepción · B6 Ajuste de inventario (por diferencia) | móvil, web y servidor | ✔ |
| B7 Escaneo de códigos de barras y QR | móvil (`escaner_screen.dart`, ML Kit); web (`escaner.component.ts`, `BarcodeDetector`, solo navegadores que lo traen) | ✔ |
| B8 Consulta sin conexión de otros roles: «Datos al…» global, caché de la API con tope de 3 s, borrado del caché al cerrar sesión, «Generar un reporte con IA necesita Internet.» | web `shell.component.ts`, `ngsw-config.json`, `auth.service.ts` | ◐ (lectura de lo ya visitado; no se descargan listados completos de Administrador o Proveedor) |
| B9 Propuesta del proveedor sin conexión | web `abastecimiento.page.ts`; servidor `PROPUESTA_PROVEEDOR` (migración 0022) | ✔ (el móvil no tiene pantalla de Proveedor) |
| D5 Indicador de estado en la barra, «Deshacer» una operación sin enviar, línea de tiempo y pantalla de demostración | web `estado-conexion.component.ts`, `linea-de-tiempo.ts`, `demostracion.component.ts`; móvil `estado_conexion_chip.dart`, `linea_de_tiempo.dart`, `demostracion_tab.dart` | ✔ |
| B10 Sincronización en segundo plano | web `public/sw-sync.js` (Background Sync, solo Chrome/Edge); móvil: al volver a primer plano y con `connectivity_plus` | ◐ |
| Extra: reportes con IA por voz (dictar, conversar, escuchar) | web `reporte-generativo.page.ts`, `core/voz/voz.service.ts` (solo Chrome/Edge) | ✔ |

## Límites conocidos
- La exportación a PDF de la analítica del CU-42 usa la impresión del navegador; los reportes con IA y los convencionales sí tienen PDF generado en el servidor.
- El aviso local de «hay ventas por sincronizar» en el móvil es una alerta dentro de la app (sin `workmanager`).

**Nota 1.** Lighthouse 12 o posterior eliminó la categoría «PWA» de su informe; la instalabilidad se verifica con las condiciones del manifiesto (`pwa.spec.ts`) y manualmente en Chrome (DevTools → Application → Manifest).

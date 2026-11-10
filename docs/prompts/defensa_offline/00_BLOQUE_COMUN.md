# Bloque común (va al inicio de cada prompt D1 a D5)

Contexto: FashionStore SaaS, defensa el jueves por la mañana. Objetivo general: que el modo sin conexión NO sea una sección aparte, sino que las pantallas principales de web (Angular PWA) y móvil (Flutter) funcionen igual con y sin conexión, con los mismos botones y ventanas, y que al volver la red todo se sincronice solo sin recargar la página ni reiniciar la app.

Reglas:
- Trabaja en la rama correccion-pago (Railway despliega desde ahí). Al terminar con todo en verde, haz también merge a main y push.
- Reutiliza lo que ya existe: cola-operaciones.service.ts, local-db.service.ts, connectivity.service.ts, catalogo-local.service.ts, comprobante-provisional.ts (web); offline_repository.dart, offline_controller.dart, local_database.dart, conectividad.dart (móvil); modules/offline (backend). No dupliques lógica: mueve o reutiliza componentes.
- No cambies los estados ni las reglas (RN11, RN12, RN14, RNF05): UUID generado en el cliente, reenvío idempotente, conflicto si falta stock.
- La sección «Modo sin conexión» se conserva como panel de diagnóstico (cola, registro de sincronización, simular sin conexión), pero ya no debe ser necesaria para operar.
- Estilo del proyecto: nombres en español, funciones cortas, sin abstracciones nuevas. Toda ruta nueva de escritura va a plataforma/bitacora/etiquetas.py.
- Mientras trabajas, corre solo las pruebas de lo que estás tocando (por ejemplo python -m pytest -q tests/<archivo>). La suite completa va UNA sola vez al final, antes del commit: cd backend && python -m pytest -q; cd frontend && npm run build; cd movil && flutter analyze && flutter test. Si todo pasa: commit y push con mi identidad de git, mensaje corto en español, SIN líneas de coautoría. Si algo falla: no hagas commit y explícame qué falló.
- Actualiza docs/PRUEBAS_SISTEMA.md (pasos manuales nuevos), docs/TRAZABILIDAD.md y docs/MENSAJES_PENDIENTES_WORD.md (mensajes y reglas nuevas para el Word).
- Responde en español con un resumen corto: qué quedó, archivos principales y cómo probarlo a mano.

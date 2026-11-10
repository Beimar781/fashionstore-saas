# PROMPT_D5 · Extras, documentación y APK

## Bloque común

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

## Tarea

Tarea 5: extras para la defensa, documentación y entrega.

Extras (solo si las tareas 1 a 4 están en verde; en este orden, y detente si algo se complica):
1. Indicador de estado permanente en la barra superior de web y móvil: en línea / sin conexión / sincronizando, con el número de operaciones pendientes; al tocarlo abre el detalle de la cola.
2. «Deshacer» una operación que aún no se sincronizó (compra, reserva, venta, ajuste) desde su pantalla normal, devolviendo el stock local.
3. Línea de tiempo de cada operación (registrada local → enviada → confirmada / conflicto → resuelta) visible al tocarla, con fecha y dispositivo.
4. Pantalla de demostración para la defensa en el panel de diagnóstico: botón «Simular sin conexión», cola en vivo y registro de sincronización en una sola vista.

Documentación:
- docs/PRUEBAS_SISTEMA.md: una sección nueva «Demostración de la defensa» con los guiones paso a paso: (a) venta de contado sin conexión del Cajero, (b) dos cajeros y la última unidad con devolución del efectivo, (c) compra del Cliente sin conexión pagada con tarjeta guardada, con y sin stock, (d) Encargado: recepción, ajuste y reservas sin conexión, (e) aviso de reconexión sin recargar.
- docs/MENSAJES_PENDIENTES_WORD.md: lista corta y exacta de lo que cambia en el Word (mensajes nuevos, regla del cobro con tarjeta guardada, pantallas que cambiaron).
- docs/TRAZABILIDAD.md y docs/COBERTURA_ENUNCIADO.md actualizados.

Entrega:
- Merge a main y push; confirmar que Railway desplegó backend y frontend, y correr python scripts/humo_produccion.py <url del backend>.
- Generar el APK nuevo con el workflow de GitHub Actions y decirme de dónde descargarlo.
- Resumen final: qué funciona sin conexión por actor (Cliente, Cajero, Encargado, Proveedor, Administrador) en web y en móvil, y qué sigue necesitando Internet.

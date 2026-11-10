# PROMPT_D2 · Caja integrada (Cajero)

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

Tarea 2: la pantalla normal de Caja (venta presencial de contado, CU-29) funciona igual con y sin conexión, en web y móvil.

- En la pantalla principal de Caja: buscar o escanear prendas, armar la venta, cobrar en efectivo y emitir comprobante con los MISMOS botones y ventanas. Si no hay red (o está «Simular sin conexión»), la venta se guarda en la cola con su UUID, baja el stock local, y se entrega el comprobante provisional LOC-<sucursal>-<código>; con red, flujo normal con comprobante CMP-….
- El catálogo y el stock que usa Caja sin red salen de la copia local; si no hay copia descargada, descargarla sola en segundo plano cuando hay red (al iniciar sesión y cada cierto tiempo), sin que el cajero tenga que ir a otra pantalla.
- En la misma pantalla de Caja: contador de ventas pendientes de sincronizar, el estado de cada venta del turno (pendiente, confirmada, en conflicto) y «Resumen de mi turno».
- Devolución (CU-41) desde su pantalla normal también funciona sin red, con las mismas validaciones (plazo, lo ya devuelto).
- Reutiliza registrar-offline.component.ts, resumen-turno.component.ts y comprobante-provisional.ts: muévelos o intégralos, no los dupliques. La ruta /pos/offline queda solo como diagnóstico.
- Caso de la defensa que debe funcionar de punta a punta: dos cajeros en dos dispositivos sin red venden la última unidad de la misma prenda; al volver la red, la primera venta que llega se confirma y la segunda queda EN_CONFLICTO; el Encargado la descarta y se registra la devolución del efectivo al cliente. Agrega una prueba de backend para este caso exacto si no existe (dos operaciones con UUID distintos sobre la última unidad) y los pasos manuales con dos navegadores.
- Móvil: lo mismo en la pantalla de venta del Cajero.

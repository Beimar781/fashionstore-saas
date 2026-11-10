# PROMPT_D3 · Encargado y Proveedor integrados

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

Tarea 3: las pantallas normales del Encargado y del Proveedor funcionan igual con y sin conexión, en web y móvil.

Encargado:
- Inventario de sucursal: recepción de mercadería y ajuste (conteo, merma) desde su pantalla normal; sin red se encolan y el stock local cambia al instante; con red, flujo normal. Incluye el botón «Escanear».
- Reservas de la sucursal: validar código, «Preparar», marcar «No encontrada» y «Atender» desde la pantalla normal de atención de reservas; sin red se encolan y la copia local cambia.
- Conflictos: la pantalla «Conflictos de sincronización» muestra para cada caso qué pasó, qué pidió el otro dispositivo y los botones REINTENTAR y DESCARTAR; al descartar una venta ya cobrada indica el monto a devolver.
- Reutiliza tareas-sucursal.component.ts; /sucursal/offline queda como diagnóstico.

Proveedor:
- «Proponer producto» desde su pantalla normal, con y sin red (ya existe en web; verificar que no dependa de la sección aparte) y agregarlo en móvil si el Proveedor tiene pantalla allí; si no la tiene, no la crees.

Administrador:
- Sin red, sus pantallas muestran los últimos datos con la franja «Datos al…» y los botones que necesitan Internet (reportes con IA, exportes, planes) quedan deshabilitados con el motivo, en vez de dar error.

Pruebas: backend ya cubre AJUSTE_INVENTARIO, RECEPCION, DEVOLUCION y atención de reservas offline; agrega las de interfaz que falten y los pasos manuales.

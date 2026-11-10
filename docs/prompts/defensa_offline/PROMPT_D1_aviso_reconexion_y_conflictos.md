# PROMPT_D1 · Aviso de reconexión y conflictos visibles

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

Tarea 1: aviso al volver la conexión y resultado de la sincronización, en web y móvil.

Web:
- Cuando connectivity.service detecte que volvió la red (real o al apagar «Simular sin conexión»), mostrar un aviso emergente global (toast en el layout/shell, visible en cualquier pantalla): «Conexión restablecida. Sincronizando N operaciones…» y al terminar «Sincronización completa: X confirmadas, Y en conflicto, Z rechazadas», con botón «Ver detalle». Sin recargar la página ni perder lo que el usuario estaba haciendo (formularios, carrito, ruta actual).
- Si la pestaña está en segundo plano y hay permiso de notificaciones, mostrar además una notificación del sistema con el mismo texto (Notification API / service worker).
- Al perder la red: aviso «Sin conexión: sus acciones se guardarán en este dispositivo y se enviarán solas al volver la red.»
- Las pantallas abiertas deben refrescar sus datos solas tras sincronizar (mis compras, mis reservas, caja, inventario), sin recargar.

Móvil:
- Lo mismo con conectividad.dart y offline_controller.dart: SnackBar/banner global al perder y recuperar la red, y notificación local del sistema si la app está en segundo plano. Sin reiniciar la app ni volver al inicio.

Conflictos visibles para quien los sufre (web y móvil):
- Cliente: en «Mis compras» y «Mis reservas», la operación en conflicto o rechazada aparece con etiqueta y motivo claro («La prenda se agotó mientras estaba sin conexión. No se le cobró nada.» o «Se le devolvió Bs X» si hubo cobro), y un botón «Elegir otra talla o sucursal» que lleva a la prenda.
- Cajero: en Caja, lista «Ventas con problema» con el motivo y el estado de la devolución del efectivo.
- Cada aviso de conflicto también llega a la campana (RF11) usando avisar_cliente donde aplique.

Pruebas: unitarias web del servicio de avisos (pierde red, vuelve red, resumen correcto), prueba de widget en móvil, y los pasos manuales en PRUEBAS_SISTEMA.md.

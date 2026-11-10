# PROMPT_D4 · Pago del Cliente sin conexión con tarjeta guardada

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

Tarea 4: el Cliente puede dejar pagada su compra sin conexión usando una tarjeta guardada; el cobro real lo hace el servidor al sincronizar.

Seguridad (obligatorio): NUNCA guardar número de tarjeta, fecha ni CVC en el dispositivo ni en la cola. Solo se guarda el identificador interno de la tarjeta guardada y lo que ya se muestra (marca y últimos 4 dígitos). No se permite ingresar una tarjeta nueva sin conexión: mostrar «Para usar una tarjeta nueva necesita Internet. Puede pagar con una tarjeta guardada o dejar la compra por pagar.»

Cliente (web y móvil), en el checkout normal:
- Guardar en local la lista de tarjetas guardadas (marca, últimos 4, vencimiento) cuando hay red.
- Sin red, en «Entrega, facturación y pago» ofrecer: «Pagar con Visa terminada en 4242 al volver la conexión» o «Dejar por pagar». Con la primera, pedir confirmación explícita: «Autorizo el cobro de Bs X a esta tarjeta cuando se confirme mi compra.»
- La operación COMPRA de la cola lleva tarjeta_guardada_id y el total autorizado.

Backend (modules/offline/ejecucion.py::_compra y la pasarela del CU-32):
- Al sincronizar: primero validar stock. Si no alcanza: EN_CONFLICTO, sin cobro, mensaje «La prenda se agotó mientras estaba sin conexión. No se le cobró nada.» y aviso push.
- Si hay stock: crear el pedido y cobrar la tarjeta guardada desde el servidor (PaymentIntent con el cliente y el método de pago guardados, confirmación fuera de sesión, en BOB). Verificar que la tarjeta pertenece a ese cliente y a esa empresa.
- Si el precio vigente difiere del autorizado: no cobrar; EN_CONFLICTO «El precio cambió; confirme el nuevo total».
- Si el cobro se aprueba: pedido pagado, stock descontado, comprobante CMP-…, aviso push «Su compra fue cobrada y confirmada».
- Si el cobro falla o la tarjeta pide autenticación (3D Secure): el pedido queda «por pagar» (como hoy), con aviso «No pudimos cobrar su tarjeta; complete el pago desde Mis compras». El stock se trata igual que en un pedido por pagar actual.
- Idempotencia: reenviar la misma operación no cobra dos veces (usar el operacion_id como clave de idempotencia de Stripe además de la restricción UNIQUE).
- Reembolso: si una compra cobrada así se devuelve después (CU-41) o el Encargado la anula, se reembolsa a la tarjeta con el flujo de devoluciones existente y el cliente recibe el aviso con el monto.
- Sin claves de Stripe debe funcionar con la pasarela simulada (regla 12), y las pruebas usan el doble en memoria.

Pruebas de backend: compra offline con tarjeta guardada y stock → cobrada y confirmada; sin stock → conflicto sin cobro; reenvío → un solo cobro; tarjeta de otro cliente → rechazo; cobro rechazado → pedido por pagar; precio cambiado → conflicto sin cobro. Pasos manuales con las tarjetas de prueba de Stripe.

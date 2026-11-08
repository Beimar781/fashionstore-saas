# Prompt Q — Todas las funciones del Cliente en modo en línea y sin conexión (web y móvil)

Ejecútalo **después** de los Prompts N, O y P (ya subidos con `git push`). Lee `CLAUDE.md`, `docs/PRUEBAS_SISTEMA.md`, la cola de operaciones sin conexión (`backend/app/modules/offline`, `frontend/src/app/core/offline/cola-operaciones.service.ts`, `movil/lib/features/offline`) y las reglas RN11, RN12, RN13 y RNF05. Todo lo que me escribas va en español. Código explicable en una defensa: nombres en español, funciones cortas, sin abstracciones innecesarias. No toques claves, variables de Railway ni secretos.

## Objetivo
Cada función del Cliente debe poder usarse **con conexión y sin conexión**, en la web (PWA) y en el móvil. Criterio:
- **A. Funciona sin conexión** con datos guardados en el dispositivo y, si cambia algo en el servidor, queda en la cola y se envía sola al recuperar la red (estados REGISTRADA_LOCAL → ENVIADA → CONFIRMADA | RECHAZADA | EN_CONFLICTO; reenvío idempotente).
- **B. Depende físicamente de Internet** (iniciar sesión por primera vez, crear cuenta, recuperar contraseña, cobrar la tarjeta, guardar tarjetas): sin red muestra un mensaje claro en español, **no pierde lo que el usuario escribió**, y donde corresponda deja la acción pendiente para completarla al volver la red.

Haz **un bloque, sus pruebas y un commit por cada punto**. Si un punto no compila o rompe pruebas, no sigas con el siguiente: explícame qué pasó.

## Estado actual (verifícalo antes de tocar nada)
Ya existe sin conexión: catálogo descargado, reservar (`RESERVA`), comprar sin pagar (`COMPRA`, la tarjeta se paga al sincronizar), cola y conflictos, aviso «Sin conexión» en el inicio del móvil. Revisa y dime en tu resumen qué de la tabla siguiente ya estaba cubierto y qué no.

## Tabla de funciones del Cliente y comportamiento sin conexión
1. **Sesión abierta:** con sesión previa, abrir la app sin red entra directo con el contexto guardado (nombre, empresa, plan, sucursal). Un fallo de red al renovar el token **nunca** cierra la sesión; se renueva al volver la red. Verifícalo en web y móvil.
2. **Iniciar sesión por primera vez, Crear cuenta, Recuperar contraseña (B):** «Sin conexión: necesita Internet para iniciar sesión / crear su cuenta / recuperar su contraseña.», sin borrar el formulario.
3. **Catálogo, filtros, detalle, promociones y stock por sucursal (A):** desde la descarga, con la fecha de la última descarga visible («Datos al 30/10 17:40»). Las imágenes de las prendas se guardan también (web: caché del Service Worker o IndexedDB; móvil: archivos locales).
4. **Vestidor virtual (A):** funciona sin red con el modelo local y los PNG descargados (web, por el Prompt P; móvil, ML Kit ya es local). Que «Descargar catálogo» incluya los PNG del vestidor en las dos plataformas.
5. **Asistente de compras (A, degradado):** sin conexión responde con un **modo de reglas local** sobre el catálogo descargado (categoría, color, talla, precio máximo y palabras clave, con la misma interpretación que el modo de respaldo del backend, `cu07_asistente`), marcado como «Respuesta local, sin IA (sin conexión)». Sigue el control por plan guardado en el dispositivo. Web y móvil.
6. **Carrito (A):** sin conexión el carrito se guarda localmente (IndexedDB en web, SQLite en móvil). Al volver la red, el contenido local se fusiona con el carrito del servidor sin duplicar y revalidando existencias (una prenda agotada se avisa y se quita). «Finalizar compra» sin conexión pide los mismos datos que la compra en línea (retiro o entrega a domicilio con dirección, NIT/CI y razón social, del Prompt O) y registra una operación `COMPRA` en la cola.
   - **Backend:** amplía `CompraOfflineIn` con `tipo_entrega`, `direccion_entrega`, `nit_ci` y `razon_social` y que la sincronización los pase al mismo servicio del checkout en línea (reutiliza, regla 15). Valores nuevos en columnas con `CHECK` → revisar la restricción y ampliarla en una migración Alembic nueva (regla 14); nunca editar una migración subida.
7. **Pago con tarjeta (B, diferido):** sin conexión no se cobra nada; el pedido queda «por pagar» y se avisa «Se pagará con tarjeta al recuperar la conexión, desde Mis compras». Tras sincronizar, el aviso push/campana ya existente (regla 17) le recuerda pagar, y desde «Mis compras» (web y móvil) se paga con Stripe.
8. **Mis compras (A, lectura):** se guarda la última lista de compras vista y se muestra sin red junto con las operaciones pendientes de la cola y su estado, en la misma lista y con una etiqueta «Pendiente de sincronizar».
9. **Comprobante PDF (A, solo lo ya visto):** todo comprobante abierto con conexión se guarda en el dispositivo (móvil: carpeta de documentos de la app, no la temporal; web: caché/IndexedDB) y se puede volver a abrir sin red. Uno nunca descargado, sin red: «Sin conexión: este comprobante todavía no se descargó. Ábralo una vez con Internet para tenerlo disponible sin conexión.»
10. **Reservar (A):** ya existe como `RESERVA`; verifica que el flujo «Agregar a mi reserva → Mi reserva» del Prompt O también funcione sin red y deje la operación en la cola.
11. **Mis reservas (A):** lista guardada más las reservas pendientes de la cola. **Cancelar sin conexión:** nueva operación `CANCELAR_RESERVA` en la cola (con su motivo opcional). Si la reserva aún no se sincronizó, cancelar solo quita la operación local. Al sincronizar: confirma, o `RECHAZADA` con mensaje si la reserva ya fue atendida o cancelada. Backend: nuevo tipo en la ficha de operaciones con ampliación del `CHECK` por migración, idempotente por UUID del cliente, ruta en `plataforma/bitacora/etiquetas.py` y pruebas (reglas 14 y 16).
12. **Avisos y notificaciones (A):** la lista de avisos se guarda y se lee sin red; marcar como leído sin red se envía luego (sin conflicto posible). Los push llegan al recuperar la conexión.
13. **Tarjetas guardadas (B):** requieren conexión; mensaje claro.
14. **Sincronización:** se dispara sola al volver la red (web: evento `online` y reintento con espera creciente; móvil: `connectivity_plus` o el mecanismo que ya use) y con un botón manual. Un contador de pendientes visible en las dos plataformas y el aviso «Sin conexión» visible también en el layout de la web (no solo en el inicio del móvil).
15. **Recursos de la app sin red (web):** la PWA debe abrir sin red toda la parte del Cliente (el shell y todas las rutas lazy del Cliente deben estar en el caché del Service Worker según `ngsw-config.json`). Comprueba con la compilación de producción servida en local y la red cortada.

## Pruebas
- Backend: una prueba por cada cambio (compra offline con entrega/NIT, `CANCELAR_RESERVA` confirmada y rechazada, reenvío idempotente, aislamiento por empresa → 404).
- Web y móvil: pruebas con dobles en memoria de la cola y de la conectividad (sin red real) para cada función A: guardar localmente, mostrar pendiente, sincronizar, y mensaje de las B.
- Guía manual en `docs/PRUEBAS_SISTEMA.md`: para la web, DevTools → Network → Offline; para el móvil, modo avión; escenarios paso a paso por cada punto de la tabla, con resultado esperado.

## Documentación (regla 11)
`docs/MENSAJES_PENDIENTES_WORD.md`: mensajes nuevos (con su código HTTP), la regla «cada función del Cliente funciona con conexión y sin conexión, o muestra un mensaje claro si depende de Internet», la nueva operación `CANCELAR_RESERVA` y los campos nuevos de `COMPRA`. Actualiza `docs/TRAZABILIDAD.md`.

## Cierre
Corre `cd backend && python -m pytest -q`, `cd frontend && npm run build` (y sus pruebas) y en `movil/` `flutter analyze` y `flutter test`. Si todo pasa: commits por bloque con mi identidad de git, mensaje corto en español, sin líneas de coautoría, y `git push` (Railway aplica las migraciones al arrancar; no toques nada ahí). Si algo falla: no hagas commit y explícame qué pasó.

Dame un resumen en español: la tabla anterior marcada con lo que ya existía, lo que agregaste y lo que quedó pendiente, y qué debo probar a mano en modo avión (móvil) y sin red (web).

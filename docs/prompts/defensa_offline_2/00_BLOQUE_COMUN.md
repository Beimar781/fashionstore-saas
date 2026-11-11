# Bloque común — corrección de lo sin conexión (segunda ronda, defensa del jueves)

Pega este bloque al inicio de CADA prompt (E1 a E5). Está en español porque así trabajamos.

## Contexto
Probamos la versión desplegada en Railway (web) y la app móvil en el celular, y lo sin conexión NO funciona en las pantallas normales:
- **Móvil, cliente:** el detalle de prenda ("Disponibilidad en…") se queda cargando y muestra «Sin conexión con el servidor.»; Reservar y Agregar quedan deshabilitados; «Mi carrito» solo dice «Sin conexión: el carrito necesita Internet.»; el chip de la barra dice «En línea» aunque todo falla.
- **Web, cliente:** «Pagar mi compra» abierto ya sin conexión se queda en «Cargando…» para siempre y no se recarga al volver la red.
- **Web, Cajero EMP-B:** todas las prendas salen «Sin stock» y las fotos salen rotas (solo texto alternativo).
- **Web, varios actores:** pantallas con «Cargando…» eterno o con un vacío engañoso («No hay lotes en tránsito», «No hay reservas…») cuando en realidad no hay red.

## Causas encontradas en el código (no las adivines: verifícalas y corrígelas)
1. **Móvil:** `catalogo_screen.dart` (hoja de la prenda) llama a `repo.opciones/detalle/agregarAlCarrito` sin respaldo local; `carrito_screen.dart` solo lee `/carrito` del servidor; el carrito local y la compra con tarjeta guardada (D4) viven solo en `features/offline/presentation/registrar_offline_screen.dart` (una sección aparte, no el flujo normal). `entrega_screen.dart` y `asistente_screen.dart` no distinguen `sinConexion`.
2. **Web:** el carrito del servidor nunca se copia a la copia local cuando hay red (`carrito-estado.service.ts`: `fijar()` no llama a `guardarLocal()`), por eso `checkout.page.ts` sin red queda con `carrito() == null`. Además `ngOnInit` de varias páginas (`recepciones`, `reservas-sucursal`, `carrito`, `producto-detalle`, `devoluciones`…) solo carga con red o no maneja `status 0`; no hay un patrón común para «sin datos guardados».
3. **«Simular sin conexión»** (`simular-sin-conexion.interceptor.ts`) corta la petición con status 0 ANTES de llegar al service worker, así que la simulación NO usa la caché del SW: una pantalla que funcionaría con el modo avión real falla en la simulación (y al revés puede haber pantallas que fallen en real). Hay que probar las dos formas.
4. **Indicador de estado (móvil):** `OfflineController.enLinea` no se entera cuando el servidor no responde (`ApiException.sinConexion`), por eso dice «En línea» con todo caído.
5. **Datos de Railway:** el stock del Cajero de la sucursal de EMP-B está en cero y las imágenes de la Caja usan una ruta que no resuelve (el catálogo del cliente sí muestra fotos).

## Reglas
- Lee `CLAUDE.md` y respétalo (estilo para defensa, bitácora, mensajes pendientes para el Word, etc.).
- Se puede tocar `main` y las pantallas normales. Lo esencial: **cada funcionalidad sin conexión que pidió la ingeniera debe verse y funcionar en la pantalla normal de la web y de la app móvil**, no en una sección aparte.
- Nunca ver ni escribir contraseñas ni claves. No cambies `user.name` ni `user.email` de git.
- Pruebas de ESTE prompt: solo las de lo que cambies (specs/tests nuevos o afectados). La suite completa se corre al final, en el prompt E5.
- Al terminar: `git add`, `git commit` y `git push` con la identidad del usuario, mensaje corto en español, **sin líneas de coautoría**. Si algo falla, no hagas commit y explica en español.
- Agrega a `docs/MENSAJES_PENDIENTES_WORD.md` los mensajes nuevos (con código HTTP) y reglas nuevas. No cambies el Word.
- Al final muestra un resumen en español: qué quedó, archivos principales y cómo fluye (router → service → repository / pantalla → servicio local → cola).

## Criterio de «listo» para cualquier pantalla
Con red apagada (modo avión REAL y también «Simular sin conexión»):
1. Nunca queda un «Cargando…» o spinner infinito. Si hay datos guardados, se ven con la fecha de «Datos al…». Si no hay, se muestra un mensaje claro («Esta pantalla necesita Internet» o «Todavía no se descargaron…») y los botones que requieren red salen deshabilitados con `necesitaInternet`.
2. Nunca un vacío engañoso («No hay…») cuando en realidad no se pudo consultar.
3. Las acciones que la ingeniera pidió sin conexión se encolan con su UUID (RN11) y muestran su estado.
4. Al volver la red la pantalla abierta se recarga sola y aparece el aviso de reconexión.

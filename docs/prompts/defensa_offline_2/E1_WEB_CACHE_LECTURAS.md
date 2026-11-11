# E1 · Web: lecturas guardadas y precarga (arregla el «Cargando…» eterno en todas las pantallas)

(Pega antes el contenido de `00_BLOQUE_COMUN.md`.)

Objetivo: que toda pantalla web que lee del servidor funcione sin conexión con los últimos datos vistos o precargados, sin depender de si el service worker está activo ni de la simulación.

## Tareas
1. **Caché de lecturas en IndexedDB** (`core/offline/`): un interceptor `lecturas-locales.interceptor.ts` que, con red, guarda la respuesta de cada GET a `API_URL` (clave = método + URL con query + `empresa_id` + `usuario_id` del token; se borran al cerrar sesión). Sin red o con la simulación activa (status 0), el mismo GET se responde desde esa copia y marca `X-Datos-Locales: <fecha>`. No guardar: login/refresh/token, PDFs/blobs, datos de tarjeta, rutas de IA que generan contenido, ni respuestas con `Cache-Control: no-store`. Límite de tamaño con descarte de lo más viejo. Ponerlo ANTES del interceptor de simulación para que la simulación también lea la copia.
2. **Precarga al iniciar sesión** (y cada vez que vuelve la red, si pasaron más de N minutos): por rol, pedir en segundo plano las lecturas de sus pantallas normales para que existan aunque el usuario nunca las haya abierto:
   - Cliente: catálogo y detalle de las prendas vistas, carrito, mis compras (primeras páginas), mis reservas, tarjetas guardadas (solo marca/últimos 4/vencimiento), sucursales.
   - Cajero: ventas recientes, reservas de la sucursal, plazo de devolución, devoluciones recientes.
   - Encargado: reservas de la sucursal, inventario (primera página), lotes en tránsito, conflictos.
   - Proveedor: lotes/abastecimiento y proveedores.
   - Administrador: usuarios, sucursales, productos, reportes/indicadores (último resultado), plan.
3. **Espejo del carrito:** en `carrito-estado.service.ts`, cada vez que llegue un carrito del servidor (`fijar` con datos reales) guardarlo también con `guardarLocal`. Así `checkout.page.ts` sin red encuentra su carrito. Corregir `checkout.page.ts` para que: (a) sin carrito local muestre «Su carrito no está guardado en este dispositivo. Ábralo con conexión una vez.» en vez de «Cargando…»; (b) al volver la red (`effect` sobre `red.online()`) vuelva a ejecutar la carga.
4. **Estado de carga común:** componente/servicio `EstadoPantalla` (cargando | con datos | con datos locales | sin datos y sin red | error) y un `<app-sin-datos>` reutilizable. Úsalo en `carrito.page.ts`, `producto-detalle.page.ts`, `recepciones.page.ts`, `reservas-sucursal.page.ts`, `atencion.page.ts`, `devoluciones.page.ts` (lista de recientes), `proveedores.page.ts`, `productos.page.ts`, `conflictos.page.ts`, `mis-compras.page.ts`: `cargando` debe terminar siempre (también en error) y el vacío solo se muestra si de verdad no hay datos.
5. **Recarga al reconectar:** toda página con `ngOnInit` que carga datos debe suscribirse a `ColaOperacionesService.alRefrescar` (ya existe en algunas) para recargar sola.
6. **SW:** revisa `ngsw-config.json`: `api-consultas` con `freshness` y `timeout 3s` es correcto para modo avión real; confirma que los `index.html` y rutas lazy de cada rol quedan precacheados (`prefetch`) para abrir la app offline sin haber visitado cada ruta. Si falta algo, corrígelo.

## Pruebas (solo las nuevas)
Specs para: interceptor (guarda, responde con status 0, no guarda lo excluido, aísla por usuario y se limpia al cerrar sesión), espejo del carrito, checkout abierto sin red con y sin carrito local, `EstadoPantalla` nunca queda en «cargando» tras un error.

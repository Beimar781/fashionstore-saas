# Prompt Ñ — Navegación del móvil (barra inferior), inicio con catálogo e imágenes, y barra del sistema que tapa opciones

Ejecútalo **antes del Prompt Q** (el Q agrega avisos y contadores en este mismo diseño) y después del O y el S, con todo subido con `git push`. Es un cambio **solo de interfaz del móvil**: el backend no debería cambiar. Lee `CLAUDE.md` y estos archivos, nada más: `movil/lib/main.dart`, `movil/lib/core/ui/tema.dart`, `movil/lib/features/home/presentation/home_screen.dart`, `movil/lib/primer_parcial/catalogo/presentation/catalogo_screen.dart`, `movil/lib/primer_parcial/ia/vestidor/presentation/vestidor_screen.dart` y `movil/lib/features/notificaciones/presentation/push_controller.dart`. Todo lo que me escribas va en español. Código explicable en una defensa: nombres en español, funciones cortas, sin abstracciones innecesarias. No toques claves, variables de Railway ni secretos. **No quites ninguna función existente:** solo cambia dónde está cada cosa.

## Qué pasa hoy (capturas de mi Redmi con el APK)
1. **La barra de botones del sistema (cuadrado, círculo, triángulo) se encima sobre el contenido.** Tapa el final de las listas (el último acceso del inicio, «Modo sin conexión», queda cortado) y, en el **vestidor virtual**, tapa los selectores de talla (L, M, S, XL) y el color. Pasa en cualquier pantalla con algo pegado abajo.
2. **El inicio es una lista larga de tarjetas** (contexto de la sesión, plan, y luego accesos a Catálogo, Mi carrito, Mis compras, Mis reservas, Modo sin conexión). Quiero que se vea como una app de tienda (la referencia es una app de pedidos tipo PedidosYa): arriba a la derecha los botones de **notificaciones** y **carrito**, abajo una **barra de navegación** con las demás opciones, y la pantalla principal es **el catálogo con las fotos de las prendas**.

## 1. Barra del sistema (hazlo primero; aplica a **todas** las pantallas, de todos los roles)
- Revisa cada pantalla del móvil que tenga contenido pegado abajo o listas que lleguen hasta el borde y corrige con los insets del sistema: `SafeArea` (con `top: false` cuando ya hay `AppBar`) o `MediaQuery.viewPaddingOf(context).bottom` sumado al `padding` inferior de los `ListView`/`SingleChildScrollView`, a los `Positioned(bottom: …)` y a los botones fijos. Pantallas a revisar como mínimo: inicio, catálogo, detalle de prenda, carrito, entrega/pago, pedidos, reservas, mi reserva, asistente, modo sin conexión, registrar sin conexión, login, registro, recuperar contraseña, tarjetas guardadas y **vestidor** (`_controles()`, `_guia()` y el contador de FPS).
- En `main.dart` deja el modo de pantalla explícito y coherente: `SystemChrome.setEnabledSystemUIMode(SystemUiMode.edgeToEdge)` con `SystemUiOverlayStyle` de barra de navegación **opaca** (color de fondo de la app, iconos oscuros o claros según contraste) y `systemNavigationBarContrastEnforced: true`, para que funcione igual con navegación por gestos y con tres botones, y en Android 15 (que fuerza pantalla completa).
- En el vestidor, la fila de colores y tallas debe quedar **siempre por encima** de la barra del sistema y de la barra de gestos, y el video no debe quedar debajo de ella.
- Prueba de Flutter: `MediaQuery` con `viewPadding.bottom = 48` para el vestidor (controles), el carrito y la pantalla de entrega, verificando que los controles inferiores quedan por encima de ese margen (`tester.getBottomLeft(...).dy <= alturaTotal - 48`).

## 2. Estructura de navegación del **Cliente** (otros roles: ver el punto 6)
Convierte el inicio del Cliente en un `Scaffold` con **barra inferior** (`NavigationBar` de Material 3, máximo 5 destinos, `IndexedStack` para conservar el estado de cada pestaña y evitar recargas innecesarias):

| Pestaña | Contenido |
|---|---|
| **Inicio** | El catálogo con imágenes (punto 3) |
| **Promociones** | Solo las prendas con promoción vigente (mismo diseño de tarjetas del Inicio, filtradas por `promocion != null`) |
| **Reservas** | La pantalla actual «Mis reservas» (con su acceso a «Mi reserva») |
| **Compras** | La pantalla actual «Mis compras» (historial y comprobantes) |
| **Perfil** | La tarjeta de contexto de hoy (nombre, rol, empresa, sucursal, panel, plan, estado, vence, sucursales permitidas), «Actualizar» (el botón de sincronizar del encabezado de hoy), «Modo sin conexión», «Asistente de compras» (solo si `iaHabilitada`), «Tarjetas guardadas» y «Cerrar sesión» |

- **Arriba a la derecha, en la barra superior de las pestañas** (y solo ahí, no en cada pantalla de detalle): un botón de **notificaciones** (campana) y un botón de **carrito**, cada uno con su **globito con el número** (avisos sin leer en `PushController`; prendas en el carrito del servidor o local). Sin número cuando es cero. El carrito abre `CarritoScreen` y la campana abre una pantalla nueva **«Avisos»** con la lista que hoy se pinta como tarjetas rosadas en el inicio (con «Marcar como leído» por aviso y «Marcar todos»). **Quita esas tarjetas de avisos del inicio** (ahora viven en «Avisos»), pero deja visibles en el Inicio, arriba, solo los avisos críticos: «Sin conexión», suscripción no vigente y operaciones pendientes o en conflicto, como hoy.
- El **asistente de compras** (plan Profesional) también aparece como un botón flotante pequeño (`FloatingActionButton.small` con icono `auto_awesome`) **solo en la pestaña Inicio** y solo si el plan lo incluye; en un plan sin IA no se ve en ningún lado.
- Titulo de la barra superior: nombre de la empresa (`Moda Urbana S.R.L.`), como hoy.
- Las pantallas que se abren encima (detalle de prenda, carrito, avisos, pago, comprobante, vestidor, asistente) siguen siendo pantallas normales con flecha de regreso.
- Si la suscripción está restringida (`s.restringido`), el Cliente solo ve la pestaña **Perfil** (su plan), igual que hoy: no muestres la barra inferior con pestañas que no puede usar.

## 3. Inicio = catálogo con imágenes (como la app de referencia)
De arriba hacia abajo, en la pestaña Inicio:
1. **Encabezado de color** (vino/tinta del tema, con la esquina inferior redondeada) con el **selector de sucursal** («Sucursal Centro ▾», abre una hoja inferior con la lista de `/catalogo/sucursales`; se guarda la última elegida en el dispositivo) y debajo el **campo de búsqueda** redondeado («Buscar prendas»). Buscar vuelve a pedir el catálogo con `q`.
2. **Carrusel de promociones** (`PageView`, altura fija, puntos indicadores abajo, avance automático cada 5 s que se detiene al tocar): una tarjeta por prenda con promoción (imagen grande, nombre de la promoción, nombre y precio con el precio original tachado). Si no hay promociones, un banner fijo con el nombre de la empresa. Tocar abre el detalle de la prenda.
3. **Fila horizontal de categorías** (las que traen las prendas cargadas; una tarjeta redondeada con la imagen de la primera prenda de esa categoría o un icono `checkroom` si no tiene, y su nombre debajo). Tocar filtra la rejilla; hay una opción «Todas». Se resalta la elegida.
4. **Rejilla de 2 columnas de prendas** con tarjeta: imagen (relación 3:4, bordes redondeados), nombre (máximo 2 líneas), categoría, **precio final** y, si hay promoción, el precio original tachado y una etiqueta con el nombre de la promoción en una esquina de la imagen; las tallas en texto pequeño; una etiqueta «Agotado» si `disponible == false`. Tocar abre el detalle actual de la prenda (que ya tiene el vestidor, el carrito y «Agregar a mi reserva»).
5. **Paginación:** pide `pagina=1` con `tamano=20` y carga la siguiente página al llegar al final (`pagina`, `tamano` ya existen en `GET /catalogo/buscar`; el backend responde `total`). Jala para refrescar (`RefreshIndicator`).
6. **Estados:** cargando (rejilla de tarjetas grises), vacío («No se encontraron prendas.»), error («No se pudo cargar el catálogo. Intente de nuevo.» con botón «Reintentar»).

### Imágenes
- La API devuelve en cada prenda `imagen` como ruta relativa (`/media/...`). La URL completa es el **origen del servidor** (el valor de `API_URL` **sin** el `/api` del final) más esa ruta: verifícalo con `ApiConfig.baseUrl` y crea **una sola función** (por ejemplo `urlImagen(String ruta)` en `core/network`) que use también el vestidor, para no tener dos formas. Si `imagen` es nula o falla la descarga, muestra un marcador de posición (icono `checkroom` sobre un fondo suave), nunca una pantalla roja ni un error.
- Regla 13 (librerías): agrega `cached_network_image` (y `flutter_cache_manager` si hace falta) a `movil/pubspec.yaml`, comprueba con `flutter pub get` limpio y con `flutter build apk --release --dart-define=API_URL=https://fashionstore-saas-production.up.railway.app/api`. Con esto las imágenes ya vistas quedan en el disco del teléfono y se ven **sin conexión**.
- **Sin conexión:** el Inicio usa el catálogo descargado en SQLite (como hoy el «Modo sin conexión») con la misma rejilla, con una franja arriba «Sin conexión · Datos al 31/10 00:36» (fecha de la última descarga). «Descargar catálogo» (en Perfil → Modo sin conexión) debe además **precargar las imágenes principales** de las prendas con el administrador de caché, para que se vean sin red aunque no se hayan visto antes. Si el Prompt Q todavía no se ejecutó, esto queda hecho aquí y el Q solo lo verifica.
- Si en producción las imágenes no cargan (por ejemplo `404` en `/media/...` porque el disco de Railway no conserva las imágenes cargadas por el sembrado), **no lo escondas**: dime qué respondió el servidor para una prenda de ejemplo (`curl -I` a `https://fashionstore-saas-production.up.railway.app/media/...`) y propón cómo resolverlo (por ejemplo regenerar las imágenes de la demostración al arrancar en `arranque.py`). No cambies nada de infraestructura sin decírmelo.

## 4. Detalle de la prenda y vestidor
- Revisa el detalle de la prenda (`catalogo_screen.dart`/pantalla de opciones) con el mismo cuidado de bordes del punto 1 y muestra arriba la **galería de imágenes** (`imagenes` del detalle, con selector de color que cambia la imagen) si hoy no se muestra; si ya se muestra, solo conserva y arregla los bordes.
- El botón «Probar en el vestidor», «Agregar al carrito» y «Agregar a mi reserva» deben quedar fijos abajo en una barra inferior del detalle, **por encima** de la barra del sistema.

## 5. Tema y estilo
- Mantén la paleta del tema (`vino`, `tinta`, `fondo`). Texto en español, iconos de Material, bordes redondeados de 12–16 px, sombras suaves, `NavigationBar` con indicador del color vino. Sin dependencias de diseño nuevas aparte de las imágenes en caché. Las tarjetas del Cliente deben verse bien en un teléfono de 360 dp de ancho.
- Accesibilidad mínima: `tooltip`/`semanticsLabel` en los botones de campana y carrito, zonas táctiles de al menos 48 dp.

## 6. Otros roles (personal de tienda, administradores, etc.)
No los rediseñes: conservan el inicio actual (lista de accesos, «Modo sin conexión» para el personal de tienda) con el arreglo de bordes del punto 1. Si un administrador entra al móvil, su pantalla actual sigue igual.

## 7. Pruebas (solo de lo que tocas)
Pruebas de Flutter con `MediaQuery`/dobles en memoria, sin red real:
- La barra inferior del Cliente muestra 5 pestañas, las conserva al cambiar (estado) y, con suscripción restringida, solo muestra Perfil.
- La campana y el carrito muestran el número correcto y desaparece el número en cero; la campana abre «Avisos» y «Marcar como leído» actualiza el número.
- El Inicio dibuja la rejilla con el catálogo de un doble del repositorio (imagen, nombre, precio final, precio tachado y etiqueta de promoción), con una imagen nula (marcador) y con error de red (mensaje y «Reintentar»).
- Filtrar por categoría y buscar por texto llaman al repositorio con los parámetros correctos; la paginación pide la página 2 al llegar al final.
- El asistente solo aparece con `iaHabilitada`.
- Los márgenes de la barra del sistema del punto 1.

## 8. Documentación (regla 11)
Actualiza `docs/PRUEBAS_SISTEMA.md` (casos manuales del móvil: barra inferior, campana y carrito con número, Inicio con imágenes, filtros por categoría, Promociones, vestidor con la barra de gestos, y sin conexión con imágenes ya vistas), `docs/MENSAJES_PENDIENTES_WORD.md` (mensajes nuevos con su código: «No se encontraron prendas.», «No se pudo cargar el catálogo. Intente de nuevo.» y la franja «Sin conexión · Datos al …»; y la decisión «el móvil del Cliente se organiza en barra inferior (Inicio, Promociones, Reservas, Compras, Perfil) con campana y carrito arriba a la derecha»), y `docs/TRAZABILIDAD.md` si agregas pruebas.

## Cierre
**Ahorro de tokens (importante):** no corras toda la suite de pruebas en este prompt y no releas todo `docs/`. Corre solo `cd movil && flutter analyze` y `flutter test` con los archivos de prueba de lo que cambiaste, y `flutter build apk --release --dart-define=API_URL=https://fashionstore-saas-production.up.railway.app/api` una sola vez al final (por la librería nueva). Si todo pasa: **un commit por punto** (1, 2, 3, 4, 8), con mi identidad de git, mensaje corto en español, sin líneas de coautoría, y `git push`. Si algo falla: no hagas commit y explícame qué pasó.

Dame un resumen corto en español: qué cambió por punto, dónde quedó cada opción (qué pestaña), cómo resolviste los bordes del vestidor, qué respondió el servidor con las imágenes de producción, y qué debo probar a mano en el celular (con navegación por gestos y con tres botones). Cuando termines avísame para que lance el workflow del APK desde el chat.

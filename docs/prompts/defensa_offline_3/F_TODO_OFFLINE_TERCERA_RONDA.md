# Tercera ronda — corregir TODO lo sin conexión en un solo pase (defensa del jueves 12/11)

Pega este prompt completo en Claude Code. Está en español porque así trabajamos.

## Contexto
Probamos en Railway (web, con «Simular sin conexión») a los 5 actores de EMP-B después de la segunda ronda (main d960fee) y revisamos el código del móvil. Lo sin conexión ya funciona en muchas pantallas, pero quedan fallas. Hay un **patrón común**: una pantalla sin datos precargados muestra el error rojo «Sin conexión con el servidor.» y además «No hay…» (vacío engañoso), o «todavía no hay datos guardados» donde debería haber datos, o deja botones de escritura activos sin avisar. Corrige las fallas de abajo y **busca y corrige las mismas fallas en cualquier otra pantalla parecida que no listamos** (no adivines: verifica en el código).

## Reglas
- Lee `CLAUDE.md` y respétalo. Se puede tocar `main`. Cada funcionalidad sin conexión debe verse en la **pantalla normal** de su actor (web y móvil), no en una sección aparte.
- Nunca ver ni escribir contraseñas ni claves. No cambies `user.name` ni `user.email` de git.
- Reutiliza lo ya hecho: `vacio.component.ts` (EstadoPantalla), `lecturas-locales.interceptor/service`, `precarga.service.ts`, `carrito-estado.service.ts`, `necesitaInternet`, y en móvil `lecturas_locales.dart`, `carrito_sin_conexion.dart`, `detalle_local.dart`. No inventes otro patrón.
- Pruebas: specs/tests de lo que cambies durante el trabajo; **al final corre la suite completa** (backend, frontend, `flutter test`, `scripts/auditar_offline.py`) y arregla lo que rompas.
- Al terminar: `git add`, `git commit` y `git push` con la identidad del usuario, mensajes cortos en español, **sin líneas de coautoría**. Si algo falla, no hagas commit y explica en español.
- Agrega a `docs/MENSAJES_PENDIENTES_WORD.md` los mensajes y reglas nuevos. No cambies el Word. Actualiza `docs/AUDITORIA_OFFLINE.md`.

## Criterio de «listo» para cualquier pantalla (web y móvil)
Con red apagada (modo avión REAL y «Simular sin conexión»):
1. Nunca «Cargando…»/spinner infinito. Con datos guardados: se ven con «Datos al…». Sin datos: mensaje claro («Esta pantalla necesita Internet» o «Todavía no se descargó…»), sin el error rojo duplicado.
2. Nunca «No hay…» cuando en realidad no se pudo consultar.
3. Botones de escritura que no se pueden encolar salen deshabilitados con «Esta función necesita Internet». Las acciones que la ingeniera pidió offline se encolan con UUID (RN11) y muestran su estado.
4. Al volver la red la pantalla abierta se recarga sola.

## A. Web — Cliente
1. **Ficha de prenda** (`features/catalogo/prenda.page.ts` y `producto-detalle.page.ts`): una prenda no vista antes dice «todavía no hay datos guardados». Debe armarse con el catálogo ya descargado (igual que el móvil con `detalle_local.dart`): tallas, colores, precio, stock y fotos de la copia local; si la prenda no está en la copia, mensaje claro.
2. **IVA sin conexión:** «Incluye IVA: Bs 0,00» (con red Bs 34,51). Calcúlalo en el cliente con la misma fórmula del servidor (IVA incluido en el precio, la tasa de la empresa descargada) en el checkout y en Mi carrito. Que coincida con el servidor al céntimo.

## B. Web — Cajero y Caja (también la usa el Encargado)
1. Texto duplicado «Cobrar la venta **Venta Venta local**»: corrige el nombre/etiqueta.
2. «IVA incluido: Bs 0,00» en la venta local y en el comprobante provisional `LOC-…`: mismo cálculo local de A.2.
3. Tras «Deshacer» una venta local, el panel verde «✓ Venta cobrada … LOC-…» sigue visible: debe desaparecer y la pantalla volver al estado inicial.

## C. Web — Encargado
1. **Conflictos de sincronización:** sin conexión dice «todavía no hay datos guardados». Agrégalo a la precarga del Encargado (y del Administrador, que sí lo tiene precargado; deben usar el mismo mecanismo). Resolver (Reintentar/Descartar) queda deshabilitado con «Esta función necesita Internet».
2. **Inventario de la sucursal:** el aviso dice «se muestran las existencias de la copia descargada» pero las tarjetas salen en 0 y el listado vacío. O muestra de verdad la copia descargada, o dice «necesita Internet»; nunca el aviso mentiroso con ceros.
3. **Ventas de la sucursal:** error rojo + «No hay ventas con esos filtros»: precárgala (ventas recientes) o muestra «necesita Internet» sin el vacío engañoso.
4. **Movimientos:** «todavía no hay datos guardados» → mensaje claro de «necesita Internet».

## D. Web — Proveedor
1. **Nuevo aviso de remisión:** el buscador de producto («Polo» + Buscar) no devuelve nada ni mensaje. Descarga en la precarga del Proveedor el catálogo mínimo de sus productos/colecciones para buscar sin conexión, o muestra «Esta función necesita Internet» y deshabilita Buscar.
2. «Ver» y «Cancelar» del aviso siguen activos sin conexión: «Ver» debe usar los datos precargados; «Cancelar» (escritura) deshabilitado con «necesita Internet» (o encolado con UUID si el enunciado lo permite; en caso de duda, deshabilitado).

## E. Web — Administrador (rutas `/empresa/...`)
1. **Abastecimiento** (avisos y propuestas): «todavía no hay datos guardados». Agrégalo a la precarga del Administrador; «Nuevo aviso de remisión» deshabilitado sin conexión.
2. **Devoluciones y cambios**, **Bitácora**: error rojo + «No hay…» engañoso. Precarga los datos recientes («Datos al…») o muestra «necesita Internet» sin el vacío. «Guardar plazo» deshabilitado sin conexión.
3. **Indicadores:** solo error rojo. Guarda la última consulta (periodo por defecto «Últimos 30 días», todas las sucursales) y muéstrala con «Datos al…»; si no existe, «necesita Internet».
4. **Reportes:** error rojo; botones Excel/PDF/CSV y «Consultar» deshabilitados con «necesita Internet» (es CU-23, solo en línea).
5. **Temporadas y colecciones:** «0 temporadas / Aún no hay temporadas»: verifica si es vacío real o engañoso (compara con red) y corrígelo si es engañoso (precarga o «necesita Internet»).
6. **Botones de escritura** (Nuevo usuario, Nueva sucursal, Nuevo producto, Nueva categoría, Editar, Desactivar, Eliminar, etc.) en todas las pantallas del Administrador: deshabilitados sin conexión con «Esta función necesita Internet». Hazlo con una directiva/clase común (no pantalla por pantalla a mano) y revisa todas las pantallas `/empresa/**`.
7. **Inventario global:** verifica que «Reservadas 0 / Agotadas 0» sin conexión coincidan con los datos con red.

## F. Catálogo local desactualizado (web y móvil)
En la web el «Descargado el 11/11/2026 00:33» no se renovó tras iniciar sesión casi 4 h después: la precarga no renueva si ya existe. Renueva el catálogo/existencias en el login y al reconectar si tiene más de 15 minutos (el móvil ya lo hace en `actualizarTrasReconectar`; la web debe hacer lo mismo y mostrar la fecha). Riesgo que evitamos: vender sin conexión con stock viejo.

## G. Móvil (auditoría del código, mismas fallas)
Hay pantallas móviles solo para Cliente, Cajero y Encargado; Administrador y Proveedor no tienen y ya muestran «Las funciones de su rol se usan desde la web» / «Esta función necesita Internet» (verifica que ese texto salga también sin red).
1. **IVA en 0:** `features/offline/data/carrito_sin_conexion.dart` fija `'iva_incluido': '0.00'`; calcula el IVA como en A.2 (la pantalla `carrito_screen.dart` lo muestra). Revisa también `registrar_offline_screen.dart`, `caja_screen.dart` y `comprobante_provisional.dart`.
2. Recorre TODAS las pantallas móviles con red apagada y revisa el patrón: `reservas_screen`, `mi_reserva_screen`, `pedidos_screen`, `tarjetas_screen` (sin red solo dice «necesitan Internet»; si hay tarjetas guardadas en la copia local de `actualizarTarjetas`, muéstralas), `entrega_screen`, `tareas_sucursal_screen` (Devoluciones, Recepción, Ajuste, Reservas), `conflictos_screen`, `resumen_turno_screen`, `registro_sync_screen`, `_AvisosScreen`, `asistente_screen` y `vestidor_screen`. Cada una debe cumplir el criterio de «listo».
3. Que el chip de conexión siga al servidor (`ApiException.sinConexion`) en TODAS las rutas, también las que usan `ApiClient` directamente.
4. Pantallas que dicen «No hay…» (`tareas_sucursal_screen` líneas ~159 y ~359, `home_screen` avisos): confirma que no aparecen cuando en realidad no se pudo cargar.
5. Agrega tests de widget/unit para: IVA local = IVA del servidor, ficha desde el catálogo descargado, chip de conexión, y una prueba por pantalla de que no hay spinner infinito sin red.

## H. Datos de demostración y cierre
1. Ejecuta (o deja listo y documentado) `scripts/preparar_demo.py` para Railway: stock del cajero/encargado de EMP-B en Camisa Oxford y Polo Básico (hoy 0 en la sucursal del cajero), una tarjeta guardada para el Cliente Demo de EMP-B, `--empresa-c` con catálogo. **Antes de escribir en Railway, dime qué va a cambiar y espera mi sí.**
2. Corre `python scripts/humo_produccion.py <url del frontend y backend de Railway>` y dime el resultado.
3. Actualiza `scripts/auditar_offline.py` para que detecte el patrón «error + No hay…» y las escrituras activas sin conexión en las pantallas `/empresa/**`, y córrelo.
4. Suite completa y, si todo pasa, dispara el workflow «Compilar APK» y dime el enlace de descarga. No cambies versiones ni claves.
5. Resumen final en español: qué quedó por actor y plataforma, archivos principales, cómo fluye (pantalla → servicio local → cola/UUID), qué NO pudiste verificar y qué debo probar yo a mano (prueba manual al final: venta offline del cajero, carrito y ficha del cliente, conflictos del encargado, y sincronización real).

# Cierre final — pago sin conexión, pantallas de actores y móvil (defensa del jueves 12/11)

Pega este prompt completo en Claude Code. Está en español porque así trabajamos.

## Reglas
Lee `CLAUDE.md` y respétalo. Se puede tocar `main`. Nunca ver ni escribir contraseñas ni claves; no cambies `user.name` ni `user.email` de git. Reutiliza lo que ya existe (`necesita-internet.directive.ts`, `vacio.component.ts`, `precarga.service.ts`, `lecturas-locales.*`, y en móvil `lecturas_locales.dart`, `offline_repository.dart`, `tareas_sucursal_screen.dart`). Pruebas de lo que cambies y **al final la suite completa** (backend, frontend, `flutter analyze`, `flutter test`, `scripts/auditar_offline.py`). Commits con mi identidad, mensajes cortos en español, **sin líneas de coautoría**, y haz `git push` (verifica con `git log origin/main` que quedó). Actualiza `docs/MENSAJES_PENDIENTES_WORD.md`, `docs/AUDITORIA_OFFLINE.md` y `docs/PRUEBAS_SISTEMA.md`. No cambies el Word.

## 0. Verifica primero (importante)
El prompt anterior G (`docs/prompts/defensa_offline_3/G_PAGO_STRIPE_Y_FICHA.md`) pedía corregir el pago con tarjeta nueva (`pago-tarjeta.component.ts`: el contenedor del Element de Stripe se destruía al pasar a «procesando») y la ficha con id inexistente. **En `origin/main` (f4f71da) ese cambio no aparece** (el archivo sigue igual). Revisa si se hizo y no se subió, y súbelo; si no se hizo, hazlo ahora: mantener montado el Element durante «procesando», distinguir un error de Stripe.js («Revise los datos de la tarjeta») de un rechazo bancario («Pago rechazado»), y «Prenda no encontrada» con enlace al catálogo en la ficha por id inexistente (hoy: 3 avisos y «Cargando…» infinito).

## 1. Pago sin conexión del Cliente (web y móvil)
Verificado en Railway: compra offline con tarjeta guardada → «Pagar con Visa 4242 al volver la conexión» + autorización → al reconectar quedó PED-… pagado con comprobante. Falta corregir:
1. **Copia local de tarjetas guardadas** (web `checkout.page.ts`, clave `tarjetas_cliente_*`; móvil `OfflineRepository.guardarTarjetas`): hoy solo se escribe al abrir el checkout/entrega con red y al descargar el catálogo. Debe actualizarse **al guardar una tarjeta** (pago con «Guardar esta tarjeta»), **al eliminarla** (`olvidar` en web; `_eliminar` en `entrega_screen.dart` y `tarjetas_screen.dart` en móvil), al iniciar sesión, en la precarga y al reconectar. Crea un solo servicio/método de «tarjetas guardadas» en cada plataforma. Prueba: guardar una tarjeta y apagar la red SIN reabrir el checkout → se ofrece; eliminar una tarjeta → ya no se ofrece sin conexión.
2. **Estilo web:** en el checkout sin conexión, las opciones «Dejar por pagar» y «Pagar con Visa terminada en…» salen con el círculo del radio separado del texto; arréglalo (grupo de radios con `label.check`).
3. Tras «Guardar compra para sincronizar» (web) sobra el mensaje «Esta pantalla necesita Internet: todavía no hay datos guardados de ella» debajo del aviso verde; debe verse solo el aviso de compra guardada con «Ir a Mis compras».
4. **NIT/CI:** la regla es mínimo 3 caracteres (backend). Mensaje: «Ingrese su NIT o CI (al menos 3 caracteres; consumidor final: su CI)», y que el error desaparezca al corregir el campo (web y móvil, `datos_entrega.dart`).
5. **Estado de la compra pendiente en lenguaje claro** (web Mis compras y móvil `pedidos_screen.dart` l.~290 y `reservas_screen.dart` l.~235): en vez de «Compra local c20069dd · REGISTRADA_LOCAL» o «Pendiente de sincronizar · ${estado}» mostrar «Pendiente de enviar · se cobrará a la Visa 4242 al reconectar» (o «Pendiente de enviar» si es por pagar), con Deshacer y Línea de tiempo visibles.
6. **Resultado del cobro al reconectar** (web y móvil): aviso local con el resultado de cada compra («Su compra PED-… fue pagada con Visa 4242», «Su compra quedó por pagar: el banco rechazó la tarjeta», «No había stock: no se cobró nada») y enlace al comprobante. Si la tarjeta venció entre el registro y la sincronización, al registrar mostrar «vence antes del…» y ofrecer «Dejar por pagar».
7. **«Modo sin conexión» (web):** el aviso «se descargó hace más de un día o no hay conexión para renovarla» sale aunque la descarga sea de hoy; distingue «sin conexión para renovar» de «tiene más de un día» (el móvil ya lo hace bien).

## 2. Encargado (web y móvil)
1. **Inventario de la sucursal sin conexión:** «Vendidas 0» y «Próximas a ingresar 0» (con red: 5 y 36) engañan: mostrar «—» o «necesita Internet» en esas tarjetas.
2. **Devoluciones sin conexión:** la lista de ventas descargadas queda vacía aunque hay ventas del día en la sucursal (compras digitales CMP-002-…). El backend (`cu37_catalogo_offline/service.py::_para_el_personal`) ya incluye pedidos PAGADO de la sucursal dentro del plazo, hasta 60. Averigua por qué no aparecen (¿descarga anterior a esas compras?, ¿`DevolucionService.venta` las excluye?, ¿web las filtra?) con una prueba en backend (compra digital + `GET /offline/catalogo` del Encargado) y corrígelo; si una compra digital no es devolvible sin conexión, dilo en pantalla («solo ventas pagadas en esta sucursal dentro del plazo»).
3. En móvil (`tareas_sucursal_screen.dart` ~l.159 y ~l.359) el texto «No hay ventas descargadas. Descargue el catálogo con conexión» sale también cuando la descarga existe y simplemente no hay ventas/reservas; distingue «no hay copia» de «no hay ventas/reservas en el plazo» (y de «no se pudo consultar»).

## 3. Proveedor (web)
1. La propuesta guardada sin conexión **no se ve en la lista**: mostrarla como «Pendiente de enviar» (como las compras locales).
2. Los botones con `necesitaInternet` («Nuevo aviso de remisión», «Cancelar») no se ven apagados (opacity 1). Define `.sin-internet { opacity: .55; cursor: not-allowed }` globalmente (en el Administrador los botones «Nuevo…» sí se ven atenuados: unifica) y asegúrate de que `aria-disabled` se aplique también a botones dibujados después (filas, modales).

## 4. Administrador (web)
1. **Bitácora:** sin conexión sale el aviso de Internet **y** «No hay registros con esos filtros»; mostrar solo el aviso (o los últimos registros precargados con «Datos al…»).
2. **Reportes:** atenuar Excel/PDF/CSV y «Consultar» sin conexión y explicar las pestañas vacías (Ventas/Reservas/Pagos/Inventario) con «Los reportes necesitan Internet».
3. **Botones de fila** (Editar, Desactivar, Eliminar, Reintentar, Descartar, Ver…): ya están protegidos al tocarlos, pero varios no se ven atenuados; aplica la misma clase.
4. **Indicadores:** muestra «Datos al…» y revisa «sin comparación vs. período anterior (Bs N/D)».
5. Recorre **Analítica** y el **Asistente de IA** sin conexión: deben decir «necesita Internet», no un error.
6. Borra del Administrador la propuesta de prueba «Prueba sin conexion» (Hilos Andinos, Bs 100) que quedó en Railway: dime cómo (si no hay opción en pantalla, un script en `scripts/`) y espera mi sí antes de tocar Railway.

## 5. Cajero (web)
El panel derecho de la Caja aún dice «Venta **Venta local**» tras cobrar (se corrigió el título de la izquierda); arregla la etiqueta del resumen. Comprueba que Devoluciones del Cajero sin conexión use la misma corrección del punto 2.2.

## 6. Móvil: auditoría final del APK (Cliente, Cajero, Encargado)
El último APK compilado es de `d960fee` (segunda ronda); le faltan F, G y este prompt. Antes de recompilar:
1. Recorre cada pantalla móvil de los tres roles con red apagada (modo avión real y «Simular sin conexión») y cumple el criterio: sin spinner infinito, sin «No hay…» cuando no se pudo consultar, escrituras que no se pueden encolar deshabilitadas con «Esta función necesita Internet», aviso «Datos al…». Incluye `catalogo_screen` (ficha, ficha con id inexistente), `carrito_screen`, `entrega_screen`, `tarjetas_screen`, `pedidos_screen`, `reservas_screen`, `mi_reserva_screen`, `caja_screen`, `caja_en_linea_screen`, `registrar_offline_screen`, `tareas_sucursal_screen` (Devoluciones, Recepción, Ajuste, Reservas), `conflictos_screen`, `resumen_turno_screen`, `registro_sync_screen`, `_AvisosScreen`, `asistente_screen`, `vestidor_screen`, `home_screen` (incluido el texto para roles sin pantalla móvil: Administrador y Proveedor).
2. Aplica en móvil los puntos 1.1, 1.4, 1.5, 1.6, 2.3 y los textos de este prompt.
3. Tests de widget/unit nuevos para: copia de tarjetas al guardar/eliminar, estado legible de la compra pendiente, «no hay copia» vs «no hay ventas», y los textos de NIT.
4. Suite completa, `git push`, y dispara el workflow **«Compilar APK»** (`gh workflow run`) desde el commit final; dame el enlace de descarga y el hash del commit con el que se compiló. No cambies versiones ni claves.

## 7. Cierre
1. Corre `python scripts/humo_produccion.py <url>` contra Railway cuando termine el despliegue, y `scripts/auditar_offline.py`.
2. `scripts/preparar_demo.py`: dime qué cambiaría en Railway (stock de Camisa Oxford y Polo Básico para el Cajero/Encargado de EMP-B, tarjeta guardada del Cliente Demo, catálogo de EMP-C) y **espera mi sí**.
3. Resumen final en español: qué quedó por actor y plataforma, archivos principales, cómo fluye, qué NO pudiste verificar, y una lista corta de lo que debo probar yo a mano en el teléfono (venta offline del Cajero, carrito/ficha/pago con tarjeta guardada del Cliente, conflictos del Encargado, sincronización real).

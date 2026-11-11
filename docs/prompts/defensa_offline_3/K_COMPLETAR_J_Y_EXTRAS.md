# Prompt K — Completar TODO el prompt J (puntos pendientes) + extras funcionales

Contexto: ejecutaste el prompt J en el commit 1028a7e, pero quedaron puntos sin hacer o a medias. Defensa mañana temprano. **Todo debe quedar funcional, probado y sin romper lo existente.** Lee de nuevo `docs/prompts/defensa_offline_3/J_PEDIDOS_POR_PAGAR_MOVIL.md` completo y cumple CADA punto; abajo está lo que falta. Al final entrega una tabla «punto → hecho / cómo se probó».

## A. Obligatorios (pendientes de J)

1. **Copia local ligada al usuario (J-5, a medias).** Guarda en la copia local el `usuario_id`, `rol` y `empresa_id` de quien la descargó. Al iniciar sesión: si no coincide con el usuario actual, bórrala y descarga de nuevo antes de mostrar pantallas. Al cerrar sesión: borra catálogo, ventas recientes, avisos en caché, tarjetas y carrito local de ese usuario (las operaciones pendientes SÍ se conservan, cada una con su dueño; otro usuario no las ve ni las envía). Prueba: Cliente → Cajero → Encargado en el mismo teléfono sin ver datos del anterior.
2. **Aviso «Sincronización completa…» (J-9).** (a) Se borra al cerrar sesión y nunca aparece en Login; (b) un solo SnackBar a la vez; (c) conteos veraces de ESA sincronización: confirmadas / en conflicto / rechazadas (hoy decía «0 en conflicto» habiendo uno); si hay conflicto el texto lo dice y «Ver detalle» abre Conflictos; (d) no se vuelve a mostrar al navegar entre pantallas.
3. **Avisos como botón de campana (J-10).** Cajero, Encargado y Cliente: el inicio abre con accesos primero; los avisos van en una campana de la barra superior con contador de no leídos que abre «Avisos» (marcar leído al abrir). Funciona sin conexión con los avisos en caché.
4. **Cliente (J-11 a J-15):** Mis compras con banda «Sin conexión» fija que no tapa la lista; compras pendientes de enviar visibles con estado legible y «Deshacer»; tarjeta guardada offline: limpiar mensaje rojo al marcar autorización y vaciar carrito local tras guardar; ocultar UUID/intentos sin red; en conflicto ofrecer «Elegir otra talla o sucursal» y «Cancelar compra»; tarjetas con indicador «Disponible sin conexión».
5. **Cajero (J-16 a J-19):** línea «IVA incluido: Bs X» (total×13/113) al armar la venta; búsqueda con resultados visibles sobre el teclado y «Sin resultados»; botón «Registrar venta» fijo abajo, nunca tapado.
6. **Encargado (J-20 a J-22):** lista vacía muestra «Copia local de <hora>» + botón «Actualizar ahora» (con red); estilo de botones en Reservas con motivo del deshabilitado; contador de conflictos pendientes en el acceso «Conflictos».
7. **Snackbars que tapan botones (J-6):** margen inferior / `behavior: floating` con `margin` por encima de los botones en TODAS las pantallas con botón inferior.
8. **Verifica el efecto que reportaste:** ventas de Caja sin pagar con cliente asociado salen como «Por pagar» en su historial; asegúrate de que el cliente pueda pagarlas con tarjeta y que al pagar el comprobante y el stock sean correctos (sin descontar stock dos veces). Prueba de backend.

## B. Extras (haz todos los que sean seguros y funcionales)

9. **Pull-to-refresh** en Mis compras, Reservas, Tareas, Conflictos y Avisos (con red recarga; sin red muestra «Sin conexión, mostrando copia local»).
10. **Indicador de sincronización en la barra superior** de las 3 pantallas principales: icono con contador de operaciones pendientes (toca → pantalla Operaciones); sin red icono «nube tachada».
11. **Reintento automático** de operaciones ENVIADA/pendientes al recuperar red (con backoff), sin duplicar (usa `operacion_id`, RN12).
12. **Diagnóstico** (ya existe): añade usuario, rol, empresa, hora de la copia local, versión de la app y cantidad de pendientes/conflictos; botón «Copiar» al portapapeles.
13. **Confirmaciones**: diálogo antes de «Deshacer» y de «Cancelar compra», con texto claro.
14. **Estados vacíos** con ilustración/texto útil en todas las listas (Mis compras, Reservas, Tareas, Conflictos, Avisos, Operaciones).
15. **Accesibilidad básica**: tooltips y `Semantics` en iconos (campana, nube), tamaños táctiles ≥ 44 px.
16. **Web**: misma regla de «Por pagar» y del aviso único en Mis compras; si prompt I no se ejecutó, ejecútalo también (`docs/prompts/defensa_offline_3/I_PULIDO_FINAL_WEB.md`).

## C. Pruebas (obligatorias)
- Backend: pytest completo verde + pruebas nuevas del punto 8.
- Móvil: `flutter analyze` sin avisos y `flutter test` verde con pruebas nuevas para: limpieza al cambiar de usuario (1), aviso de sync veraz y borrado al logout (2), campana con contador (3), IVA en Caja (5), reintento al volver la red (B11).
- Web: `npm run build` y tests verdes.
- No toques credenciales ni datos reales. Un commit por tema, en español, a mi nombre, **sin co-autor**. Sube a `correccion-pago` y `main`.
- Al terminar, dame: lista de commits, tabla punto→estado, y avísame para compilar la APK nueva (no la compiles tú; yo la lanzo desde Actions).

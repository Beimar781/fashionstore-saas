# Prompt M — Aviso pegado, contador de conflictos y mejoras de pulido del móvil (APK 6d8b6d0)

Resultado de probar la APK real (Cliente, Cajero y Encargado, EMP-A, 11/11 21:30). Casi todo de J y K funciona; esto es lo que falló y las mejoras que faltan. **Todo debe quedar funcional, con pruebas, sin romper lo existente. Haz TODOS los puntos.**

## A. Fallas confirmadas (obligatorias)

1. **El aviso «Sincronización completa: … · Ver detalle» no se cierra** (más de 60 s, sigue al cambiar de pestaña). Causa probable: en Flutter un `SnackBar` con `action` es persistente y se ignora `duration`. En `lib/main.dart` (≈ líneas 64–74) agrega `persist: false` a los dos SnackBar globales (duración 5 s). Revisa con `grep SnackBarAction` todos los SnackBar con `action:` en `movil/lib` y ponles `persist: false`. «Ver detalle» debe seguir funcionando durante esos 5 s. Conserva `clearSnackBars()` al cerrar sesión. Prueba de widget: visible a los 3 s, desaparece a los 6 s.
2. **El acceso «Conflictos de sincronización» del inicio (Encargado) no muestra contador** aunque la pantalla lista 2 conflictos (J-22). Muestra una insignia con la cantidad de conflictos pendientes de la sucursal/empresa (los del servidor cuando hay red + los locales EN_CONFLICTO); se actualiza al abrir el inicio, tras sincronizar y al volver de Conflictos; si es 0, sin insignia. Mismo contador (solo los propios) para Cajero y Cliente donde aplique. Prueba de widget.
3. **Reservas (Tareas de la sucursal)**: el botón «No encontrada» (tareas_sucursal_screen.dart ≈ línea 389) es un `TextButton` sin forma de botón y se lee como una etiqueta de estado. Conviértelo en un botón claro «Marcar no encontrada» (outlined, icono, color de advertencia), con diálogo de confirmación y, tras marcarlo, que el ítem muestre un estado «No encontrada» distinto del botón.

## B. Mejoras detectadas en la prueba (obligatorias)
4. **Caja (Cajero):** con la lista de resultados abierta, las prendas agregadas, el Total y el «IVA incluido» quedan muy abajo. Muestra la venta en curso (líneas + total + IVA) en un panel fijo arriba del botón «Registrar venta» (colapsable) y deja los resultados en una zona desplazable; al agregar una prenda, cierra el teclado y limpia el buscador. Verifica y deja visible el mensaje «Sin resultados».
5. **Teclado:** al tocar fuera de un campo o al agregar una prenda, que el teclado se cierre (`FocusScope.unfocus`) en Caja, Carrito, Entrega y Devoluciones; la tecla «Atrás» no debe sacar de Caja con una venta en curso sin avisar (diálogo «¿Descartar la venta en curso?»).
6. **Avisos (campana):** en la pantalla «Avisos» agrega «Marcar todos como leídos» y agrupa por «Hoy / Anteriores»; cada aviso de pedido por pagar debe abrir directamente «Mis compras» en ese pedido.
7. **Mis compras (Cliente):** los pedidos «Por pagar» arriba y resaltados con insignia ámbar; mostrar el plazo para pagar si existe; el diálogo del pedido ya tiene «Pagar con tarjeta» — conserva ese botón y agrega «Cancelar pedido» con confirmación (libera el stock; probar en backend si no existe el endpoint, si no existe solo ocultar el botón y dejarlo anotado).
8. **Conflictos:** en cada tarjeta indica el estado del stock actual de la prenda («hoy hay 0») y deshabilita «Reintentar» si sigue en 0, con el texto «Sin stock todavía»; «Descartar» pide confirmación; después de reintentar/descartar actualiza el contador (punto 2) y la campana.
9. **Perfil / Diagnóstico:** botón «Copiar diagnóstico» (usuario, rol, empresa, hora de la copia local, versión de la app, pendientes, conflictos) y «Cerrar sesión» con diálogo que avisa si hay operaciones pendientes de enviar.
10. **Inicio de cada actor:** mostrar «Última sincronización: hh:mm» y el estado de red; botón de refrescar con animación que no bloquee la pantalla.

## C. Extras funcionales (haz todos los que sean seguros)
11. **Modo oscuro y escalado de texto:** comprobar que ninguna pantalla se desborda con texto grande (accesibilidad del sistema 130 %) ni con tema oscuro; corrige los desbordes.
12. **Feedback táctil y carga:** `CircularProgressIndicator` o skeleton en toda carga > 300 ms, botones que se deshabilitan mientras envían (evita doble toque / doble compra), `HapticFeedback.lightImpact()` en acciones clave (registrar venta, pagar, deshacer).
13. **Errores de red amigables:** unifica los mensajes («No hay conexión, se guardó en este teléfono», «El servidor no respondió, reintentamos solos») en un único helper; nunca mostrar texto técnico (códigos HTTP, excepciones).
14. **Búsqueda del catálogo:** debounce de 300 ms, historial de las 5 últimas búsquedas y sugerencia «¿Quiso decir…?» si no hay resultados.
15. **Mis compras / Reservas:** filtros rápidos (Todas · Por pagar · Pagadas · Con conflicto) y buscador por código.
16. **Comprobantes sin conexión:** si el comprobante ya se descargó una vez, que «Ver comprobante» funcione sin red desde la copia local.
17. **Diagnóstico de salud al iniciar:** si la copia local tiene más de 24 h, aviso suave «Actualice el catálogo» con botón, sin bloquear.
18. **Web (consistencia):** el aviso de sincronización de la web debe ser único y de 5 s, y los pedidos «Por pagar» deben destacarse igual que en el móvil.

## D. Pruebas y entrega
- `flutter analyze` sin avisos y `flutter test` verde, con pruebas nuevas para: SnackBar que desaparece (1), contador de conflictos (2), botón «Marcar no encontrada» con diálogo (3), panel de venta con IVA (4), cierre de teclado/descartar venta (5), «Marcar todos como leídos» (6), «Reintentar» deshabilitado sin stock (8).
- `pytest` y `npm run build` verdes si tocas backend/web.
- No toques credenciales ni datos reales. Un commit por tema, en español, a mi nombre, **sin co-autor**; sube a `correccion-pago` y `main`.
- Entrégame: lista de commits y tabla «punto → hecho / cómo se probó / no hecho y por qué». No compiles la APK: yo la lanzo desde Actions.

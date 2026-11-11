# E3 · Móvil (Flutter): cliente con y sin conexión en el catálogo, la ficha, el carrito y el pago

(Pega antes `00_BLOQUE_COMUN.md`.)

Objetivo: lo mismo que ya funciona en la web debe funcionar en las pantallas normales de la app, no en «Modo sin conexión».

## Tareas
1. **Indicador y conectividad:** `OfflineController.enLinea` (y el chip de la barra) deben pasar a «Sin conexión» también cuando una llamada falla con `ApiException.sinConexion` (servidor inalcanzable), y volver a «En línea» al primer éxito o cuando `Conectividad` vea red. Una sola fuente de verdad para todas las pantallas y avisos de reconexión (toast + notificación local si la app está en segundo plano).
2. **Ficha de prenda** (`catalogo_screen.dart`, hoja con «Disponibilidad en»): si `opciones/detalle` fallan por `sinConexion`, armar las variantes, el stock por sucursal, el precio y la galería desde `productos_locales` (SQLite). Mostrar «Datos al …». El selector de sucursal funciona con la copia. Reservar y Agregar quedan **habilitados** si la variante tiene stock en la copia.
3. **Carrito local en SQLite** (ya existen `guardarCarritoCliente/carritoClienteLocal` en `offline_repository.dart`): `agregarAlCarrito`, cambiar cantidad, quitar y elegir sucursal sin red escriben en el carrito local; con red se espejan los datos del servidor al local en cada carga. Al volver la red se fusiona con el del servidor (igual que `fusionarLocal` en la web) sin duplicar ni perder ítems.
4. **`carrito_screen.dart`:** si no hay red, mostrar el carrito local (con «Datos al …») en lugar del mensaje rojo; botón «Pagar» → flujo de compra sin conexión. Si no hay carrito local, mensaje claro, nunca pantalla vacía.
5. **Pago sin conexión integrado al flujo normal:** reutilizar la lógica de `registrar_offline_screen.dart` (D4: `tarjeta_guardada_id` + `total_autorizado`, autorización del cobro, comprobante provisional `LOC-…`) desde `entrega_screen.dart`/`carrito_screen.dart`. Tarjeta nueva: deshabilitada con aviso «necesita Internet». Tras guardar: pantalla de «compra pendiente» con su estado.
6. **Resto de pantallas del cliente:** `entrega_screen.dart`, `tarjetas_screen.dart`, `mi_reserva_screen.dart`, `reservas_screen.dart`, `pedidos_screen.dart`, `asistente_screen.dart`, vestidor, avisos: cada `catch (ApiException)` debe distinguir `sinConexion` y mostrar copia local o mensaje claro; ningún `CircularProgressIndicator` sin salida; recarga automática al volver la red.
7. **Aviso al reconectar:** notificación local (no push de servidor) «Volvió la conexión: se enviaron N operaciones», y refresco de la pantalla abierta.

## Pruebas (solo las nuevas o afectadas)
`flutter test` de: ficha de prenda sin red (variantes, botones habilitados), carrito local (agregar, cantidad, quitar, fusión), pago con tarjeta guardada sin red (queda en cola con UUID), chip de estado ante `sinConexion`. Luego `flutter analyze`.

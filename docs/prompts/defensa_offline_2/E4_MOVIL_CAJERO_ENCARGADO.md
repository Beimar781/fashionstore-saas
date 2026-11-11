# E4 · Móvil (Flutter): Cajero, Encargado y demás roles integrados en sus pantallas normales

(Pega antes `00_BLOQUE_COMUN.md`. Requiere E3 hecho: comparte el indicador de conexión.)

Hoy el Cajero y el Encargado entran a «Caja sin conexión» y «Tareas de la sucursal» como accesos aparte del inicio (`home_screen.dart`, líneas con `offline.habilitado`). La ingeniera pidió que sea la interfaz principal.

## Tareas
1. **Cajero:** el acceso «Caja» del inicio abre una sola pantalla de Caja que funciona con red y sin red (con red: igual que la web; sin red: copia local, stock local, comprobante provisional, deshacer). Eliminar la duplicación «Caja» vs «Caja sin conexión»; dejar «Diagnóstico sin conexión» como pantalla de apoyo.
2. **Cajero, devoluciones y cambios:** una sola pantalla con y sin red (plazo de devolución, lo ya devuelto, monto a devolver en conflicto).
3. **Encargado:** «Tareas de la sucursal» (Recepción, Ajuste, Reservas) y Conflictos accesibles desde su inicio normal; cada pestaña con datos de la copia y estados claros; reservas sucursal se actualizan al volver la red.
4. **Proveedor y Administrador en móvil:** verifica qué ofrece la app para estos roles. Si no tienen funciones sin conexión en el documento, su inicio debe mostrar «Esta función necesita Internet» y botones deshabilitados con `necesitaInternet`, y las consultas que ya vieron, con «Datos al …». Nada de spinner infinito.
5. **Conflictos (CU-40):** pantalla accesible a quien corresponda con REINTENTAR/DESCARTAR y monto a devolver; aviso al afectado.
6. **Consistencia con la web:** mismos textos de error de las fichas de CU, mismos estados (REGISTRADA_LOCAL → ENVIADA → CONFIRMADA | RECHAZADA | EN_CONFLICTO), misma línea de tiempo y deshacer solo en REGISTRADA_LOCAL.

## Pruebas (solo las nuevas o afectadas)
`flutter test` de Caja con y sin red (misma pantalla), devolución sin red, Encargado recepción/ajuste/reserva en cola, Proveedor/Admin sin spinner infinito. Luego `flutter analyze`.

# Prompt J — Pedidos por pagar no aparecen en "Mis compras"

Hallazgo en la APK real (commit 57358e5, Cliente EMP-A): al reconectar, una compra hecha sin conexión con «Dejar por pagar» se sincroniza (queda CONFIRMADA y el aviso dice «Su compra PED-… está lista: pague con tarjeta en Mis compras»), pero en **Mis compras** (móvil y, probablemente, web) el pedido no aparece, así que el cliente no puede pagarlo.

Causa: `backend/app/primer_parcial/ventas/cu12_historial_compras/repository.py` define `FINALIZADAS = ("PAGADO", "PENDIENTE_CONFIRMACION")` y `GET /compras` sin `estado` solo devuelve esas. El móvil (`pedidos_screen.dart`, botón «Pagar con tarjeta» para `PENDIENTE_PAGO`) y el aviso ya esperan verlo.

Haz esto:
1. Incluye `PENDIENTE_PAGO` en el listado por defecto de `GET /compras` (renombra la constante a algo como `VISIBLES_AL_CLIENTE`). Revisa que ningún otro código dependa de `FINALIZADAS`.
2. Verifica web (`/tienda/compras`) y móvil: el pedido por pagar se ve con su estado legible «Por pagar» y el botón de pagar (sin comprobante todavía).
3. Prueba de backend: un pedido `PENDIENTE_PAGO` del cliente aparece en `GET /compras`; el de otro cliente u otra empresa no.
4. Commit en español a mi nombre, sin co-autor; corre `pytest`, `npm run build`, `flutter analyze` y `flutter test` solo si cambiaste archivos de cada parte. Si tocas `movil/`, avísame para compilar otra APK.

## Puntos adicionales (APK real, Cajero y Encargado de EMP-A)

5. **Catálogo sin renovar al cambiar de usuario (móvil).** El Cajero y el Encargado iniciaron sesión menos de 15 min después de que el Cliente descargó el catálogo y no se les renovó: el Encargado vio «No hay ventas de esta sucursal dentro del plazo hasta la última descarga (14:59)» y solo tras «Actualizar catálogo» aparecieron CMP-001-000008, 000007, etc. La renovación al iniciar sesión (RN21) no debe depender del límite de 15 minutos cuando cambia el usuario o el rol: renueva siempre en el login, y que la copia local quede asociada al usuario/rol que la descargó (y se borre al cerrar sesión). Revisa en `movil/lib/features/offline/` el controlador y la precarga.
6. **Snackbar fijo tapa botones.** El aviso «Sincronización completa… Ver detalle» queda más de un minuto y tapa el botón «Registrar venta en el dispositivo» de la Caja y el último acceso del inicio. Dale duración corta (4–5 s) y que no se acumule/encole.
7. **Tareas de la sucursal → Reservas:** el botón «Preparar» sale con texto oscuro sobre fondo oscuro y pegado a «Atender» (se lee como deshabilitado). Ajusta el estilo del botón deshabilitado y la separación.
8. Textos menores: la Caja dice «Venta de contado sin conexión» también con conexión (ponlo solo sin conexión); en Operaciones oculta el UUID técnico y «1 intento(s) de envío» mientras no haya red; en el inicio del Cajero/Encargado sube Caja y Devoluciones por encima de la lista de avisos.

Si tocas `movil/`, avísame para compilar una APK nueva.

# Corrección urgente — pago con tarjeta nueva en Stripe y ficha inexistente (defensa del jueves 12/11)

Pega este prompt completo en Claude Code. Está en español porque así trabajamos.

## Reglas
Lee `CLAUDE.md` y respétalo. Se puede tocar `main`. Nunca ver ni escribir contraseñas ni claves; no cambies `user.name` ni `user.email` de git. Pruebas solo de lo que cambies y al final la suite del frontend. `git add`, `git commit` y `git push` con mi identidad, mensaje corto en español, **sin líneas de coautoría**. Si algo falla, no hagas commit y explica.

## 1. «Pagar» con una tarjeta nueva falla en Railway (Stripe modo prueba)
Al pagar con tarjeta nueva (y «Guardar esta tarjeta para mis próximas compras» marcado) sale «✖ Pago rechazado … Motivo: We could not retrieve data from the specified Element. Please make sure the Element you are attempting to use is mounted and the ready event has been emitted. No se cobró nada.»

Causa probable (verifícala, no la adivines): en `frontend/src/app/features/primer-parcial/ventas/pago-tarjeta.component.ts`, `pagar()` pone `fase = 'procesando'` y el bloque `@if (fase() === 'pago' || 'rechazado' || 'error')` que contiene `<div id="tarjeta-stripe">` se destruye; cuando llega `confirmarConStripe()` el Element `campoTarjeta` ya no está montado y `stripe.confirmCardPayment` falla. Además el error de Stripe.js se muestra como «Pago rechazado» (402), engañoso.

Corrección:
1. Mantén el `<div id="tarjeta-stripe">` (y el Element) montado durante `procesando` (ocúltalo con `[hidden]`/CSS en lugar de quitarlo con `@if`), y que `montarStripe()` solo recree el Element si realmente no está montado.
2. Si `confirmCardPayment` devuelve `r.error` por un motivo del cliente (campo vacío/no montado/número inválido), no llames al servidor como si fuera un rechazo bancario: muestra un mensaje claro («Revise los datos de la tarjeta») y deja reintentar. Reserva «Pago rechazado» para rechazos reales del banco/Stripe.
3. Revisa que «Guardar esta tarjeta» pase `setup_future_usage` y que la tarjeta guardada aparezca luego en «Tarjetas guardadas» (web y la copia local del móvil, `actualizarTarjetas`).
4. Test del componente: durante `procesando` el contenedor de Stripe sigue en el DOM; un error de Stripe.js no se muestra como rechazo bancario.
5. Dime cómo probar con la tarjeta de prueba de Stripe (yo escribo el número a mano en la web) y qué mensaje debe verse en cada caso (aprobada, rechazada 4000 0000 0000 0002, campo vacío).

## 2. Ficha de prenda con id inexistente (`/tienda/catalogo/27`)
Con red muestra tres avisos «Producto no encontrado» y se queda en «Cargando…» para siempre. Debe mostrar «Prenda no encontrada» con un enlace al catálogo (sin spinner infinito y un solo aviso). Revisa lo mismo en `producto-detalle.page.ts` y en cualquier página de detalle por id (`/empresa/...`, reservas, pedidos). Sin conexión ya funciona («necesita Internet»).

## Al terminar
Resumen en español, archivos cambiados y el commit. Si el despliegue de Railway es automático, dime cuándo termina.

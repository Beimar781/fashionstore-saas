# Prompt I — Pulido final web (4 detalles menores)

Contexto: la verificación en Railway del prompt H salió bien. Quedan 4 detalles de pulido, solo frontend Angular. No toques backend ni móvil. Commits a mi nombre, sin líneas de co-autor. Corre solo los tests de los archivos que cambies.

1. **Proveedor / Abastecimiento — botón "Cancelar" del aviso de remisión**
   Hoy, sin conexión, solo muestra el aviso "Esta función necesita Internet." al pulsarlo. Aplícale `[necesitaInternet]` igual que a "Nuevo aviso de remisión", para que salga atenuado (`sin-internet`, `aria-disabled`). Archivo: `features/primer-parcial/proveedores/abastecimiento.page.ts` (compartido con Administrador). Revisa también "Ver": ese debe seguir funcionando.

2. **Caja (Cajero) — "IVA incluido" en la pre-factura**
   Hoy solo aparece después de registrar la venta. Muestra "IVA incluido: Bs X" debajo del Total desde que hay prendas en la pre-factura, con el mismo cálculo (13% incluido: total × 0,13 / 1,13, 2 decimales) que usa la venta local. Reutiliza la función existente, no dupliques la fórmula.

3. **Ficha de prenda — aviso al elegir sucursal sin conexión**
   Al elegir sucursal sin conexión sale el toast "Sin conexión con el servidor." aunque el stock se muestra bien desde la copia local. Quita ese toast cuando hay copia local del stock; si no hay copia, muestra "Sin conexión: no hay stock guardado para esta sucursal." (archivo: `features/catalogo/prenda.page.ts`).

4. **Ficha de prenda — "Agregar al carrito" deshabilitado sin sucursal**
   Hoy solo hay un tooltip. Agrega un texto visible junto al botón: "Elija una sucursal para agregar al carrito." que desaparezca al elegir sucursal. Mantén la lógica `sucursalParaCarrito()`.

Al terminar: agrega una prueba unitaria mínima por punto 2 y 4, haz un commit por punto y push a main. Responde con la lista de commits y qué archivos tocaste.

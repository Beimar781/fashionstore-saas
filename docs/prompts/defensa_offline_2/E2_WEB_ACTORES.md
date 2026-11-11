# E2 · Web: cada actor con y sin conexión en SUS pantallas normales

(Pega antes `00_BLOQUE_COMUN.md`. Requiere E1 hecho.)

Para cada actor recorre el código de sus pantallas web y deja lo pedido por la ingeniera funcionando sin conexión. Si algo ya funciona, solo verifícalo con una prueba. Corrige lo que falle.

## Cliente
- Catálogo, ficha de prenda (`producto-detalle`), búsqueda, filtros: desde la copia local; ficha con variantes, stock por sucursal y precio.
- Agregar al carrito, cambiar cantidad, quitar y elegir sucursal sin red: se aplican al carrito local (con aviso «se enviará al volver la red») y se fusionan al volver (`fusionarLocal`). Sin que se pierda lo ya existente en el servidor.
- Reservar sin red (ya existe: verifica que se hace desde la pantalla normal de la ficha/carrito).
- Checkout: entrega y facturación, tarjeta guardada (solo `tarjeta_guardada_id` + `total_autorizado`), autorización del cobro, «Guardar compra para sincronizar» y pantalla de «compra pendiente» con comprobante provisional `LOC-…`. Tarjeta nueva: botón deshabilitado con el texto «necesita Internet».
- Mis compras / Mis reservas: lo local primero (operaciones REGISTRADA_LOCAL con su estado) y debajo lo ya sincronizado.
- Asistente de compras: si no hay red, respuesta local sobre el catálogo descargado o mensaje claro.

## Cajero (Caja y Devoluciones y cambios)
- Caja: buscar y escanear con la copia local, descontar el stock local, comprobante provisional, deshacer, estado. **Revisa por qué todas las prendas salen «Sin stock» en EMP-B**: ¿el stock local se calcula por la sucursal del cajero y esa sucursal tiene 0 en la base, o hay un fallo al mapear `stock` por sucursal? Si es dato, agrega al seed de demo (EMP-B, la sucursal del cajero) stock suficiente para Camisa Oxford, Polo Básico y Pantalón de Lana, sin tocar migraciones subidas.
- **Fotos rotas en Caja:** usa la misma función de URL de imagen que el catálogo del cliente (que sí muestra fotos); revisa también que las imágenes se descarguen a la copia local para verse sin red.
- Devoluciones: la lista de recientes y la búsqueda de venta desde la copia local; la devolución se encola con sus validaciones; conflictos con monto a devolver.

## Encargado de sucursal
- Reservas de la sucursal (preparar, prenda no encontrada, atender), Recepción de lotes, Ajuste de inventario, Conflictos: cargar desde copia/precarga; acciones encoladas; sin vacío engañoso.

## Proveedor
- Abastecimiento y recepciones: ver lotes ya descargados y registrar lo permitido sin red (según el documento); lo que necesite servidor, deshabilitado con `necesitaInternet` y mensaje.

## Administrador / SuperAdmin
- Lo que el documento permite sin red (consultas de lo último visto: usuarios, sucursales, productos, reportes) se ve con la fecha «Datos al…»; lo demás (crear, editar, reportes con IA, suscripción) queda deshabilitado con mensaje, nunca «Cargando…».
- Reportes CU-23: si no hay red, mostrar el último reporte visto y el botón de generar deshabilitado.

## Pruebas (solo las nuevas o afectadas)
Un spec por actor con: abrir la pantalla con red apagada → muestra datos locales o mensaje claro (nunca «Cargando…»); acción principal encolada; al volver la red se sincroniza y la pantalla se recarga sola.

# Mensajes y reglas redactados en el código que faltan en el documento Word

El documento aprobado manda (RNF12). Cuando un caso de uso no trae ficha o la ficha no define un mensaje, el código usa uno redactado por
el equipo. Esta lista sirve para pasarlos después al Word (fichas, pruebas 5.2.1/5.3.1 y reglas de negocio) y dejar documento y código iguales.

Estado de cada fila: **Pendiente** = aún no está en el Word.

## Fase C

### CU-09 · Realizar reserva de múltiples prendas

El documento solo lo nombra en la tabla 2.5.5 («Modificado», RF14, RF19); **no tiene ficha ni prueba**. Falta redactarlas.

Flujo implementado (para la ficha): el cliente elige prendas (talla y color) → elige sucursal y horario aproximado → el sistema valida horario y
stock → crea la reserva con un código → pasa el stock de *disponible* a *reservado* → avisa a la sucursal (RF11) y confirma al cliente.

| # | Situación | Mensaje | Código HTTP | Estado |
|---|---|---|---|---|
| 1 | No se eligió ninguna prenda | «Seleccione al menos una prenda para reservar.» | 422 | Pendiente |
| 2 | El horario ya pasó | «El horario de la reserva debe ser posterior al momento actual.» | 422 | Pendiente |
| 3 | Horario a más de 14 días | «La reserva no puede programarse con más de 14 días de anticipación.» | 422 | Pendiente |
| 4 | Horario fuera de la atención de la sucursal | «El horario debe estar dentro del horario de atención de la sucursal (09:00 a 20:00).» (las horas salen del horario de la sucursal) | 422 | Pendiente |
| 5 | Falta stock de una o más prendas | «No hay stock suficiente en {sucursal} para: {producto} ({talla}, {color}): solicitadas {n}, disponibles {d}; …» | 409 | Pendiente |
| 6 | Una prenda está inactiva, retirada o no existe | «Una o más prendas ya no están disponibles en el catálogo.» | 422 | Pendiente |
| 7 | Sucursal inexistente, inactiva o de otra empresa | «Sucursal no encontrada.» | 404 | Pendiente |
| 8 | Cantidad fuera de 1 a 10 por prenda, o más de 20 prendas distintas | Mensaje de validación del campo (`items.0.cantidad: …`) | 422 | Pendiente |
| 9 | Quien reserva no es Cliente | «No tiene permisos para esta operación.» | 403 | Ya existe (mensaje general) |

Reglas de negocio nuevas (agregar a la lista de RN o a la ficha):

- **Vigencia:** la reserva vence 24 horas después del horario aproximado elegido (configurable por el sistema).
- **Anticipación máxima:** 14 días (configurable).
- **Todo o nada:** si falta stock de cualquier prenda no se aparta ninguna.
- **Una prenda repetida se suma** en una sola línea de la reserva.
- **Código de reserva:** `RSV-` + 8 caracteres, único por empresa, sin los caracteres 0, O, 1 e I para dictarlo sin errores.
- **Stock:** al reservar pasa de *disponible* a *reservada* (movimiento de inventario RESERVA); al cancelar, expirar o completar sin compra vuelve a
  *disponible*; al venderse (CU-29) pasa a *vendida*.
- **Expiración sin tareas programadas:** las reservas vencidas se liberan al consultar reservas (cliente o sucursal), al validar un código y al
  desactivar una sucursal.
- **Sucursal con reservas activas** (pendientes, preparadas o en probador): no se puede desactivar. Usa el mensaje que ya existe en CU-14:
  «La sucursal tiene reservas pendientes u operaciones sin sincronizar. Resuélvalas antes de desactivarla.»

### CU-10 · Consultar y cancelar reservas

Igual que CU-09: solo aparece en la tabla 2.5.5 («Modificado», RF14, RF20); **no tiene ficha ni prueba**.

| # | Situación | Mensaje | Código HTTP | Estado |
|---|---|---|---|---|
| 1 | Cancelar una reserva que no está pendiente ni preparada | «No se puede cancelar una reserva {estado}.» con el estado en minúscula: pendiente, preparada, en probador, completada, cancelada o expirada | 409 | Pendiente |
| 2 | La reserva no existe, es de otro cliente o de otra empresa | «Reserva no encontrada.» | 404 | Pendiente |
| 3 | Quien consulta no es Cliente | «No tiene permisos para esta operación.» | 403 | Ya existe (mensaje general) |

Reglas de negocio nuevas:

- El cliente **solo ve y cancela sus propias reservas**; la ajena responde 404 (no se revela su existencia).
- Se puede cancelar solo en estado **pendiente** o **preparada**; al cancelar, el stock vuelve a disponible y la sucursal recibe un aviso.
- El cliente puede filtrar por estado y consultar el estado de cada reserva (RF12).
- Estados de la reserva: pendiente → preparada → en probador → completada; y desde pendiente o preparada, cancelada o expirada.

### RF11 · Notificaciones (las generan CU-09, CU-10, CU-24 y CU-25)

Textos de los avisos, para agregarlos al RF11 o a las fichas:

| Aviso | A quién | Título / mensaje |
|---|---|---|
| Reserva nueva | La sucursal | «Nueva reserva {código}» · «{cliente} reservó {n} prenda(s) para el {fecha hora}. Prepárelas para su visita.» |
| Reserva registrada | El cliente | «Reserva {código} registrada» · «Su reserva en {sucursal} quedó registrada para el {fecha hora}. Presente el código {código} en el mostrador.» |
| Reserva cancelada | La sucursal | «Reserva {código} cancelada» · «{cliente} canceló su reserva. Las prendas volvieron a estar disponibles.» |
| Reserva expirada | El cliente | «Reserva {código} expirada» · «Su reserva venció sin ser atendida y las prendas volvieron a estar disponibles. Puede hacer una nueva reserva.» |

## Fase C · textos extra de CU-24 y CU-25

Estos dos casos **sí tienen ficha**; los textos de abajo son los que la ficha no define.

| CU | Situación | Mensaje | Estado |
|---|---|---|---|
| CU-24 | Preparar una reserva sin prendas por preparar | «La reserva no tiene prendas por preparar.» | Pendiente |
| CU-24 | Marcar «No encontrado» en una reserva ya atendida o cerrada | «No se puede modificar una reserva {estado}.» | Pendiente |
| CU-24 | Marcar «No encontrado» una prenda ya marcada | «La prenda ya fue marcada.» | Pendiente |
| CU-24 | Cambio de estado no permitido | «No se puede pasar una reserva {estado} a {estado}.» | Pendiente |
| CU-24 | Aviso al cliente al preparar | «Reserva {código} lista» · «Sus prendas ya están preparadas: puede pasar a la tienda con su código de reserva.» | Pendiente |
| CU-24 | Aviso al cliente por prenda no encontrada | «Ajuste en su reserva {código}» · «Lamentamos el inconveniente: una de sus prendas ya no está disponible en la tienda. Preparamos el resto de su reserva.» (o «Su reserva fue cancelada.» si no queda ninguna) | Pendiente |
| CU-24 | Aviso de ajuste de stock a la sucursal | «Ajuste de stock · reserva {código}» · «Una prenda de la reserva {código} no se encontró en físico; se descontó del inventario de la sucursal.» | Pendiente |
| CU-25 | El código pertenece a otra sucursal de la misma empresa | «La reserva corresponde a otra sucursal.» | Pendiente |
| CU-25 | Atender una reserva que no está pendiente ni preparada | «La reserva debe estar pendiente o preparada para atender al cliente.» | Pendiente |
| CU-25 | Completar sin haber atendido al cliente | «Primero debe atender al cliente (entregar las prendas).» | Pendiente |

Interpretación confirmada de **CU-25** (agregar al flujo o a las excepciones de la ficha): al cerrar la atención el Encargado indica si el cliente
se lleva las prendas.

- **No se lleva nada:** la reserva queda *completada* y el stock vuelve a *disponible*.
- **Se lleva las prendas:** la reserva queda *en probador* con su stock apartado hasta que el Cajero la cobre en CU-29 (venta presencial).
  Una reserva *completada* o *cancelada* ya no sirve como código en el mostrador; su mensaje es el de la ficha: «El código de reserva no existe o ya ha expirado su vigencia.»

## Fase D

Los CU-08, CU-11, CU-12 y CU-32 **sí tienen ficha y prueba en el Anexo B**; sus mensajes oficiales se usan tal cual:
«La cantidad solicitada supera el stock disponible temporalmente.» (CU-08), «La transacción no pudo ser procesada, verifique su método de pago o saldo
disponible.» (CU-11), «Aún no has realizado ninguna compra en nuestras tiendas.» (CU-12) y «Transacción denegada por su banco» (CU-32).
Lo de abajo es lo que las fichas **no** definen.

### Decisiones de diseño que conviene reflejar en las fichas

- **CU-08 · el carrito tiene sucursal.** El stock sale de la sucursal elegida, así que el carrito se asocia a una sola sucursal (la primera que se elige al agregar
  una prenda; se puede cambiar en el carrito). Las prendas que no tengan stock en la nueva sucursal quedan marcadas y no se pueden pagar. El stock no se aparta en
  el carrito: se verifica al agregar, al mostrar el carrito, al hacer el checkout y al cobrar.
- **CU-08 · impuestos.** Los precios ya incluyen el IVA (13 %, configurable); el carrito y el comprobante muestran cuánto del total es IVA.
- **CU-11 · el pedido nace en el checkout.** «Proceder al pago» convierte el carrito en un pedido *Pendiente de pago* con precios congelados; el pedido pasa a
  *Pagado* cuando la pasarela aprueba, y recién entonces se descuenta el stock, se numera el comprobante y se vacía el carrito. Un cliente tiene un solo pedido por
  pagar a la vez: un nuevo checkout cancela el anterior.
- **CU-11 · comprobante.** Número correlativo por sucursal (`CMP-<sucursal>-<número>`), descargable en PDF.
- **CU-12 · qué es una compra.** Se listan los pedidos *Pagados* y los *Pendientes de confirmación*; los pedidos sin pagar o cancelados no aparecen. Las ventas
  presenciales (CU-29) se agregarán al mismo historial.
- **CU-32 · autorizar y cobrar en dos tiempos.** Primero la pasarela *autoriza* la tarjeta; el sistema confirma el stock y solo entonces *cobra*. Si las prendas se
  agotan mientras el cliente paga, se anula la autorización y no se cobra nada.
- **CU-32 · pasarela.** Stripe en modo de prueba cuando hay claves en el `.env`; si no, una pasarela simulada que solo acepta tarjetas de prueba. Stripe no cobra en
  bolivianos: en modo de prueba se cobra el equivalente en dólares (6,96 Bs por dólar, configurable). El número de la tarjeta y el CVC nunca se guardan: solo marca,
  últimos 4 dígitos y vencimiento.
- **CU-32 · tarjeta guardada.** El cliente puede guardar la tarjeta para próximas compras, usarla y eliminarla.
- **CU-32 · respuesta por consulta, no por webhook.** El sistema lee el resultado directamente de la pasarela (la ficha admite «Webhook o Response»). Un pago sin
  respuesta queda *Pendiente de confirmación* y el cliente puede pedir verificarlo.

### Mensajes nuevos

| CU | Situación | Mensaje | Código HTTP | Estado |
|---|---|---|---|---|
| CU-08 | Agregar sin haber elegido sucursal | «Elija la sucursal en la que desea comprar.» | 422 | Pendiente |
| CU-08 | Agregar una prenda inactiva, retirada o de otra empresa | «La prenda ya no está disponible en el catálogo.» | 422 | Pendiente |
| CU-08 | Agregar de otra sucursal con el carrito ya iniciado | «Su carrito es para la sucursal {nombre}. Cambie de sucursal en el carrito o vacíelo.» | 409 | Pendiente |
| CU-08 | Modificar o quitar una prenda que no es del carrito del cliente | «Prenda del carrito no encontrada.» | 404 | Pendiente |
| CU-08 | Prenda del carrito sin stock tras cambiar de sucursal o de stock | Aviso: «{prenda} ({talla}, {color}): en {sucursal} hay {n} disponible(s) y tiene {m} en el carrito.» | — | Pendiente |
| CU-08 | Prenda del carrito retirada del catálogo | Aviso: «{prenda} ({talla}, {color}) ya no está disponible en el catálogo. Quítela del carrito.» | — | Pendiente |
| CU-11 | Checkout con el carrito vacío | «Su carrito está vacío.» | 422 | Pendiente |
| CU-11 | Checkout con prendas sin stock o retiradas | «Hay prendas sin stock suficiente o retiradas del catálogo. Ajuste su carrito antes de pagar.» + el detalle | 409 | Pendiente |
| CU-11 | Entrega a domicilio sin dirección | «Ingrese la dirección de entrega.» | 422 | Pendiente |
| CU-11 | Sin NIT o CI | «Ingrese su NIT o CI para la facturación.» | 422 | Pendiente |
| CU-12 | Pedido inexistente, de otro cliente o de otra empresa | «Pedido no encontrado.» | 404 | Pendiente |
| CU-12 | Descargar el comprobante de una compra sin pagar | «Solo hay comprobante para compras pagadas.» | 409 | Pendiente |
| CU-32 | El stock se agotó antes de pedir el pago | «Algunas prendas se agotaron: {prenda} ({talla}, {color}): quedan {n}, necesita {m}. No se realizó ningún cobro. Ajuste su carrito e intente de nuevo.» | 409 | Pendiente |
| CU-32 | El stock se agotó mientras el cliente pagaba | Igual, con «se agotaron mientras pagaba» | 409 | Pendiente |
| CU-32 | Pago rechazado: motivo del banco | «Transacción denegada por su banco» (fondos insuficientes o tarjeta rechazada); otros motivos: «Su tarjeta está vencida.», «El código de seguridad (CVC) es incorrecto.», «Este entorno solo admite tarjetas de prueba.» (solo pasarela simulada) | 402 | Pendiente (el primero ya está en la ficha) |
| CU-32 | Pago sin respuesta de la pasarela | «Pendiente de confirmación: la pasarela no respondió. Verificaremos el estado de su pago; no se le cobrará dos veces.» | 200 | Pendiente (la ficha solo dice «Pendiente de confirmación») |
| CU-32 | Pago aprobado | «Pago aprobado.» | 200 | Pendiente |
| CU-32 | Pedido que ya no está por pagar | «El pedido no está pendiente de pago.» | 409 | Pendiente |
| CU-32 | Confirmar un pago ya rechazado o cancelado | «Este pago ya fue procesado. Inicie un nuevo pago.» | 409 | Pendiente |
| CU-32 | Conciliar un pago que no está pendiente de confirmación | «Este pago no está pendiente de confirmación.» | 409 | Pendiente |
| CU-32 | Número de tarjeta inválido (solo pasarela simulada) | «El número de la tarjeta no es válido.» | 422 | Pendiente |
| CU-32 | CVC inválido (solo pasarela simulada) | «El código de seguridad (CVC) debe tener 3 o 4 dígitos.» | 422 | Pendiente |
| CU-32 | Faltan los datos de la tarjeta (solo pasarela simulada) | «Ingrese los datos de la tarjeta.» | 422 | Pendiente |
| CU-32 | Tarjeta guardada inexistente, ajena o de otra pasarela | «Tarjeta no encontrada.» | 404 | Pendiente |
| CU-32 | Pago inexistente o de otro cliente | «Pago no encontrado.» | 404 | Pendiente |
| CU-32 | La pasarela no está disponible | «No se pudo comunicar con la pasarela de pago. Intente nuevamente.» | 502 | Pendiente |

### Tarjetas de prueba de la pasarela simulada

| Tarjeta | Resultado |
|---|---|
| 4242 4242 4242 4242 (Visa) y 5555 5555 5555 4444 (Mastercard) | Pago aprobado |
| 4000 0000 0000 9995 | Rechazada: fondos insuficientes («Transacción denegada por su banco») |
| 4000 0000 0000 0002 | Rechazada por el banco |
| 4000 0000 0000 0069 | Rechazada: tarjeta vencida |
| 4000 0000 0000 0127 | Rechazada: CVC incorrecto |
| 4000 0000 0000 0119 | La pasarela no responde: queda *Pendiente de confirmación* (se concilia después) |
| Cualquier otro número válido | Rechazada: solo se admiten tarjetas de prueba |

Con Stripe en modo de prueba valen las tarjetas de prueba de Stripe (por ejemplo 4242 4242 4242 4242 y 4000 0000 0000 9995).

## Fase E

CU-27, CU-28 y CU-30 **sí tienen ficha y prueba en el Anexo B**; sus mensajes oficiales se usan tal cual: «Acceso denegado a datos de otras sucursales.» (CU-27),
«El código de barras escaneado no coincide con ningún producto registrado en la base de datos.» (CU-28) y «Falla de red con el servicio de impuestos, se generará un
comprobante interno temporal.» (CU-30). **CU-29 no tiene ficha ni prueba** en el Word (solo aparece en la tabla 2.5.5 como «Modificado», RF15 y RF19): falta redactarla.

### Decisiones de diseño que conviene reflejar en las fichas

- **CU-29 · flujo.** El cajero escanea o busca las prendas (CU-28), arma la pre-factura y registra la venta presencial, que queda *pendiente de cobro* (el stock no se
  toca). También puede cobrar una reserva: escribe el código, elige lo que el cliente se lleva y el resto vuelve a disponible. Una reserva solo se cobra si está
  *preparada* o *en probador*, es de su sucursal y no venció. Una reserva tiene una sola venta abierta: la nueva reemplaza a la anterior.
- **CU-29 · cliente.** Si se indica el correo de un cliente registrado (o la venta nace de su reserva), la compra aparece en su historial (CU-12). Sin cliente, la
  venta es de mostrador; el NIT/CI por defecto es 0 y la razón social «Sin nombre».
- **CU-29 / CU-30 · sucursal.** Un Cajero (o el Encargado, que también puede operar la caja) solo vende y cobra en su sucursal (RN10). Una venta de otra sucursal u otra
  empresa no existe para él (404).
- **CU-30 · el stock se descuenta al cobrar**, no al registrar la venta. Movimiento VENTA con referencia VENTA; si la venta viene de una reserva, el stock pasa de
  *reservado* a *vendido* (VENTA_RESERVA) y lo que el cliente no se lleva vuelve a *disponible*. Cada venta lleva un comprobante `CMP-<sucursal>-<número>`.
- **CU-30 · medios de pago.** Efectivo (el sistema calcula el cambio) y tarjeta (con la misma pasarela de CU-32; en
  caja no se guardan tarjetas). Un solo método por venta; el pago mixto no se implementa en esta versión.
- **CU-30 · sin stock a mitad del cobro.** Si las prendas se agotan mientras se cobra, no se descuenta nada y no se registra ningún cobro. En efectivo la venta sigue
  pendiente para que el cajero la anule y la rehaga; con tarjeta se anula la autorización y la venta queda cancelada.
- **CU-30 · servicio de impuestos.** Adaptador simulado (regla 12): autoriza el comprobante con un código de prueba y el comprobante es una *factura*. Si el servicio no
  responde, la venta se cobra igual y el comprobante queda como *interno temporal*. La conversión posterior del temporal en factura todavía no está implementada.
- **CU-27 · cierre de caja.** No hay un registro de cierre: el «cierre» del día es el arqueo por método (efectivo, tarjeta), con el efectivo que debe haber en caja
  (lo cobrado en efectivo, ya descontado el cambio). Incluye las ventas de caja, los pedidos online pagados de la sucursal y las reservas completadas del día.
- **CU-27 · otra sucursal.** Pedir los datos de otra sucursal (o un ticket de otra sucursal de la misma empresa) responde 403 con el mensaje de la ficha; un ticket de otra
  empresa responde 404 (no se revela que existe).
- **CU-12 · historial.** Ahora incluye también las compras presenciales de los clientes registrados, y el cliente puede descargar su comprobante.

### Mensajes nuevos

| CU | Situación | Mensaje | Código HTTP | Estado |
|---|---|---|---|---|
| CU-27 | Venta inexistente o de otra empresa | «Venta no encontrada.» | 404 | Pendiente |
| CU-27 / CU-28 / CU-29 / CU-30 | Empleado sin sucursal asignada | «Su usuario no tiene una sucursal asignada.» | 403 | Pendiente (RN10) |
| CU-29 | Venta sin prendas | «Agregue al menos una prenda a la venta.» | 422 | Pendiente |
| CU-29 | Prenda inactiva, retirada o de otra empresa | «Una o más prendas ya no están disponibles en el catálogo.» | 422 | Pendiente |
| CU-29 | Falta stock en la sucursal del cajero | «No hay stock suficiente en {sucursal} para: {prenda} ({talla}, {color}): solicitadas {n}, disponibles {d}; …» | 409 | Pendiente |
| CU-29 | Código de reserva inexistente, de otra empresa, no preparada, cancelada, completada o vencida | «El código de reserva no existe o ya ha expirado su vigencia.» (el mismo de CU-25) | 404 | Ya está en CU-25 |
| CU-29 | La reserva es de otra sucursal | «La reserva corresponde a otra sucursal.» | 409 | Pendiente |
| CU-29 | Prendas o cantidades que no están en la reserva | «La venta incluye prendas o cantidades que no están en la reserva.» | 422 | Pendiente |
| CU-29 | Correo de cliente inexistente, de un empleado o de otra empresa | «No hay un cliente registrado con ese correo.» | 404 | Pendiente |
| CU-29 | Anular una venta ya cobrada | «Una venta ya cobrada no se puede anular; registre una devolución.» | 409 | Pendiente |
| CU-29 | Anular una venta ya anulada | «La venta ya está anulada.» | 409 | Pendiente |
| CU-30 | Efectivo sin monto recibido | «Ingrese el monto recibido.» | 422 | Pendiente |
| CU-30 | Monto recibido menor al total | «El monto recibido es menor al total de la venta.» | 422 | Pendiente |
| CU-30 | Cobrar una venta que no está pendiente | «La venta no está pendiente de cobro.» | 409 | Pendiente |
| CU-30 | Comprobante de una venta sin cobrar | «Solo hay comprobante de ventas cobradas.» | 409 | Pendiente |
| CU-30 | El stock se agotó a mitad del cobro | «Algunas prendas se agotaron mientras pagaba: {prenda} ({talla}, {color}): quedan {n}, necesita {m}. No se realizó ningún cobro. Anule la venta y regístrela de nuevo con lo disponible.» | 409 | Pendiente |
| CU-30 | La reserva venció a mitad del cobro | «La reserva ya no está vigente. No se realizó ningún cobro.» | 409 | Pendiente |
| CU-30 | Tarjeta rechazada en caja | Los mismos de CU-11 y CU-32: «La transacción no pudo ser procesada…» con el motivo «Transacción denegada por su banco» | 402 | Ya están en CU-11 y CU-32 |

### Configuración nueva

`IMPUESTOS_SIMULAR_FALLA=true` en `backend/.env` (opcional): simula que el servicio de impuestos no responde, para mostrar el comprobante interno temporal de la ficha CU-30.

## Fase F

CU-41 **no tiene ficha ni prueba en el Word** (solo aparece en la tabla 2.5.5 y en RN15): falta redactarla. Los mensajes de abajo salen del código.

### Decisiones de diseño que conviene reflejar en las fichas

- **CU-41 · quién.** Lo registran el Cajero y el Encargado, solo sobre ventas de **su** sucursal (RN10); una venta de otra sucursal u otra empresa no existe para ellos (404). El
  Administrador solo consulta las notas de toda la empresa y fija el plazo.
- **CU-41 · RN15.** Se requiere el comprobante de la venta (`CMP-<sucursal>-<número>`); se busca sin distinguir mayúsculas. Plazo de devolución por empresa, 15 días desde el pago
  por defecto, configurable de 0 a 365 días por el Administrador.
- **CU-41 · devolución parcial.** Se puede devolver parte de lo vendido y volver más tarde por el resto; nunca más de lo vendido menos lo ya devuelto.
- **CU-41 · inventario.** La prenda devuelta vuelve a *disponible* de la sucursal de la venta (movimiento DEVOLUCION, referencia DEVOLUCION). Se asume que la prenda se recibe en buen
  estado; no hay una bandeja de revisión de prendas dañadas.
- **CU-41 · reembolso en el mismo medio de pago.** Efectivo → efectivo; tarjeta → a la misma tarjeta por la pasarela (Stripe de prueba o
  simulada, regla 12). El reembolso se prorratea por el valor devuelto y el último devuelve exactamente lo que quedaba, para que la suma coincida con lo cobrado. Si la pasarela falla,
  la devolución no se registra y el inventario no cambia.
- **CU-41 · cambio.** Se devuelven una o más prendas y se entregan otras, sujeto a la disponibilidad de la sucursal. Si lo nuevo vale más, el cliente paga la diferencia en caja
  (**el cliente elige**: en efectivo, con cálculo del cambio, o con tarjeta por la misma pasarela del CU-32; con tarjeta primero se autoriza, luego se registra el cambio y recién entonces se cobra, y si falta stock
  o la tarjeta se rechaza no se cobra ni se registra nada). Si vale menos, se reembolsa la diferencia en el medio de la venta original. Se puede
  cambiar por la misma prenda que se devuelve.
- **CU-41 · nota.** Cada devolución o cambio emite una nota `NDV-<sucursal>-<número>` en PDF con las prendas, los montos y el medio del reembolso.
- **CU-41 · cobro de la diferencia con tarjeta.** El Cajero inicia el cobro (el servidor calcula el monto, nunca el navegador) y confirma la tarjeta; no se guardan tarjetas en caja. La diferencia cobrada con tarjeta se muestra
  aparte en CU-27 y no entra al efectivo de caja.
- **CU-27 · ventas netas.** El reporte del día muestra las ventas netas (vendido − devuelto + entregado en cambios), el detalle de devoluciones y descuenta del efectivo que debe haber
  en caja los reembolsos en efectivo (y suma las diferencias cobradas en efectivo).
- **Pagos en tienda (decisión del equipo).** En el local se paga con efectivo o tarjeta; online solo con tarjeta (cubierto por pruebas). Se quitó el QR que la ficha CU-30
  mencionaba como «QR simple local»: la ficha debe decir «efectivo o tarjeta». Los planes SaaS (CU-33/35) conservan «QR» como forma de pago administrativa de la suscripción.

### Mensajes nuevos

| CU | Situación | Mensaje | Código HTTP | Estado |
|---|---|---|---|---|
| CU-41 | Falta el comprobante | «Para devolver o cambiar una prenda se requiere el comprobante de la venta.» | 422 | Pendiente (RN15) |
| CU-41 | Comprobante inexistente, de otra sucursal o de otra empresa | «No se encontró una venta con ese comprobante en su sucursal.» | 404 | Pendiente |
| CU-41 | Fuera del plazo | «El plazo para devolver o cambiar esta compra venció el {fecha} (plazo de {n} días).» | 409 | Pendiente (RN15) |
| CU-41 | Sin motivo | «Indique el motivo de la devolución.» | 422 | Pendiente |
| CU-41 | Sin prendas elegidas | «Seleccione al menos una prenda a devolver.» | 422 | Pendiente |
| CU-41 | Línea que no pertenece a la venta | «La prenda indicada no pertenece a esa venta.» | 422 | Pendiente |
| CU-41 | Más de lo vendido | «Solo se pueden devolver {n} unidad(es) de {prenda} ({talla}, {color}): se vendieron {v} y ya se devolvieron {d}.» | 409 | Pendiente |
| CU-41 | Prenda ya devuelta por completo | «{prenda} ({talla}, {color}) ya fue devuelto por completo.» | 409 | Pendiente |
| CU-41 | Cambio sin prendas nuevas | «Un cambio requiere al menos una prenda nueva.» | 422 | Pendiente |
| CU-41 | Devolución con prendas nuevas | «Una devolución no lleva prendas nuevas; registre un cambio.» | 422 | Pendiente |
| CU-41 | Prenda nueva inactiva o retirada | «Una o más prendas del cambio ya no están disponibles en el catálogo.» | 422 | Pendiente |
| CU-41 | Sin stock para el cambio | «No hay stock suficiente en {sucursal} para el cambio: {prenda} ({talla}, {color}): solicitadas {n}, disponibles {d}.» | 409 | Pendiente |
| CU-41 | Cambio que vale más y no se indica el pago | «El cambio tiene una diferencia de Bs {monto} a cobrar: indique cómo paga el cliente.» | 422 | Pendiente |
| CU-41 | La diferencia se quiere pagar con tarjeta pero no hay diferencia | «El cambio no tiene una diferencia a cobrar.» | 422 | Pendiente |
| CU-41 | Se elige tarjeta sin iniciar el cobro | «Inicie el cobro con tarjeta de la diferencia antes de registrar el cambio.» | 422 | Pendiente |
| CU-41 | El cobro iniciado es de otra venta u otro cajero | «Cobro de la diferencia no encontrado.» | 404 | Pendiente |
| CU-41 | El cambio cambió después de iniciar el cobro (otras prendas o cantidades) o el cobro ya se usó | «El cobro de la diferencia ya no coincide con el cambio. Inicie el cobro con tarjeta nuevamente.» | 409 | Pendiente |
| CU-41 | Tarjeta rechazada al pagar la diferencia | Los mismos de CU-11 y CU-32: «La transacción no pudo ser procesada…» con el motivo del banco | 402 | Ya están en CU-11 y CU-32 |
| CU-41 | La pasarela no respondió al pagar la diferencia | «No se pudo comunicar con la pasarela de pago. Intente nuevamente: no se registró el cambio ni se cobró nada.» | 502 | Pendiente |
| CU-41 | Efectivo recibido menor a la diferencia | «El monto recibido es menor a la diferencia a cobrar.» | 422 | Pendiente |
| CU-41 | La pasarela no pudo reembolsar | «No se pudo reembolsar el pago en la pasarela: la devolución no se registró. Intente nuevamente.» | 502 | Pendiente |
| CU-41 | La venta no tiene pago aprobado | «La venta no tiene un pago aprobado que reembolsar.» | 409 | Pendiente |
| CU-41 | Nota inexistente o de otra sucursal/empresa | «Devolución no encontrada.» | 404 | Pendiente |

## Fase G

**CU-21, CU-22, CU-23, CU-36 y CU-42 no tienen ficha ni prueba en el Word** (solo aparecen en la tabla 2.5.2 y en las reglas RN07/RN08); **CU-07 sí** (Anexo B). Falta redactar las fichas de CU-21, 22, 23, 36 y 42.

### Decisiones de diseño que conviene reflejar en las fichas

- **RN07 · funcionalidades por plan.** Los reportes convencionales (CU-21, CU-22) los habilita `reportes_convencionales` y las funciones de IA (CU-23, CU-42 y CU-07, incluido el asistente que usa el cliente)
  las habilita `reportes_ia` (plan Profesional). Sin ella la respuesta es 403 con el mensaje de plan, y el menú muestra la opción bloqueada.
- **CU-21 · ventas netas.** Ventas netas = ventas pagadas (digitales y de caja) − valor devuelto + valor entregado en cambios (CU-41). Con filtro de canal, las devoluciones son las de las ventas de ese canal.
  Las prendas más y menos vendidas se miden netas de devoluciones. Periodo por defecto: últimos 30 días; máximo 366 días. Se puede exportar a CSV.
- **CU-21 · vista de pagos.** Sale de la tabla `pagos`: aprobados, rechazados y pendientes de confirmación (pagos con tarjeta cuya pasarela no respondió), con el detalle de los que tuvieron problemas.
- **CU-22 · indicadores.** Cada cifra (ventas netas, ventas, ticket promedio, reservas, conversión de reservas) se compara con el periodo anterior de la misma duración (7, 14, 30 o 90 días). Stock bajo = disponible
  igual o menor que el umbral mínimo de la sucursal (solo variantes con umbral definido).
- **CU-23 · IA externa con respaldo (regla 12).** Con `ANTHROPIC_API_KEY` la IA solo interpreta la petición y devuelve una especificación JSON que el servidor **valida** (campos permitidos, sucursal de la empresa,
  periodo máximo); si no hay clave, la API falla o la especificación no es válida, se usan reglas locales. Las cifras siempre salen de la base de datos, nunca de la IA. La voz usa la Web Speech API del navegador
  (se transcribe en el cliente y el texto se envía como cualquier petición). «Último mes» se interpreta como los últimos 30 días; «mes pasado» o «mes anterior», como el mes calendario anterior.
- **CU-23 · constancia.** Cada reporte generado queda registrado (petición, especificación, resultado y origen IA o reglas); el Administrador ve el historial de su empresa.
- **CU-42 · modelos.** Rotación por KMeans (3 grupos: ALTA, MEDIA, BAJA) sobre unidades vendidas en 30 días y relación con el stock; con menos de 3 productos distintos se usan umbrales fijos. Pronóstico por regresión
  lineal sobre las ventas semanales de las últimas 12 semanas, proyectado a 4 semanas, solo para productos con al menos 3 semanas con ventas. La recomendación compara la demanda proyectada con el stock (reponer,
  sobrestock o adecuado).
- **CU-36 · plan y uso.** Lo ve el Administrador aunque la suscripción haya vencido (RN05); en ese caso solo se muestran plan y vigencia. El único límite del plan es el de sucursales activas; usuarios, productos, ventas
  del mes y consultas de IA se muestran como consumo informativo. Se avisa cuando faltan 15 días o menos para el vencimiento y cuando se alcanza el límite de sucursales.
- **CU-07 · asistente.** Solo lo usa el Cliente. Entiende color, categoría, talla, rango de precios, género, ocasión, outfit y ofertas, usando también lo dicho antes en la conversación; busca con la misma búsqueda del
  catálogo (CU-04) y solo ofrece prendas con stock (de la sucursal elegida, si la hay). Si no hay resultados suelta filtros en orden (precio, talla, color, estilo) y lo avisa. El recomendador usa la categoría y el color
  que el cliente más compró y no repite lo que ya compró; si aún no compró, muestra lo más vendido.

- **CU-07 · perfil de gustos y privacidad.** El sistema aprende de lo que el cliente **compra** (peso 3), **busca** en el catálogo o le pide al asistente (2) y **mira** (1); lo reciente pesa más. Con ese perfil puntúa las
  prendas con stock (categoría, color, talla, precio, oferta) y recomienda con un motivo por prenda, muestra las ofertas que le convienen y arma outfits (prendas de otras categorías que combinan en tono). Con IA externa,
  la IA elige y explica; el servidor solo acepta prendas candidatas reales. Es un dato personal: el cliente puede **apagar** la personalización (se borra lo aprendido y deja de usarse incluso lo comprado) y **borrar** su historial
  en cualquier momento; se recuerdan solo las últimas 200 acciones.

### Mensajes nuevos

| CU | Situación | Mensaje | Código HTTP | Estado |
|---|---|---|---|---|
| CU-07 | Registrar una vista sin indicar la prenda | «Indique la prenda que miró.» | 422 | Pendiente |
| CU-07 | Prenda inexistente o de otra empresa | «Prenda no encontrada.» | 404 | Pendiente |
| CU-07 | Búsqueda sin ningún dato | «La búsqueda no tiene datos de los que aprender.» | 422 | Pendiente |
| CU-07 | Outfit con una prenda inexistente, sin stock o de otra empresa | «Prenda no encontrada o sin stock.» | 404 | Pendiente |
| CU-07 | «Recomiéndame algo» sin historial | «Todavía no conozco sus gustos, así que le muestro lo más vendido. Busque o mire prendas y aprenderé qué le gusta.» | 200 (respuesta del asistente) | Pendiente |
| CU-21 / CU-22 / CU-23 / CU-42 / CU-07 | El plan no incluye la funcionalidad | «Su plan no incluye esta funcionalidad. Cambie al plan Profesional.» | 403 | Ya existe (RN07) |
| CU-21 / CU-22 / CU-42 | Sucursal inexistente o de otra empresa | «Sucursal no encontrada.» | 404 | Pendiente |
| CU-21 | Fecha inicial posterior a la final | «La fecha inicial no puede ser posterior a la final.» | 422 | Pendiente |
| CU-21 | Periodo mayor a un año | «El periodo no puede superar 366 días.» | 422 | Pendiente |
| CU-21 | Tipo de exportación desconocido | «Tipo de exportación no soportado. Use ventas, reservas o pagos.» | 422 | Pendiente |
| CU-22 | Periodo distinto de 7, 14, 30 o 90 días | «El periodo debe ser de 7, 14, 30 o 90 días.» | 422 | Pendiente |
| CU-23 | Petición vacía | «Escriba o dicte lo que desea consultar.» | 422 | Pendiente |
| CU-23 | Reporte de otra empresa o inexistente | «Reporte no encontrado.» | 404 | Pendiente |
| CU-42 | Aún no hay ventas suficientes (menos de 3 semanas con ventas por producto) | «Todavía no hay ventas suficientes para pronosticar la demanda: se necesitan al menos 3 semanas con ventas de un producto.» | 200 (aviso) | Pendiente |
| CU-07 | Mensaje vacío o el último no es del cliente | «Escriba su consulta para el asistente.» | 422 | Pendiente |
| CU-07 | Sin prendas con esas características | «No encontré prendas disponibles con esas características. Pruebe con otro color, otra categoría o un precio mayor.» | 200 (respuesta del asistente) | Pendiente |

### Configuración nueva

`ANTHROPIC_API_KEY=` y, opcionalmente, `IA_MODELO=` en `backend/.env`: activan la interpretación con IA externa de CU-07 y CU-23. Sin ellas se usa el modo de respaldo con reglas locales. Nueva librería: `scikit-learn` (con `numpy`) en `requirements.txt`.

## Fase H

**CU-37, CU-38, CU-39 y CU-40 no tienen ficha ni prueba en el Word**; solo están sus reglas (RN11 a RN16), los requisitos RF18 a RF22 y los RNF03 a RNF06 y RNF10. Falta redactar las cuatro fichas. Las decisiones de abajo salen del código.

### Decisiones de diseño que conviene reflejar en las fichas

- **Qué se puede hacer sin conexión (RF19, RN13).** El personal de tienda (Cajero y Encargado) registra **ventas de contado** y el Cliente registra **reservas**. No hay ventas con tarjeta sin conexión: la pasarela necesita Internet.
  El efectivo recibido y el cambio se calculan en el dispositivo, pero eso no implica que el servidor haya aceptado la venta: se confirma al sincronizar.
- **Estados (RN11).** `REGISTRADA_LOCAL` y `ENVIADA` existen solo en el dispositivo; el servidor fija `CONFIRMADA`, `RECHAZADA` o `EN_CONFLICTO`. Una operación enviada **no se borra del dispositivo** hasta que el servidor
  la confirme o rechace (RN12); si no hay respuesta, vuelve a `REGISTRADA_LOCAL` y se reintenta (al volver la conexión y cada 30 segundos). Una operación en conflicto tampoco se borra.
- **Idempotencia (RN12, RNF05).** El identificador (UUID) lo genera el dispositivo. El servidor guarda (empresa, identificador) como único: reenviar una operación ya procesada devuelve su resultado original sin duplicarla,
  también si llegan dos envíos a la vez o el mismo identificador dos veces en un lote. Un identificador ya usado por otro usuario se rechaza sin tocar la operación original.
- **Una sola transacción (RNF04).** La operación y todos sus efectos (venta, cobro, descuento de inventario, comprobante o reserva) se confirman juntos o no se confirma nada. Si el servidor falla por un problema pasajero, la operación
  **no se guarda** y el dispositivo la reintenta (RNF06).
- **Orden.** Las operaciones de un lote se aplican en el orden en que ocurrieron en el dispositivo; si queda una sola unidad, es de la operación más antigua.
- **Conflictos (RN14, RF22).** Si al sincronizar no alcanzan las existencias, no se descuenta nada (ni de las prendas que sí alcanzaban) y la operación queda `EN_CONFLICTO` con las prendas que faltan (pedidas y disponibles hoy);
  se avisa a la sucursal (RF11). El Encargado (de su sucursal) o el Administrador la resuelve: **reintentar** (con las existencias de ahora; si ya alcanzan, queda confirmada) o **descartar** con un motivo (en una venta de contado se indica
  devolver el efectivo al cliente). Una sucursal con conflictos sin resolver no se puede desactivar (CU-14, excepción 5).
- **Rechazos.** Se rechaza, con el mensaje de la regla, lo que ya no se puede aplicar por otro motivo: monto recibido menor al total (los precios pudieron cambiar), prenda que ya no está en el catálogo, reserva con horario ya pasado,
  formato inválido, sucursal ajena (RN10) o un rol que no puede registrar ese tipo de operación.
- **Catálogo offline (RF18, RN16).** La descarga trae productos activos con variantes, precio con promoción vigente y stock; el personal recibe solo el stock de su sucursal (RN10) y los datos mínimos de los clientes (nombre y correo);
  el cliente recibe el stock de todas las sucursales activas (para elegir dónde reservar) y ningún dato de otros clientes. Siempre se muestra la fecha de la descarga y se avisa que puede estar desactualizada (más de un día o sin conexión).
- **Plan y suscripción.** La sincronización y la descarga exigen que el plan incluya la operación offline (ambos planes, RN07) y que la suscripción esté vigente (RN05). El Administrador no registra operaciones offline: solo gestiona conflictos.
- **Observabilidad (RNF10).** Cada operación procesada deja un registro con su identificador, tipo, estado, empresa y sucursal; no se escriben los datos de la venta ni de los clientes en el registro de diagnóstico.
- **Móvil.** Flutter con SQLite (`sesion`, `sucursales_autorizadas`, `productos_locales`, `clientes_locales`, `operaciones_pendientes` y `meta`). Si no hay conexión, el catálogo del cliente usa el catálogo descargado. El pago con tarjeta de la compra digital
  en el móvil solo está disponible con la pasarela de pruebas; con Stripe se termina en la web.

### Mensajes nuevos

| CU | Situación | Mensaje | Código HTTP | Estado |
|---|---|---|---|---|
| CU-38 | Operación confirmada | «Operación confirmada.» | 200 (estado CONFIRMADA) | Pendiente |
| CU-38 | Rol que no puede registrar ese tipo de operación | «No tiene permisos para registrar este tipo de operación sin conexión.» | 200 (estado RECHAZADA) | Pendiente |
| CU-38 | Operación de otra sucursal (RN10) | «La operación corresponde a otra sucursal.» | 200 (estado RECHAZADA) | Pendiente |
| CU-38 | Sucursal inexistente o de otra empresa | «Sucursal no encontrada.» | 200 (estado RECHAZADA) | Pendiente |
| CU-38 | Identificador usado por otro usuario | «Este identificador de operación ya fue utilizado por otro usuario.» | 200 (estado RECHAZADA) | Pendiente |
| CU-38 | Operación con formato inválido | «La operación no tiene el formato esperado.» | 200 (estado RECHAZADA) | Pendiente |
| CU-38 | Faltan existencias (RN14) | «No hay existencias suficientes para esta operación. No se descontó nada del inventario; el Encargado debe resolverla.» | 200 (estado EN_CONFLICTO) | Pendiente |
| CU-38 | Falla pasajera del servidor | «El servidor no pudo procesar la operación ahora. Se conserva en el dispositivo y se reintentará.» | 200 (estado ERROR; el dispositivo la reintenta) | Pendiente |
| CU-38 | Monto recibido menor al total / prenda no disponible / horario inválido | Los mismos de CU-30, CU-29 y CU-09 | 200 (estado RECHAZADA) | Ya están en CU-09, CU-29 y CU-30 |
| CU-40 | Operación inexistente, de otra sucursal u otra empresa | «Operación no encontrada.» | 404 | Pendiente |
| CU-40 | La operación ya no está en conflicto | «La operación ya no está en conflicto.» | 409 | Pendiente |
| CU-40 | Descartar sin motivo | «Indique el motivo del descarte.» | 422 | Pendiente |
| CU-40 | Reintentar y todavía no alcanzan | «Todavía no hay existencias suficientes: {prenda} ({talla}, {color}): solicitadas {n}, disponibles {d}.» | 409 | Pendiente |
| CU-40 | Reintentar una operación de un usuario que ya no está activo | «El usuario que registró la operación ya no está activo: descártela.» | 409 | Pendiente |
| CU-37 / CU-38 / CU-39 / CU-40 | El plan no incluye la operación offline | «Su plan no incluye esta funcionalidad. Cambie al plan Profesional.» | 403 | Ya existe (RN07) |

### Reglas de la sucursal

CU-14 ya decía que no se puede desactivar una sucursal con «operaciones sin sincronizar»: ahora lo cumplen las operaciones en conflicto (mensaje existente: «La sucursal tiene reservas pendientes u operaciones sin sincronizar. Resuélvalas antes de desactivarla.»).

## Fase J · Bitácora del sistema

La bitácora **no es un caso de uso**: es una función transversal, como el aislamiento por empresa (RNF02). Conviene mencionarla en la arquitectura y en la trazabilidad, no como CU. Las decisiones salen del código.

### Decisiones de diseño que conviene reflejar en el documento

- **Qué se registra.** Cada inicio y cierre de sesión, cada intento de ingreso fallido (con el correo y la empresa que se intentaron, **sin** la contraseña) y toda operación de escritura (alta, modificación, eliminación, aprobación, cancelación, pago,
  cobro, devolución, sincronización...) terminada con éxito por un usuario con sesión. Las consultas no se registran. Lo que falla (validaciones, conflictos, errores) tampoco: no es una operación realizada.
- **Qué se guarda.** Quién (usuario con el nombre que tenía en ese momento, rol y empresa), acción, entidad, un detalle en español legible (por ejemplo «Registró la sucursal Centro») y la IP (con proxy, la de `X-Forwarded-For`).
  **Nunca** contraseñas, tokens ni datos de tarjeta: el detalle solo usa los campos que nombra la tabla de etiquetas.
- **Cómo se registra.** Sin tocar cada caso de uso: un middleware lee la sesión y una tabla de etiquetas (ruta → acción y entidad) arma el detalle; una ruta sin etiqueta se registra con un texto genérico. Al agregar un endpoint de escritura se agrega su
  etiqueta (regla 16) y una prueba falla si falta. Un fallo al registrar nunca deshace ni rompe la operación.
- **Solo se agrega.** No existe ningún endpoint para editar o borrar, y un disparador de la base de datos impide `UPDATE` y `DELETE` incluso con acceso directo a la tabla. Las operaciones de inventario siguen en su propia bitácora (`movimientos_inventario`).
- **Quién la ve (RN02, RN04).** El Administrador, solo la de su empresa (el `empresa_id` sale del token); el SuperAdministrador, la de todas las empresas con filtro por empresa y columna Empresa, más sus operaciones de plataforma (planes, empresas).
  Una operación del SuperAdministrador sobre una empresa (suspenderla, asignarle un plan) se guarda con el `empresa_id` de esa empresa, así el Administrador de la empresa la ve. Encargado, Cajero y Cliente no tienen acceso. Con la suscripción vencida (RN05), el Administrador no ve
  la bitácora (solo su plan).
- **Cierre de sesión.** Los tokens no tienen estado en el servidor: al cerrar sesión, la web y el móvil avisan a `POST /auth/logout` (si no hay conexión, igual cierran la sesión local) y queda el registro.
- **Pantalla.** «Bitácora» con el total de registros, filtros por usuario, entidad, acción, rango de fechas (el «hasta» incluye todo el día) y búsqueda en el detalle o la IP; tabla paginada de la más reciente a la más antigua, con la acción como etiqueta de color
  (verde: inicio de sesión; gris: cierre; rojo: intentos fallidos, cancelaciones y eliminaciones; azul: altas; ámbar: modificaciones y ajustes; morado: pagos, cobros y devoluciones).

### Mensajes nuevos

| Situación | Mensaje | Código HTTP | Estado |
|---|---|---|---|
| Cierre de sesión | «Sesión cerrada.» | 200 | Pendiente |
| Página o tamaño de página inválidos en la consulta | «La página y el tamaño deben ser números positivos (tamaño máximo 100).» | 422 | Pendiente |
| Encargado, Cajero o Cliente consultan la bitácora; el Administrador consulta la general | «No tiene permisos para esta operación.» | 403 | Ya existe |
| El SuperAdministrador consulta la de una empresa | «Esta operación pertenece a una empresa.» | 403 | Ya existe |
| Cualquier intento de modificar o borrar un registro | (no existe la ruta) 405; en la base: «La bitácora no se puede modificar ni borrar.» | 405 | Pendiente |

### Para el Word

Agregar la tabla `bitacora` al modelo de datos (con su disparador de inmutabilidad), la función transversal a la arquitectura y a la tabla de trazabilidad (sin CU), y la regla de que la bitácora la ve cada Administrador solo de su empresa (RN02) y el SuperAdministrador de todas.

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

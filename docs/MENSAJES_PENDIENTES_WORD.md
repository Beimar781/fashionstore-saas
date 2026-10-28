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

*(Se completa al terminar la fase: mensajes y reglas de CU-08, CU-11, CU-12 y CU-32 que no estén en el Anexo B.)*

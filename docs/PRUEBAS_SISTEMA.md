# Guía de pruebas del sistema (web + móvil)

Lista de verificación para probar FashionStore completo, con la web y el APK a la vez, contra el despliegue real.

- **Web:** <https://frontend-production-13a8.up.railway.app> · **API:** <https://fashionstore-saas-production.up.railway.app> (`/docs`, `/salud`).
- **Móvil:** APK compilado con «Compilar APK» (ver `docs/DESPLIEGUE.md`, apartado 3.6).
- **Cuentas:** el código de empresa va en el primer campo (el SuperAdmin lo deja vacío). Las contraseñas están en `backend/app/seed.py`.

| Rol | Empresa | Correo |
|---|---|---|
| SuperAdmin | (vacío) | `superadmin@fashionstore.com` |
| Administrador | EMP-A | `admin@modaurbana.com` |
| Cliente | EMP-A | `cliente@emp-a.com` |
| Administrador | EMP-B | `admin@estiloandino.com` |
| Cliente | EMP-B | `cliente@emp-b.com` |

**Tarjetas de prueba de Stripe** (cualquier fecha futura y cualquier CVC; sirven igual en la web y en el móvil):

| Tarjeta | Resultado |
|---|---|
| `4242 4242 4242 4242` | Aprueba |
| `4000 0000 0000 0002` | Rechaza (tarjeta declinada por el banco) |
| `4000 0027 6000 3184` | Pide autenticación 3D Secure: al completarla aprueba; si se rechaza o se abandona, no se cobra |

**Antes de empezar**, corre la prueba de humo (revisa salud, inicios de sesión, catálogo, pagos, asistente de EMP-A y de EMP-B):

```
python scripts/humo_produccion.py https://fashionstore-saas-production.up.railway.app
```

Debe terminar con todas las líneas en ✔. Si el asistente de EMP-B marca ✘ (origen `REGLAS`), la IA está en modo de respaldo: mira los registros del backend en Railway, donde queda el tipo de error (por ejemplo `ReadTimeout` o el código HTTP de Gemini).

Marca cada fila cuando el resultado real coincida con el esperado.

## 1. Login y recuperación de contraseña (correo real)

| # | Dónde | Cuenta | Pasos | Resultado esperado | ✔ |
|---|---|---|---|---|---|
| 1.1 | Web | Cliente EMP-A | Iniciar sesión con código `EMP-A`, correo y contraseña. | Entra a la tienda de EMP-A. | ☐ |
| 1.2 | Web | Cliente EMP-A | Probar el ojito de mostrar/ocultar contraseña. | La contraseña se muestra y se oculta. | ☐ |
| 1.3 | Web | Cualquiera | Contraseña equivocada. | Mensaje de credenciales incorrectas; no entra. | ☐ |
| 1.4 | Web | Un correo propio con cuenta | «¿Olvidó su contraseña?», escribir código y correo. | Mensaje genérico de «si los datos son correctos recibirá un correo». Llega el correo de Brevo con el enlace. | ☐ |
| 1.5 | Web | Ídem | Abrir el enlace y definir una contraseña nueva. | «Contraseña restablecida»; el enlace ya no sirve una segunda vez. | ☐ |
| 1.6 | Móvil | Cliente EMP-A | Iniciar sesión; probar mostrar/ocultar contraseña. | Entra; el ojito funciona. | ☐ |
| 1.7 | Móvil | Ídem | En el login, escribir código y correo y tocar «¿Olvidó su contraseña?». | Aviso con el mensaje genérico del servidor; llega el correo con el enlace (que abre la web). | ☐ |
| 1.8 | Móvil | Ninguna | En el login tocar «¿No tiene cuenta? Crear cuenta»; escribir `EMP-A`, nombre, apellidos, un correo nuevo y una contraseña de 8 o más caracteres. | La app vuelve al login con el código y el correo escritos y el aviso «Cuenta creada. Ingrese con su contraseña.»; se puede ingresar. | ☐ |
| 1.9 | Móvil | Ninguna | Crear cuenta con una contraseña de menos de 8 caracteres y con un correo ya usado. | «La contraseña debe tener al menos 8 caracteres.» y «Este correo ya está en uso.» | ☐ |

## 2. Catálogo por empresa

| # | Dónde | Cuenta | Pasos | Resultado esperado | ✔ |
|---|---|---|---|---|---|
| 2.1 | Web | Cliente EMP-A | Abrir el catálogo. | Solo prendas de EMP-A. **Sin** asistente de IA en el menú. | ☐ |
| 2.2 | Web | Cliente EMP-B | Abrir el catálogo. | Solo prendas de EMP-B. **Con** asistente de IA. | ☐ |
| 2.3 | Móvil | Cliente EMP-A y luego EMP-B | Abrir el catálogo en cada una. | Cada empresa ve únicamente su catálogo. | ☐ |

## 3. Asistente de IA

| # | Dónde | Cuenta | Pasos | Resultado esperado | ✔ |
|---|---|---|---|---|---|
| 3.1 | Web | Cliente EMP-B | Pedir «una camisa para el trabajo». | Respuesta con prendas reales de EMP-B; el origen es `IA` (la API lo devuelve en `origen`). | ☐ |
| 3.2 | Web | Cliente EMP-A | Llamar al asistente (con la API `/docs` o la pantalla, si se ve). | **403** «Su plan no incluye esta funcionalidad. Cambie al plan Profesional.» | ☐ |
| 3.3 | Web | Cliente EMP-B | Si la IA falla (clave o límite), repetir el pedido. | Responde igual con reglas locales (origen `REGLAS`); el motivo queda en el registro del backend. | ☐ |
| 3.4 | Móvil | Cliente EMP-B (plan Profesional) | En el inicio aparece «Asistente de compras». Pedir «una camisa para el trabajo»; tocar una prenda sugerida y un botón de sugerencia; elegir una sucursal. | Burbujas de conversación, prendas con su precio que abren la ficha de la prenda y sugerencias que envían otra consulta. | ☐ |
| 3.5 | Móvil | Cliente EMP-A (plan Básico) | Mirar el inicio. | **No** aparece «Asistente de compras». | ☐ |
| 3.6 | Móvil | Cliente EMP-B | Con modo avión, pedir algo al asistente. | «Sin conexión: el asistente necesita Internet.» | ☐ |

## 4. Vestidor virtual

| # | Dónde | Cuenta | Pasos | Resultado esperado | ✔ |
|---|---|---|---|---|---|
| 4.1 | Móvil | Cliente | Abrir una camiseta → Vestidor; aceptar el permiso de cámara. | La prenda se dibuja sobre los hombros y sigue el movimiento. | ☐ |
| 4.2 | Móvil | Cliente | Negar el permiso de cámara. | Mensaje explicando cómo permitirla en Ajustes. | ☐ |
| 4.3 | Móvil | Cliente | **Mantener presionado el título** del vestidor. | Aparece el contador «FPS: n · promedio: n». Anotar el promedio para el Word. Otra pulsación larga lo oculta. | ☐ |
| 4.4 | Móvil | Cliente | Cambiar de color y de talla. | La prenda cambia sin cerrar la cámara. | ☐ |

## 5. Carrito y compra con tarjeta de prueba

| # | Dónde | Cuenta | Pasos | Resultado esperado | ✔ |
|---|---|---|---|---|---|
| 5.1 | Web | Cliente EMP-A | Agregar una prenda al carrito, elegir retiro en tienda y pagar con `4242 4242 4242 4242`. | Pago aprobado; se muestra el comprobante `CMP-<sucursal>-<número>`; el stock baja. | ☐ |
| 5.2 | Web | Cliente EMP-A | Repetir con `4000 0000 0000 9995`. | «Transacción denegada por su banco»; no se cobra ni baja el stock. | ☐ |
| 5.3 | Móvil | Cliente EMP-A | Agregar al carrito y tocar «Pagar con tarjeta». Se abre la hoja de pago de Stripe: escribir `4242 4242 4242 4242`, fecha futura y CVC. | La hoja se cierra y la app muestra «✔ Pago aprobado» con la marca, los últimos 4 dígitos y el N.° de comprobante. En «Mis compras» el pedido figura como pagado. | ☐ |
| 5.4 | Móvil | Cliente EMP-A | Repetir con `4000 0000 0000 0002`. | La hoja de Stripe muestra que la tarjeta fue rechazada y permite reintentar; al cerrarla, la app dice que el pedido quedó pendiente de pago. No se cobra ni baja el stock. | ☐ |
| 5.5 | Móvil | Cliente EMP-A | Repetir con `4000 0027 6000 3184` y completar la autenticación 3D Secure. | Pide la autenticación; al completarla, «✔ Pago aprobado». Si se rechaza la autenticación, no se cobra. | ☐ |
| 5.6 | Móvil | Cliente EMP-A | Abrir la hoja de pago y cerrarla sin pagar. | «El pedido … quedó pendiente de pago.» Sin mensaje de error ni cobro. | ☐ |
| 5.7 | Móvil | Cliente EMP-A | Al tocar «Pagar con tarjeta» se abre «Entrega, facturación y pago». Dejar el NIT vacío y tocar «Continuar al pago». | «Ingrese su NIT o CI para la facturación.» | ☐ |
| 5.8 | Móvil | Cliente EMP-A | Elegir «A domicilio» sin dirección y con NIT `1234567`. | «Ingrese la dirección de entrega.» | ☐ |
| 5.9 | Móvil | Cliente EMP-A | Elegir «A domicilio», escribir la dirección, NIT `1234567` y razón social, y pagar con `4242 4242 4242 4242`. | Pago aprobado; en la web, la compra figura con entrega a domicilio, esa dirección y esos datos de facturación. | ☐ |
| 5.10 | Web | Cliente EMP-A | En el pago con tarjeta, marcar «Guardar esta tarjeta para mis próximas compras» y pagar con `4242 4242 4242 4242`. | Pago aprobado. En la siguiente compra aparece «Visa terminada en 4242» entre las tarjetas guardadas. | ☐ |
| 5.11 | Móvil | Cliente EMP-A | En «Entrega, facturación y pago», dejar «Usar otra tarjeta» con «Guardar esta tarjeta para mis próximas compras» marcado y pagar con `4242 4242 4242 4242` en la hoja de Stripe. | Pago aprobado. En la siguiente compra, en esa misma pantalla, aparece «Visa terminada en 4242 · vence …» y la tarjeta guardada en la web (5.10) también está. | ☐ |
| 5.12 | Móvil | Cliente EMP-A | Elegir la tarjeta guardada y tocar «Continuar al pago». | No se pide la tarjeta de nuevo: Stripe confirma directamente y la app muestra «✔ Pago aprobado». | ☐ |
| 5.13 | Móvil | Cliente EMP-A | Tocar el ícono de eliminar junto a una tarjeta guardada. | La tarjeta desaparece de la lista y también de la web. | ☐ |

## 6. Comprobante PDF

| # | Dónde | Cuenta | Pasos | Resultado esperado | ✔ |
|---|---|---|---|---|---|
| 6.1 | Web | Cliente EMP-A | «Mis compras» → la compra de 5.1 → descargar comprobante. | PDF con el número `CMP-…`, las prendas, el IVA y el total. | ☐ |
| 6.2 | Móvil | Cliente EMP-A | «Mis compras» → ver el detalle. | Muestra el número de comprobante de la compra. | ☐ |
| 6.3 | Móvil | Cliente EMP-A | Tras un pago aprobado, tocar «Ver comprobante» en el resultado. | El botón muestra «Descargando…» y no se puede tocar dos veces; se abre el PDF en el visor del teléfono (desde ahí se comparte o se guarda). | ☐ |
| 6.4 | Móvil | Cliente EMP-A | «Mis compras» → «Ver comprobante» de una compra pagada. | Se abre el mismo PDF. Las compras sin pagar no tienen el botón. | ☐ |
| 6.5 | Móvil | Cliente EMP-A | Con modo avión, tocar «Ver comprobante». | «Sin conexión: no se puede descargar el comprobante. Inténtelo de nuevo cuando tenga red.» La app no se cierra. | ☐ |
| 6.6 | Móvil | Cliente EMP-A | En un teléfono sin visor de PDF, tocar «Ver comprobante». | «No hay una aplicación para abrir PDF en este teléfono.» | ☐ |

## 7. Reservas

| # | Dónde | Cuenta | Pasos | Resultado esperado | ✔ |
|---|---|---|---|---|---|
| 7.1 | Web | Cliente EMP-A | Reservar una prenda en una sucursal. | Reserva creada; el stock disponible baja. | ☐ |
| 7.2 | Móvil | Cliente EMP-A | «Mis reservas» → cancelar la reserva. | La reserva se cancela y el stock se libera. | ☐ |
| 7.3 | Móvil | Cliente EMP-A | En el catálogo, abrir una prenda y tocar el marcador «Agregar a mi reserva» de una talla y color con stock (junto al carrito). | Mensaje de que la prenda se agregó a su reserva. | ☐ |
| 7.4 | Móvil | Cliente EMP-A | «Mis reservas» → botón «Mi reserva (n)». Elegir sucursal, día y hora, y «Confirmar reserva». | «Reserva … confirmada. Presente ese código en la tienda.»; la reserva aparece en «Mis reservas» y el stock se aparta. | ☐ |
| 7.5 | Móvil | Cliente EMP-A | En «Mis reservas», cancelar una reserva. | Pide un motivo opcional (hasta 200 caracteres); al confirmar, la reserva queda cancelada. | ☐ |

## 8. Devolución y aviso push al cliente

| # | Dónde | Cuenta | Pasos | Resultado esperado | ✔ |
|---|---|---|---|---|---|
| 8.1 | Web | Administrador EMP-A | Registrar la devolución (o el cambio) de la compra de 5.1. | Devolución registrada; reembolso a la tarjeta de prueba; el stock vuelve. | ☐ |
| 8.2 | Web | Cliente EMP-A | Estar con la sesión abierta y permiso de notificaciones. | Llega la notificación push del navegador y se enciende la campana. | ☐ |
| 8.3 | Móvil | Cliente EMP-A | Con el APK instalado e iniciada la sesión (permiso aceptado). | Llega la notificación nativa de Android; con la app abierta aparece el aviso y la campana. | ☐ |
| 8.4 | Móvil | Cliente EMP-A | Negar el permiso de notificaciones y repetir 8.1. | No hay notificación del sistema, pero el aviso aparece dentro de la app (campana). | ☐ |

## 9. Compra offline y conflicto

| # | Dónde | Cuenta | Pasos | Resultado esperado | ✔ |
|---|---|---|---|---|---|
| 9.1 | Móvil | Cliente EMP-B | Descargar el catálogo con conexión; activar modo avión; registrar una compra. | Queda `REGISTRADA_LOCAL` (RN11) y el stock local baja. | ☐ |
| 9.2 | Móvil | Ídem | Desactivar el modo avión y sincronizar. | Pasa a `ENVIADA` y luego `CONFIRMADA`; una segunda sincronización no la duplica (RNF05). | ☐ |
| 9.3 | Móvil + Web | Ídem + Administrador EMP-B | Con la red apagada, registrar una compra de la última unidad; mientras tanto, vender esa unidad desde la web; reconectar. | La operación queda `EN_CONFLICTO` («la prenda se agotó, no se le cobró nada»), llega el aviso push y el Encargado la ve para resolverla. | ☐ |

## 10. Bitácora y panel del SuperAdmin

| # | Dónde | Cuenta | Pasos | Resultado esperado | ✔ |
|---|---|---|---|---|---|
| 10.1 | Web | Administrador EMP-A | Abrir la bitácora. | Aparecen los inicios de sesión, la venta y la devolución de las pruebas anteriores, solo de EMP-A. Sin contraseñas ni datos de tarjeta. | ☐ |
| 10.2 | Web | SuperAdmin | Abrir el panel y la bitácora general. | Ve las dos empresas, sus planes y suscripciones, y la bitácora de toda la plataforma. | ☐ |
| 10.3 | Web | Administrador EMP-A | Intentar abrir una ruta de la plataforma (`/api/plataforma/empresas`). | **403**: solo el SuperAdmin entra. | ☐ |

## 11. Navegación y catálogo del móvil

| # | Dónde | Cuenta | Pasos | Resultado esperado | ✔ |
|---|---|---|---|---|---|
| 11.1 | Móvil | Cliente EMP-B | Abrir Inicio y cambiar entre Inicio, Promociones, Reservas, Compras y Perfil. | La barra inferior conserva la pestaña elegida y las listas no vuelven al principio al cambiar. La campana y el carrito están arriba a la derecha; sus globos desaparecen cuando el conteo es cero. | ☐ |
| 11.2 | Móvil | Cliente EMP-B | En Inicio, cambiar sucursal, buscar texto, filtrar una categoría y tocar una prenda. | Se muestran fotos y una rejilla de dos columnas; el detalle abre la prenda y las acciones fijas quedan visibles debajo. La sucursal elegida se recuerda al volver a abrir la app. | ☐ |
| 11.3 | Móvil | Cliente EMP-B | Abrir Promociones y tocar una tarjeta del carrusel. | Solo se muestran prendas con promoción; el carrusel avanza cada cinco segundos y abre el detalle. | ☐ |
| 11.4 | Móvil | Cliente EMP-B | Tocar la campana, marcar un aviso como leído y luego «Marcar todos». | Se muestra «Avisos» y el número de avisos pendientes se actualiza. | ☐ |
| 11.5 | Móvil | Cliente EMP-A | Iniciar sesión con suscripción restringida. | Solo aparece Perfil para consultar el plan; no se muestran pestañas del catálogo ni el asistente. | ☐ |
| 11.6 | Móvil | Cliente EMP-B | Descargar el catálogo desde Perfil → Modo sin conexión, abrir Inicio y activar modo avión. | La franja indica «Sin conexión · Datos al …» y se conservan las fotos descargadas, incluso las que no se habían abierto antes. | ☐ |
| 11.7 | Móvil | Cliente EMP-B | En Android, probar el inicio, carrito, entrega y vestidor tanto con navegación por gestos como con tres botones. | El contenido final y los selectores de color y talla quedan por encima de la barra del sistema; el video no queda oculto bajo la barra de gestos. | ☐ |

## 12. Vestidor virtual también en la web

| # | Dónde | Cuenta | Pasos | Resultado esperado | ✓ |
|---|---|---|---|---|---|
| 12.1 | Web (Chrome y Edge) | Cliente con prenda lista | Abrir el detalle de una prenda admitida, entrar al vestidor, permitir la cámara y probar varios colores y tallas. | La guía aparece, la prenda sigue hombros y cadera, la talla modifica su escala, la foto se descarga como PNG y se agrega al carrito la variante elegida. El video se procesa localmente. | ☐ |
| 12.2 | Web (Chrome y Edge) | Cliente | Denegar el permiso de cámara e intentar abrirla otra vez permitiendo el acceso. | Se muestra «Permita el acceso a la cámara para usar el vestidor.»; al permitirlo el vestidor funciona. Al ocultar la pestaña se detiene la cámara. | ☐ |
| 12.3 | Web instalada como PWA | Cliente | Con conexión, descargar el catálogo; esperar a que estén disponibles los recursos de MediaPipe; desconectar Internet y abrir un producto admitido del catálogo descargado. | El vestidor carga el modelo local y los PNG guardados, y permite probarse la prenda sin enviar video. Si falta un recurso descargado se informa «Descargue el catálogo con conexión para usar el vestidor sin Internet.». | ☐ |
| 12.4 | Móvil Android | Cliente | Repetir el flujo móvil existente con una prenda y color listos. | La cámara y el ajuste de la prenda en móvil se mantienen sin cambios. | ☐ |

## 13. Funciones del Cliente con y sin conexión (Prompt Q)

Web: DevTools → Network → **Offline** (o desconectar el Wi‑Fi). Móvil: **modo avión**. Antes de cortar la red, iniciar sesión con el Cliente, abrir «Modo sin conexión» y tocar «Descargar catálogo»; abrir una vez un comprobante y la lista de compras.

| # | Dónde | Pasos | Resultado esperado | ✔ |
|---|---|---|---|---|
| 13.1 | Web y móvil | Con sesión abierta, cortar la red y abrir la app (cerrarla y volverla a abrir). | Entra directo con el nombre, la empresa y el plan guardados. Al volver la red no pide iniciar sesión otra vez. | ☐ |
| 13.2 | Web y móvil | Sin red y **sin sesión**: escribir los datos en iniciar sesión, crear cuenta y recuperar contraseña. | «Sin conexión: necesita Internet para iniciar sesión / crear su cuenta / recuperar su contraseña.» y el formulario conserva lo escrito. | ☐ |
| 13.3 | Web y móvil | Sin red, abrir el catálogo, filtrar, ver el detalle y las promociones. | Se ve lo descargado con «Datos al …»; las fotos ya vistas o precargadas se ven. | ☐ |
| 13.4 | Web y móvil | Sin red, abrir el vestidor de una prenda descargada. | Funciona con el modelo local y el PNG guardado. Sin catálogo descargado: «Descargue el catálogo con conexión para usar el vestidor sin Internet.» | ☐ |
| 13.5 | Web y móvil | Sin red, usar el asistente (plan Profesional). | Responde con «Respuesta local, sin IA (sin conexión)» sobre el catálogo descargado. Con plan Básico no aparece. | ☐ |
| 13.6 | Web y móvil | Sin red, agregar prendas al carrito y reiniciar la app. | El carrito se conserva. Con red, se fusiona con el del servidor sin duplicar; una prenda agotada se avisa y se quita. | ☐ |
| 13.7 | Web y móvil | Sin red, «Finalizar compra» con retiro, y otra con domicilio sin dirección, y con NIT vacío. | Pide los mismos datos que en línea con los mismos mensajes; la compra queda `REGISTRADA_LOCAL`. | ☐ |
| 13.8 | Web y móvil | Volver la red. | La compra se sincroniza sola (`ENVIADA` → `CONFIRMADA`), llega el aviso y aparece «por pagar» en «Mis compras»; desde ahí se paga con Stripe. | ☐ |
| 13.9 | Web y móvil | Sin red, abrir «Mis compras». | La última lista vista más las operaciones pendientes con la etiqueta «Pendiente de sincronizar». | ☐ |
| 13.10 | Web y móvil | Sin red, abrir un comprobante ya visto y otro nunca abierto. | El visto se abre. El otro: «Sin conexión: este comprobante todavía no se descargó. Ábralo una vez con Internet para tenerlo disponible sin conexión.» | ☐ |
| 13.11 | Web y móvil | Sin red, «Agregar a mi reserva» → «Mi reserva» → confirmar. | La reserva queda en la cola y en «Mis reservas» como pendiente; al volver la red se confirma. | ☐ |
| 13.12 | Web y móvil | Sin red, cancelar una reserva ya confirmada (con motivo) y otra que aún no se sincronizó. | La primera queda como `CANCELAR_RESERVA` pendiente y al sincronizar se cancela (o queda `RECHAZADA` con mensaje si ya fue atendida o cancelada). La segunda solo desaparece de la cola. | ☐ |
| 13.13 | Web y móvil | Sin red, abrir los avisos y marcar uno como leído. | Se ven los últimos avisos guardados; al volver la red se envía la lectura y el contador se actualiza. | ☐ |
| 13.14 | Web y móvil | Sin red, abrir «Tarjetas guardadas» o pagar con tarjeta. | «Sin conexión: las tarjetas guardadas necesitan Internet.» y no se cobra nada. | ☐ |
| 13.15 | Web y móvil | Con operaciones pendientes, mirar el aviso y el contador. | Franja «Sin conexión» y contador de pendientes visibles (en la web, en el menú y la franja del layout). Al volver la red se sincroniza sola; también hay botón manual. | ☐ |
| 13.16 | Web | Compilar en producción, servir `dist` en local, cargar una vez con red, cortar la red y recorrer las pantallas del Cliente. | Todas abren sin red desde el Service Worker (shell y rutas del Cliente). | ☐ |

## 14. Cierre del enunciado (Prompt R)

| # | Dónde | Cuenta | Pasos | Resultado esperado | ✔ |
|---|---|---|---|---|---|
| 14.1 | Web | Administrador EMP-B | «Reportes con IA»: pedir «los productos más vendidos de este mes y las ventas». Tocar «Descargar Excel» y «Descargar PDF». | Se descargan `reporte-N.xlsx` y `reporte-N.pdf` con la empresa, el periodo, las tablas y el pie «Generado por FashionStore»; el Excel trae un gráfico. | ☐ |
| 14.2 | Web | Administrador EMP-A (plan Básico) | Intentar exportar un reporte con IA. | 403 «Su plan no incluye esta funcionalidad. Cambie al plan Profesional.» | ☐ |
| 14.3 | Web | Administrador | «Reportes» → pestaña «Inventario»; filtrar por sucursal; botones Excel, PDF y CSV. | Tabla paginada con bajo stock y agotados; los tres archivos descargan el mismo contenido. | ☐ |
| 14.4 | Web | SuperAdministrador o equipo | En el servidor: `python -m app.demo_historial` y luego pedir «ventas de los últimos tres meses por sucursal». | El reporte trae ventas de EMP-A y EMP-B de 3 meses; correrlo otra vez no agrega nada. | ☐ |
| 14.5 | Web | Cualquiera | Chrome: aparece «⬇ Instalar aplicación»; instalarla. Ya instalada, el botón desaparece. | La app se abre en su propia ventana. | ☐ |
| 14.6 | Web | Cualquiera | Con la app cargada, cortar la red y abrir una ruta que nunca se visitó. | Página «Sin conexión» con los botones «Ir al inicio» y «Reintentar». | ☐ |
| 14.7 | Móvil | Cajero | Con modo avión, registrar una venta de contado. Abrir «Modo sin conexión» → Operaciones → «Comprobante provisional». | Se abre un PDF con `LOC-<sucursal>-<código>`, el detalle, el efectivo y el cambio, y «Válido una vez sincronizada la venta». | ☐ |
| 14.8 | Móvil y web | Cajero | «Resumen de mi turno» (icono del recibo en el móvil; pestaña «Mi turno» en la web). | Cantidad de ventas, efectivo, cambio y el desglose por estado; en el móvil, «Descargar PDF». | ☐ |
| 14.9 | Móvil y web | Cajero | Registrar una venta sin conexión y, antes de sincronizar, cambiar el precio de la prenda en la web. Volver la red. | La venta queda EN_CONFLICTO: «El precio de una prenda cambió desde que se registró la venta.» El Encargado la reintenta y se confirma con el precio actual. | ☐ |
| 14.10 | Móvil | Cajero | Poner el reloj del teléfono 20 minutos adelantado y sincronizar. | Aviso «La hora de este dispositivo parece incorrecta; revísela para que sus ventas queden con la fecha correcta.» | ☐ |
| 14.11 | Web y móvil | Cualquiera | Activar «Simular sin conexión» (Perfil en el móvil; menú lateral en la web) con Internet encendido. | Franja «Modo sin conexión simulado»; las operaciones quedan pendientes. Al apagar el interruptor se sincronizan solas. | ☐ |
| 14.12 | Web y móvil | Cliente | Cerrar sesión con operaciones pendientes. | «Tiene N operaciones sin sincronizar. Se conservarán en este dispositivo.» Al volver a entrar el mismo usuario, siguen ahí; otro usuario del mismo dispositivo no las ve. | ☐ |
| 14.13 | Web y móvil | Cualquiera | Ver «Registro de sincronización» y «Copiar diagnóstico». | Una fila por intento con resultado y código; el texto copiado no trae correos ni NIT. | ☐ |
| 14.14 | Web y móvil | Cliente | Con el catálogo descargado hace más de 6 horas y con Internet. | Se actualiza solo en segundo plano; el botón «Actualizar ahora» lo hace a mano. | ☐ |
| 14.15 | API | Encargado | Sincronizar `AJUSTE_INVENTARIO` (diferencia +4, motivo CONTEO), `RECEPCION` y `DEVOLUCION` con `POST /api/offline/sincronizar`. | Cada una queda CONFIRMADA y el inventario cambia; un ajuste que deja el stock negativo queda EN_CONFLICTO; reenviar no duplica. | ☐ |
| 14.16 | Web y móvil | Cajero | Descargar el catálogo con Internet; sin conexión, «Tareas de la sucursal» → Devolución → elegir una venta reciente y una prenda. | Queda en la cola; si el plazo venció: «El plazo de devolución de esta venta venció.»; lo devuelto ya no se puede devolver otra vez. Al volver la red, CONFIRMADA. | ☐ |
| 14.17 | Web y móvil | Encargado | Sin conexión: Recepción de 5 unidades y Ajuste de −2 (merma). | El stock local sube y baja de inmediato; al sincronizar el servidor aplica ambos y deja la bitácora de inventario. | ☐ |
| 14.18 | Web y móvil | Encargado | Sin conexión, pestaña Reservas: validar el código, «Preparar», marcar una prenda «No encontrada» y «Atender». | Cada paso queda en la cola y la copia local cambia; al sincronizar el servidor reutiliza el CU-24/25. | ☐ |
| 14.19 | Móvil y web | Encargado | En Recepción o Ajuste, tocar «Escanear» y apuntar al código de barras (en la web solo Chrome/Edge). | Se llena el buscador con el código y se elige la prenda. | ☐ |
| 14.20 | Web | Proveedor | Sin conexión, «Proponer producto». | «Propuesta guardada en este dispositivo…»; al volver la red llega a la administración. | ☐ |
| 14.21 | Web | Cajero | Venta de contado sin conexión → Operaciones → botón «Comprobante LOC-…». | Se descarga un PDF provisional con el detalle, el total y el cambio. | ☐ |
| 14.22 | Web | Administrador | Sin conexión, «Reportes con IA» → «Generar». | «Generar un reporte con IA necesita Internet.» La franja superior muestra «Datos al…». | ☐ |
| 14.24 | Web (Chrome) | Administrador EMP-B | «Reportes con IA» → «🗣 Conversar», permitir el micrófono y decir «ventas de este mes». Después decir «repite» y por último «terminar». | La app saluda en voz, genera el reporte, lo lee en voz alta, vuelve a escuchar; «repite» lo lee otra vez y «terminar» cierra la conversación. Tres silencios seguidos también la cierran. | ☐ |
| 14.25 | Web (Chrome) | Administrador | Con un reporte en pantalla, tocar «🔊 Escuchar» y luego «⏹ Detener lectura». | Lee el reporte sin símbolos de formato («bolivianos» en lugar de «Bs»); se detiene al instante. | ☐ |
| 14.26 | Web | Administrador EMP-B | «Reportes con IA» → escribir (o dictar) «los 10 productos más vendidos de los últimos 3 meses, agrupados por sucursal» y generar. | Periodo «Últimos 3 meses» (90 días hasta hoy); una tabla por cada sucursal de EMP-B con su top 10 (producto, unidades, ingresos en Bs); los botones Excel y PDF traen una tabla por sucursal. Sin «por sucursal» el ranking es uno solo. | ☐ |
| 14.23 | Web | Cajero | Chrome: registrar una venta sin conexión, cambiar a otra pestaña y volver la red. | La cola se envía sola (Background Sync). | ☐ |

## 15. Modo sin conexión integrado (defensa · D1)

| # | Dónde | Cuenta | Pasos | Resultado esperado | ✔ |
|---|---|---|---|---|---|
| 15.1 | Web | Cualquiera | En cualquier pantalla, activar «Simular sin conexión» (o cortar el WiFi). | Aviso emergente «Sin conexión: sus acciones se guardarán en este dispositivo y se enviarán solas al volver la red.»; la pantalla no se recarga ni cambia de ruta. | ☐ |
| 15.2 | Web | Cliente | Sin conexión, dejar dos reservas o compras. Apagar «Simular sin conexión» sin recargar. | «Conexión restablecida. Sincronizando 2 operaciones…» y luego «Sincronización completa: X confirmadas, Y en conflicto, Z rechazadas» con el botón «Ver detalle», que abre la cola. «Mis compras» y «Mis reservas» se actualizan solas si estaban abiertas. | ☐ |
| 15.3 | Web | Cliente | Permitir las notificaciones del sitio, dejar una operación sin conexión, cambiar a otra pestaña y volver la red. | Además del aviso, sale una notificación del sistema con el mismo texto. | ☐ |
| 15.4 | Web y móvil | Cliente | Sin conexión, comprar la última unidad de una prenda; antes de sincronizar, venderla desde caja. Volver la red. | En «Mis compras» aparece «Compras que no se pudieron realizar» con la etiqueta «En conflicto», el motivo «La prenda se agotó mientras estaba sin conexión. No se le cobró nada.» y el botón «Elegir otra talla o sucursal» (abre la prenda en la web, el catálogo en el móvil). La campana trae el mismo aviso. | ☐ |
| 15.5 | Web y móvil | Cajero | Sin conexión, vender una prenda que otro dispositivo ya agotó. Volver la red. | En Caja (web) y en el inicio (móvil) aparece «Ventas con problema» con el motivo y «Devolución del efectivo: Pendiente…»; cuando el Encargado la descarta pasa a «Efectivo devuelto al cliente.» sin recargar. | ☐ |
| 15.6 | Móvil | Cliente o Cajero | Poner modo avión y luego quitarlo, sin salir de la pantalla. Repetir con la app en segundo plano. | SnackBar al perder y al recuperar la red, y el resumen de la sincronización; en segundo plano, además una notificación del sistema. La app no se reinicia ni vuelve al inicio. | ☐ |
| 15.7 | Web | Cajero | Con la sesión recién iniciada y con red, esperar unos segundos (sin abrir «Diagnóstico sin conexión»). Luego activar «Simular sin conexión». | El catálogo de la sucursal ya está descargado solo (sin pasar por otra pantalla); la franja «Datos al…» lo confirma. | ☐ |
| 15.8 | Web | Cajero | En **Caja** con «Simular sin conexión» activo: buscar o escanear una prenda, armar la venta, «Registrar venta», escribir el efectivo y «Cobrar». | Los mismos botones y ventanas de siempre. Sale «✔ Venta cobrada» con el comprobante provisional **LOC-<sucursal>-<código>** y el cambio; «Imprimir comprobante» descarga el PDF provisional; el stock local baja; arriba aparece «1 venta(s) por sincronizar». | ☐ |
| 15.9 | Web | Cajero | Apagar «Simular sin conexión» sin recargar. | Aviso de reconexión; la venta pasa a «Confirmada» en «Mi turno» y recibe su comprobante **CMP-…** oficial; el contador vuelve a 0. «Resumen de mi turno» muestra ventas, efectivo, cambio y estados. | ☐ |
| 15.10 | Web | Cajero | En **Devoluciones y cambios** con «Simular sin conexión»: elegir una venta reciente, indicar prendas y «Registrar devolución». Repetir con una venta fuera de plazo. | Se guarda en la cola; lo ya devuelto no se puede devolver otra vez; fuera de plazo: «El plazo de devolución de esta venta venció.». Al volver la red queda CONFIRMADA. | ☐ |
| 15.11 | Web (dos navegadores) | Dos cajeros de la misma sucursal + Encargado | Dejar UNA unidad de una prenda. Con «Simular sin conexión» en ambos navegadores, que cada cajero venda esa unidad en efectivo. Apagar la simulación primero en el navegador A y después en el B. | A: venta Confirmada con CMP-…. B: «Ventas con problema» (En conflicto) con «No hay existencias suficientes…». El Encargado, en «Conflictos de sincronización», la descarta marcando «Devolver el efectivo al cliente» (prenda sin daños, sin desgaste y con etiquetas): B ve la venta Rechazada y «Efectivo devuelto al cliente.» con la nota de devolución; el stock queda en 0 y no se descontó dos veces. | ☐ |
| 15.12 | Móvil | Cajero | Iniciar sesión con red y esperar. Poner modo avión. Abrir **Caja** desde el inicio, buscar o escanear una prenda, registrar la venta con el efectivo. | El catálogo se descargó solo; la venta se guarda; el aviso inferior ofrece «Comprobante» (PDF provisional LOC-…); la pestaña «Mi turno (1 por sincronizar)» lista la venta como «Registrada en el dispositivo». | ☐ |
| 15.13 | Móvil | Cajero | Quitar el modo avión sin salir de la pantalla. | Aviso de reconexión y de resumen; en «Mi turno» la venta pasa a «Confirmada por el servidor» con su CMP-…; «Resumen de mi turno» (icono del recibo). | ☐ |
| 15.14 | Móvil | Cajero | En el inicio, «Devoluciones» (sin conexión). | Abre la devolución de la sucursal con las mismas validaciones (plazo y lo ya devuelto). | ☐ |
| 15.15 | Web | Encargado + Cajero | El Encargado prepara una reserva (queda PREPARADA) con red. En el Cajero, con red, esperar la descarga. Activar «Simular sin conexión» y en **Caja** escribir el código en «Cobrar una reserva», «Registrar venta» y cobrar en efectivo. | La reserva se carga con el nombre del cliente y sus prendas con el precio de la copia; la venta se guarda con el comprobante LOC-…; el stock local no baja (ya estaba apartado). Al volver la red queda Confirmada con su CMP-…, la reserva pasa a COMPLETADA y el stock reservado queda como vendido. Una reserva sin preparar: «El código de reserva no existe, no está lista para cobrar…». | ☐ |
| 15.16 | Móvil | Cajero | Igual que 15.15 pero en **Caja** del teléfono: campo «Cobrar una reserva (código)», botón «Cargar la reserva», efectivo y «Registrar venta». | Se cargan las prendas reservadas, la venta lleva el código de la reserva y no toca el stock local; al sincronizar se confirma. | ☐ |
| 15.17 | Móvil | Cliente | Con una compra en conflicto (como en 15.4), en «Mis compras» tocar «Elegir otra talla o sucursal». | Abre el catálogo ya buscando esa prenda y, con conexión, muestra su ficha para elegir otra talla o sucursal. | ☐ |
| 15.18 | Móvil | Cualquiera | Dejar operaciones pendientes, quitar el modo avión. | El resumen «Sincronización completa…» trae el botón «Ver detalle», que abre la cola de operaciones. Con «Mis compras» o «Mis reservas» abiertas, la lista se actualiza sola. | ☐ |
| 15.19 | Web y móvil | Cajero | Con red, enviar dos ventas juntas o una que quede en conflicto (sin reconexión). | El resumen de la sincronización se anuncia igual (varias operaciones o conflictos/rechazos); una sola venta confirmada no repite el aviso. | ☐ |
| 15.20 | Web | Encargado | En **Inventario** con «Simular sin conexión»: buscar por nombre o SKU, «Escanear» un código de barras, «Ajustar» una prenda (Salida, cantidad, motivo «Daño») y «Recibir» una cantidad con su referencia. | La tabla sale de la copia descargada con aviso «Sin conexión…»; reservadas, vendidas y mínimos se ven como «—» y «Mínimo» está apagado («El mínimo de reposición necesita Internet»). El ajuste y la recepción cambian el Disp. al instante y quedan en «Diagnóstico sin conexión → Operaciones». Al volver la red el servidor los aplica y la tabla se recarga sola. Un ajuste que dejaría el stock en negativo queda EN_CONFLICTO. | ☐ |
| 15.21 | Web | Encargado | En **Recepción de mercadería** sin conexión: elegir la prenda, cantidad y referencia, «Registrar recepción». | Aviso «Sin conexión…»; el inventario local sube y la operación queda pendiente; al volver la red se confirma. Con red la pantalla es la de siempre (lotes en tránsito). | ☐ |
| 15.22 | Web | Encargado | En **Reservas de la sucursal** y en **Atención de reservas** sin conexión: validar el código, «Preparar», «No encontrada» en una prenda y «Atender · lleva las prendas». | Mismos pasos que con red, sobre la copia descargada; cada paso queda en la cola y cambia el estado de la reserva en pantalla. Al volver la red se confirman en el orden en que se hicieron. «Atender · lleva las prendas» deja la reserva lista para cobrarse en Caja (paso 15.15). | ☐ |
| 15.23 | Web (dos navegadores) | Encargado + Cajero | Repetir 15.11 (dos cajeros, última unidad) y abrir **Conflictos de sincronización**. | La tarjeta dice «Qué pasó», «Qué pidió ese dispositivo» (prenda, pidió, hay hoy, faltan) y «El cliente entregó Bs 350,00 en caja. Si descarta esta venta debe devolverle Bs 300,00.»; el botón dice «Descartar y devolver Bs 300,00» y al confirmar el aviso trae la nota de devolución. | ☐ |
| 15.24 | Móvil | Encargado | En el inicio, «Conflictos de sincronización» (con conexión): ver el caso de 15.23, «Reintentar» y «Descartar…» devolviendo el efectivo. | Mismos datos y el mismo monto a devolver; no se puede devolver el dinero sin marcar las tres condiciones de la prenda. Sin conexión: «Sin conexión: los conflictos se resuelven cuando hay Internet.». | ☐ |
| 15.25 | Móvil | Encargado | En «Tareas de la sucursal», sin conexión: «Recepción» y «Ajuste» (con «Escanear») y «Reservas». | Igual que en la web (15.20 y 15.22). | ☐ |
| 15.26 | Web | Proveedor | En **Mis envíos y propuestas** (sin entrar a «Diagnóstico sin conexión») con «Simular sin conexión»: «Nueva propuesta» y enviar. | «Propuesta guardada en este dispositivo…»; al volver la red llega a la administración (necesita que la lista de colecciones se haya visto antes con red). | ☐ |
| 15.27 | Web | Administrador | Navegar Reportes, Indicadores e Inventario global con red; cortar la red (o «Simular sin conexión») y volver a abrirlos. En «Reportes», «Reportes con IA», «Analítica» y «Usuarios» tocar los botones de exportar, generar, descargar o crear. | Las pantallas muestran los últimos datos y la franja superior dice «Sin conexión… Datos al dd/MM HH:mm.» (la última vez que vio datos del servidor). Esos botones se ven apagados, explican «… necesita Internet.» al pasar el cursor y, si se tocan, avisan «Esta función necesita Internet.» en vez de dar error. | ☐ |
| 15.28 | Web | Cliente | Con red y Stripe en modo prueba: comprar guardando una tarjeta (`4242 4242 4242 4242`). Abrir otra vez «Pagar mi compra» con red (así se guarda la lista de tarjetas), activar «Simular sin conexión» y, en «Entrega, facturación y pago», elegir «Pagar con Visa terminada en 4242 al volver la conexión». | Sin marcar «Autorizo el cobro de Bs X a esta tarjeta cuando se confirme mi compra.» no deja guardar («Confirme la autorización del cobro…»). Con «Dejar por pagar» o con la tarjeta autorizada la compra se guarda en el dispositivo. Aparece el texto «Para usar una tarjeta nueva necesita Internet. Puede pagar con una tarjeta guardada o dejar la compra por pagar.» y no hay ningún campo para escribir una tarjeta. | ☐ |
| 15.29 | Web | Cliente | Apagar «Simular sin conexión» sin recargar. | El servidor crea el pedido y cobra la tarjeta guardada: aviso «Su compra fue cobrada y confirmada» (campana y notificación), «Mis compras» la muestra Pagada con su comprobante CMP-…, y en el panel de Stripe hay UN solo cobro (en BOB) para ese pedido; reenviar la operación no cobra otra vez. | ☐ |
| 15.30 | Web (dos navegadores) | Cliente + Cajero | Dejar una sola unidad; el Cajero la vende en caja; el Cliente (sin conexión) la compra pagando con la tarjeta guardada. | La compra queda EN_CONFLICTO con «La prenda se agotó mientras estaba sin conexión. No se le cobró nada.» y su aviso; en Stripe no aparece ningún cobro. | ☐ |
| 15.31 | Web | Cliente + Administrador | El Cliente compra sin conexión pagando con la tarjeta autorizando Bs 100; antes de sincronizar el Administrador sube el precio de la prenda. | EN_CONFLICTO «El precio cambió; confirme el nuevo total.»; no se cobra nada y el cliente recibe el aviso. | ☐ |
| 15.32 | Web | Cliente | Guardar en Stripe la tarjeta `4000 0027 6000 3184` (pide 3D Secure: completarlo al pagar con «Guardar esta tarjeta»), y comprar sin conexión pagando con ella. | Al sincronizar el banco pide autenticación y no se puede cobrar fuera de sesión: la compra queda confirmada pero **por pagar** con el aviso «No pudimos cobrar su tarjeta; complete el pago desde Mis compras.»; desde «Mis compras» se completa el pago con 3D Secure. | ☐ |
| 15.33 | Web | Cajero | Devolver (en Devoluciones, con red) una prenda de la compra cobrada en 15.29. | Se reembolsa a la misma tarjeta con el flujo de CU-41 y el cliente recibe el aviso con el monto. | ☐ |
| 15.34 | Móvil | Cliente | Con red, abrir «Entrega, facturación y pago» (o descargar el catálogo) para que se guarden las tarjetas; modo avión; «Modo sin conexión → Registrar → Comprar» y elegir «Pagar con Visa terminada en 4242 al volver la conexión». | Mismo comportamiento que en 15.28 y 15.29: exige autorizar el cobro, solo guarda el id de la tarjeta y el total, y al volver la red el servidor cobra. | ☐ |

## 16. Demostración de la defensa (D5)

Antes de empezar: iniciar sesión con red en cada cuenta, esperar a que se descargue el catálogo y dejar a la vista la barra superior. Allí está el indicador **En línea / Sin conexión / Sincronizando… N** (web y móvil): al tocarlo abre la cola de ese rol. El panel «Modo sin conexión → Demostración» reúne el interruptor «Simular sin conexión», los contadores, la cola en vivo y el registro de sincronización en una sola vista.

| # | Dónde | Cuenta | Pasos | Resultado esperado | ✔ |
|---|---|---|---|---|---|
| 16.1 | Web | Cajero | **Guion (a), venta sin conexión.** Activar «Simular sin conexión». En Caja buscar o escanear una prenda, «Registrar venta», escribir el efectivo y «Cobrar». | El indicador pasa a «Sin conexión · 1». La venta queda «Registrada en el dispositivo» con comprobante provisional LOC-…; el stock local baja. | ☐ |
| 16.2 | Web | Cajero | Seguir 16.1: apagar «Simular sin conexión» sin recargar. | Aviso de reconexión; el indicador pasa por «Sincronizando…» y vuelve a «En línea»; la venta queda «Confirmada» con su CMP-… oficial. | ☐ |
| 16.3 | Web y móvil | Cajero | **Guion (b), dos cajeros y la última unidad.** Dejar una sola unidad; en dos dispositivos con «Simular sin conexión», vender esa unidad. Volver la red en ambos. | Uno queda «Confirmada»; el otro «En conflicto» (sin existencias). Aparece en «Ventas con problema» y en «Conflictos de sincronización» del Encargado. | ☐ |
| 16.4 | Web o móvil | Encargado | Seguir 16.3: abrir «Conflictos de sincronización», «Descartar…» devolviendo el efectivo. | Se muestra el monto a devolver; la operación queda «Rechazada» y su línea de tiempo termina en «Resuelta por el Encargado: descartada». | ☐ |
| 16.5 | Web | Cliente | **Guion (c), compra pagada con tarjeta guardada.** Con red guardar una tarjeta de prueba (`4242 4242 4242 4242`), abrir otra vez «Pagar mi compra» para bajar la lista y activar «Simular sin conexión». Comprar eligiendo «Pagar con Visa…» y autorizar el monto. | Compra «Registrada en el dispositivo»; la cola guarda solo el id de la tarjeta y el total, nunca el número ni el CVC. | ☐ |
| 16.6 | Web | Cliente | Seguir 16.5 con stock: apagar «Simular sin conexión». | El servidor crea el pedido y cobra la tarjeta: aviso «Su compra fue cobrada y confirmada» y comprobante CMP-…. | ☐ |
| 16.7 | Web (dos navegadores) | Cliente + Cajero | Repetir 16.5 dejando una sola unidad que el Cajero vende antes de sincronizar. | La compra queda «En conflicto» y **no se cobra nada**; el Cliente lo ve en «Compras que no se pudieron completar». | ☐ |
| 16.8 | Web y móvil | Encargado | **Guion (d), Encargado.** Sin conexión: «Recepción» (prenda, cantidad, referencia), «Ajuste» (Salida, cantidad, motivo) y en Reservas «Preparar» y «Atender». | Cada operación queda en la cola; el inventario local sube o baja de forma provisional. | ☐ |
| 16.9 | Web y móvil | Encargado | Seguir 16.8: volver la red. | El resumen «Sincronización completa…» con «Ver detalle»; el inventario del servidor refleja la recepción y el ajuste, y las reservas pasan a su estado. | ☐ |
| 16.10 | Web y móvil | Cualquiera | **Guion (e), aviso de reconexión.** Dejar dos operaciones sin conexión. Apagar el interruptor (o quitar el modo avión) sin salir de la pantalla ni recargar. | Aviso «Conexión restablecida. Sincronizando 2 operaciones…», después el resumen con «Ver detalle»; las pantallas abiertas se refrescan solas. | ☐ |
| 16.11 | Web y móvil | Cualquiera | **Deshacer.** Sin conexión, registrar una venta o compra y tocar «Deshacer» (en «Mi turno», «Mis compras» o la cola). Repetir con una recepción, un ajuste y una devolución. | La operación sale de la cola y el stock local vuelve a como estaba (la devolución vuelve a ser devolvible). Aviso «Operación deshecha». | ☐ |
| 16.12 | Web y móvil | Cualquiera | Buscar «Deshacer» en una operación ya enviada, en una atención de reservas o en el cobro de una reserva. | No aparece el botón: solo se deshace lo que todavía no salió del dispositivo y no depende de una reserva. | ☐ |
| 16.13 | Web y móvil | Cualquiera | **Línea de tiempo.** En la cola, tocar «Línea de tiempo» de una operación (pendiente, confirmada y una que pasó por conflicto). | Muestra: Registrada en <dispositivo> → cada Envío con su resultado y hora → Confirmada, En conflicto o Resuelta por el Encargado. Funciona sin conexión. | ☐ |
| 16.14 | Web | Cualquiera | **Demostración.** Abrir «Modo sin conexión → Demostración», activar el interruptor, registrar algo y apagarlo. | Los contadores (Pendientes, Confirmadas, En conflicto, Rechazadas), la cola en vivo y el registro de sincronización cambian sin recargar. | ☐ |
| 16.15 | Móvil | Cliente o Cajero | Tocar el indicador de la barra del inicio. | Abre la cola de operaciones; la cuarta pestaña «Demostración» tiene lo mismo que la web. | ☐ |

## 17. Lecturas guardadas sin conexión (segunda ronda · E1)

| # | Dónde | Cuenta | Pasos | Resultado esperado | ✔ |
|---|---|---|---|---|---|
| 17.1 | Web (Chrome, build de producción) | Cliente | Iniciar sesión con red y esperar unos segundos sin abrir nada. Activar el modo avión (DevTools → Network → Offline) y abrir «Pagar mi compra». | Se ve el carrito guardado (nunca «Cargando…» eterno). Con «Simular sin conexión» pasa lo mismo. | ☐ |
| 17.2 | Web | Cliente | Con «Pagar mi compra» abierto sin red, volver la red. | La pantalla se recarga sola con el carrito del servidor. | ☐ |
| 17.3 | Web | Cliente | Iniciar sesión sin haber puesto nada en el carrito en este navegador y abrir «Pagar mi compra» sin red. | «Su carrito no está guardado en este dispositivo. Ábralo con conexión una vez.» | ☐ |
| 17.4 | Web | Encargado, Cajero, Proveedor, Administrador | Iniciar sesión con red, esperar y cortar la red. Abrir recepciones, reservas de la sucursal, inventario, proveedores, usuarios, sucursales, productos y plan. | Cada pantalla muestra lo último visto o precargado; si nunca se abrió, «Sin conexión: todavía no hay datos guardados…». Ninguna queda en «Cargando…». | ☐ |
| 17.5 | Web | Cualquiera | Cerrar sesión e iniciar con otra cuenta sin red. | No aparecen datos de la cuenta anterior. | ☐ |

## 18. Cada actor en sus pantallas normales (segunda ronda · E2)

| # | Dónde | Cuenta | Pasos | Resultado esperado | ✔ |
|---|---|---|---|---|---|
| 18.1 | Web | Cliente | Con 2 prendas en el carrito (con red), activar «Simular sin conexión» y abrir «Mi carrito». Cambiar una cantidad, quitar la otra y agregar una prenda nueva desde su ficha. | El carrito se ve con lo cambiado y el aviso «Sin conexión…»; el indicador muestra que hay cambios; «Cambiar de sucursal necesita Internet.» | ☐ |
| 18.2 | Web | Cliente | Seguir 18.1: «Proceder al pago», elegir una tarjeta guardada, autorizar y «Guardar compra para sincronizar». Apagar la simulación. | La compra se confirma y se cobra; el carrito del servidor queda **sin** lo comprado (si quedó algo, solo lo no comprado). | ☐ |
| 18.3 | Web | Cliente | Repetir 18.1 pero sin comprar: apagar la simulación. | Los cambios se aplican al carrito del servidor (cantidad, quitado) y la prenda nueva se fusiona; no se duplica nada. | ☐ |
| 18.4 | Web | Cajero | Abrir Caja con red y luego con «Simular sin conexión»: buscar una prenda. | Las fotos se ven (también sin conexión). Si todas dicen «Sin stock» con red, ver 18.5. | ☐ |
| 18.5 | Web | Administrador | Ver el inventario de la sucursal del Cajero. | Debe tener existencias en esa sucursal (los datos de demostración se preparan con el script del prompt E5). | ☐ |
| 18.6 | Web | Administrador | Sin conexión abrir Usuarios, Sucursales, Productos, Promociones y Proveedores. | Se ve lo último visto o precargado; los botones Crear, Editar, Activar, Desactivar y Guardar salen apagados («Esta función necesita Internet.»). | ☐ |
| 18.7 | Web | Proveedor | Sin conexión abrir «Mis envíos y propuestas». | Ve los avisos y propuestas guardados; si nunca los abrió, el mensaje de datos sin guardar (no «Aún no hay…»); «Nueva propuesta» se guarda en la cola. | ☐ |
| 18.8 | Web | Administrador | Sin conexión abrir Reportes con IA. | Se ve el último reporte visto; «Generar» queda apagado. | ☐ |

## 19. Cliente en el teléfono con y sin conexión (segunda ronda · E3)

| # | Dónde | Cuenta | Pasos | Resultado esperado | ✔ |
|---|---|---|---|---|---|
| 19.1 | Móvil | Cliente | Con red abrir el catálogo, una ficha y «Mi carrito». Activar el modo avión (o apagar el servidor) y tocar cualquier pantalla que llame al servidor. | El chip de la barra pasa a «Sin conexión» aunque el WiFi siga conectado; al volver el servidor, vuelve a «En línea» y aparece el aviso de reconexión. | ☐ |
| 19.2 | Móvil | Cliente | Sin conexión abrir la ficha de una prenda (la misma que vio antes, y otra que nunca abrió). | Ninguna queda con el círculo girando: se ven las variantes, el stock y los precios (de lo visto o del catálogo descargado) con «Sin conexión · datos al…». «Reservar» y «Agregar» están habilitados si hay stock. | ☐ |
| 19.3 | Móvil | Cliente | Sin conexión «Agregar» una prenda y abrir «Mi carrito». Cambiar una cantidad, quitar otra prenda. | El carrito se ve con lo cambiado y el aviso «Sin conexión…»; «Pagar» dice «Guardar compra para sincronizar». | ☐ |
| 19.4 | Móvil | Cliente | Volver la conexión y abrir «Mi carrito». | Los cambios se aplican al carrito del servidor y las prendas nuevas se suman sin duplicarse. | ☐ |
| 19.5 | Móvil | Cliente | Sin conexión «Guardar compra para sincronizar»: datos de entrega, tarjeta guardada, autorizar el cobro. Volver la conexión. | La compra se confirma y se cobra a la tarjeta; el carrito del servidor queda sin lo comprado. Con tarjeta nueva el botón explica que necesita Internet. | ☐ |
| 19.6 | Móvil | Cliente | Sin conexión abrir «Mi carrito» en un teléfono que nunca lo abrió. | «Sin conexión: su carrito no está guardado en este teléfono. Ábralo con conexión una vez.» (sin spinner). | ☐ |
| 19.7 | Móvil | Cliente | Con el catálogo descargado, buscar sin conexión y abrir una prenda. | Las fotos se ven (descargadas con el catálogo) y la ficha abre. | ☐ |

## 20. Cajero, Encargado y otros roles en el teléfono (segunda ronda · E4)

| # | Dónde | Cuenta | Pasos | Resultado esperado | ✔ |
|---|---|---|---|---|---|
| 20.1 | Móvil | Cajero | Mirar el inicio con y sin conexión. | Una sola «Caja» y una sola «Devoluciones» (la misma pantalla con y sin red); «Diagnóstico sin conexión» queda como apoyo. | ☐ |
| 20.2 | Móvil | Encargado | Mirar el inicio. | Además: «Tareas de la sucursal» (Recepción, Ajuste, Reservas) y «Conflictos de sincronización». | ☐ |
| 20.3 | Móvil | Encargado | En «Tareas → Reservas» preparar una reserva sin conexión, volver la red y esperar. | La lista de reservas se renueva sola con lo del servidor (no queda lo viejo). | ☐ |
| 20.4 | Móvil | Encargado | Abrir «Conflictos» con red, cortar la red y volver a abrirlo. | Se ve la última lista con «Sin conexión · datos al…»; Reintentar y Descartar quedan apagados; al volver la red se activan solos. | ☐ |
| 20.5 | Móvil | Cliente o Cajero | Dejar operaciones pendientes, mandar la app a segundo plano y volver la red. | Llega la notificación «Volvió la conexión: se enviaron N operaciones.» | ☐ |
| 20.6 | Móvil | Proveedor o Administrador | Abrir la app con y sin conexión. | Con red: «Las funciones de su rol se usan desde la web…»; sin red: «Esta función necesita Internet.» y «Actualizar mi plan» apagado. Nunca un spinner infinito. | ☐ |
| 20.7 | Web | Encargado | Abrir «Conflictos de sincronización» sin conexión. | Se ve lo último guardado; Reintentar y Descartar salen apagados («Esta función necesita Internet.»). | ☐ |

## 21. Cierre de la segunda ronda (E5): recorridos de la demostración y datos

**Preparar los datos** (una vez, contra el despliegue; es idempotente y no lleva claves en el código):

```bash
python scripts/preparar_demo.py --url https://fashionstore-saas-production.up.railway.app
# opcional: catálogo mínimo en EMP-C (necesita CLAVE_SUPERADMIN en el entorno)
python scripts/preparar_demo.py --url https://fashionstore-saas-production.up.railway.app --empresa-c "EMP-C,<correo>,<clave>"
```

**Auditoría de pantallas:** `python scripts/auditar_offline.py` (o `--verificar` en la integración continua) escribe `docs/AUDITORIA_OFFLINE.md`; también la corre `pytest` (`test_e5_auditoria_offline.py`).

**Cada guion de la sección 16 y la prueba automática que lo respalda**

| Guion | Backend | Web | Móvil |
|---|---|---|---|
| (a) Cajero vende sin conexión y sincroniza | `test_cu38_sincronizar.py` | `caja-offline.spec.ts` | `caja_screen_test.dart`, `flujo_offline_completo_test.dart` |
| (b) Dos cajeros y la última unidad (monto a devolver) | `test_d2_dos_cajeros_ultima_unidad.py`, `test_d3_conflictos_monto.py` | `deshacer-y-tiempo.spec.ts`, `tareas-sucursal.spec.ts` | `conflictos_screen_test.dart`, `e4_roles_sin_conexion_test.dart` |
| (c) Cliente compra con tarjeta guardada, con y sin stock | `test_d4_compra_tarjeta_guardada.py`, `test_e2_compra_offline_vacia_carrito.py` | `checkout-offline.spec.ts`, `checkout-sin-carrito.spec.ts`, `carrito-sin-conexion.spec.ts` | `tarjeta_guardada_offline_test.dart`, `e3_cliente_sin_conexion_test.dart` |
| (d) Encargado, Proveedor y Administrador | `test_r_operaciones_offline_sucursal.py`, `test_r_propuesta_proveedor_offline.py`, `test_r_atencion_reservas_offline.py` | `inventario-offline.spec.ts`, `abastecimiento-offline.spec.ts`, `lecturas-locales.spec.ts` | `tareas_sucursal_test.dart`, `e4_roles_sin_conexion_test.dart` |
| (e) Aviso de reconexión sin recargar | — | `avisos-conexion.spec.ts`, `simulacion.spec.ts` | `avisos_conexion_test.dart`, `simulacion_test.dart` |
| Reporte CU-23 por sucursal | `test_cu23_reportes_generativos.py` | `lecturas-locales.spec.ts` (último reporte visto sin red) | no aplica (solo web) |

| # | Dónde | Cuenta | Pasos | Resultado esperado | ✔ |
|---|---|---|---|---|---|
| 21.1 | Web (Chrome, build de producción) | Cajero de EMP-B | Después de correr `preparar_demo.py`, abrir Caja con red y con el modo avión. | Las prendas tienen existencias y las fotos se ven en ambos casos. | ☐ |
| 21.2 | Móvil | Cajero o Encargado de una empresa con un plan SIN modo sin conexión | Abrir el inicio. | Aparece «Caja» (con el aviso del plan); buscar, registrar y cobrar en efectivo funciona con Internet; sin Internet dice «Esta función necesita Internet…». | ☐ |

## Diferencias conocidas entre la web y el móvil

- El vestidor está disponible para el Cliente en web y móvil; en web se usa la cámara del computador.
- **Reportes administrativos, caja, inventario y demás roles:** solo en la web.
- **Comprobante de una compra hecha sin conexión:** una compra offline confirmada queda por pagar y todavía no tiene comprobante; el PDF existe cuando se paga con tarjeta.

## Si algo falla

- **La web no carga datos o da error de CORS:** revisar `CORS_ORIGINS` en Railway (ver «Problemas frecuentes» de `docs/DESPLIEGUE.md`).
- **El asistente responde `REGLAS` en EMP-B:** mirar el registro del backend; el mensaje trae el tipo de error o el código HTTP de Gemini.
- **El APK no recibe push:** revisar el aviso del flujo (sin `google-services.json`) y `FCM_PROYECTO` / `FCM_CREDENCIALES_JSON`.

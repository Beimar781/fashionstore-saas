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

## 6. Comprobante PDF

| # | Dónde | Cuenta | Pasos | Resultado esperado | ✔ |
|---|---|---|---|---|---|
| 6.1 | Web | Cliente EMP-A | «Mis compras» → la compra de 5.1 → descargar comprobante. | PDF con el número `CMP-…`, las prendas, el IVA y el total. | ☐ |
| 6.2 | Móvil | Cliente EMP-A | «Mis compras» → ver el detalle. | Muestra el número de comprobante de la compra. | ☐ |

## 7. Reservas

| # | Dónde | Cuenta | Pasos | Resultado esperado | ✔ |
|---|---|---|---|---|---|
| 7.1 | Web | Cliente EMP-A | Reservar una prenda en una sucursal. | Reserva creada; el stock disponible baja. | ☐ |
| 7.2 | Móvil | Cliente EMP-A | «Mis reservas» → cancelar la reserva. | La reserva se cancela y el stock se libera. | ☐ |

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

## Si algo falla

- **La web no carga datos o da error de CORS:** revisar `CORS_ORIGINS` en Railway (ver «Problemas frecuentes» de `docs/DESPLIEGUE.md`).
- **El asistente responde `REGLAS` en EMP-B:** mirar el registro del backend; el mensaje trae el tipo de error o el código HTTP de Gemini.
- **El APK no recibe push:** revisar el aviso del flujo (sin `google-services.json`) y `FCM_PROYECTO` / `FCM_CREDENCIALES_JSON`.

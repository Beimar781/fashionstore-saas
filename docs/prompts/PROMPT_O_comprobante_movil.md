# Prompt O — Paridad del Cliente en el móvil (comprobante PDF y funciones que faltan)

Ejecútalo **solo después** de terminar el Prompt N (pago con Stripe en el móvil) y de haberlo subido con `git push`. Lee `CLAUDE.md`, `docs/PRUEBAS_SISTEMA.md` y `docs/DESPLIEGUE.md`. Todo lo que me escribas va en español. Código explicable en una defensa: nombres en español, funciones cortas, sin abstracciones innecesarias. No toques claves, variables de Railway ni secretos. Los textos de error son los de las fichas de CU; si un mensaje ya existe en la web o el backend, reutilízalo igual.

## Objetivo
Comparé lo que puede hacer el **Cliente** en la web con lo que hace hoy en el móvil. Quiero que el móvil tenga todo lo del Cliente que tiene la web (el vestidor virtual queda solo en el móvil, por diseño). Reportes administrativos, caja, inventario y demás roles siguen solo en la web.

Lo que el móvil ya tiene: login con ojito y recuperar contraseña, catálogo con búsqueda y detalle por sucursal, vestidor, carrito, pago (Prompt N), historial de compras (solo el número del comprobante), mis reservas (ver y cancelar), modo sin conexión y avisos push.

Lo que le falta al móvil, en este orden de prioridad (haz **un bloque, una prueba y un commit por cada punto**; si un punto no compila o rompe pruebas, no sigas con el siguiente: explícame qué pasó):

## 1. Comprobante PDF
1. Librerías (regla 13): agrega `path_provider` y `open_filex` a `movil/pubspec.yaml`. Comprueba con instalación limpia (`flutter pub get`) y con `flutter build apk --release --dart-define=API_URL=https://fashionstore-saas-production.up.railway.app/api`.
2. Descarga: en el repositorio de compras (`primer_parcial/ventas/data`) una función que pida `GET /compras/{id}/comprobante` con el token como bytes, lo guarde en la carpeta temporal (nombre del `Content-Disposition` o `comprobante-<numero>.pdf`) y devuelva la ruta.
3. Botón «Ver comprobante»: en `pedidos_screen.dart` para cada compra con `comprobante_numero`, y en la pantalla de pago aprobado de `carrito_screen.dart`. Abre el PDF con el visor del teléfono (desde ahí se comparte o se guarda). Si la operación offline confirmada ya trae su comprobante, también ahí; si no lo trae, no inventes nada y dímelo.
4. Errores en español sin cerrar la app: sin conexión → «Sin conexión: no se puede descargar el comprobante. Inténtelo de nuevo cuando tenga red.»; 404/403 → «No se encontró el comprobante de esta compra.»; sin visor de PDF → «No hay una aplicación para abrir PDF en este teléfono.» El botón muestra un indicador y no se puede tocar dos veces.
5. Pruebas de Dart con dobles en memoria (descarga correcta, nombre del archivo, error de red, 404, y que no se abra nada si falla).

## 2. Compra completa: entrega y datos de facturación
Hoy el móvil envía siempre retiro, NIT `0` y «Sin nombre». La web (`checkout.page.ts`) deja elegir **Retiro en sucursal** o **Entrega a domicilio** (con dirección de entrega) y pide **NIT o CI** y **Razón social** (opcional). Agrega esa misma pantalla al móvil antes de pagar, con las mismas validaciones y mensajes, y envía esos datos a `POST /compras/checkout`. Pruebas de Dart del formulario (retiro, domicilio sin dirección, NIT vacío).

## 3. Reservar prendas en línea
La web permite «Agregar a mi reserva» desde el catálogo y luego confirmar en «Mi reserva» eligiendo sucursal y día y hora aproximada (`reservar.page.ts`, `POST /reservas`). En el móvil hoy solo se reserva desde «Modo sin conexión». Agrega: botón «Agregar a mi reserva» en el detalle de la prenda (al lado del carrito), pantalla «Mi reserva» con sucursal, día y hora, y confirmación con el mismo cuerpo y reglas que la web. Que la pantalla «Mis reservas» tenga un acceso a ella y que al cancelar pida el motivo (campo opcional de 200 caracteres, como en la web). El modo sin conexión sigue igual. Pruebas de Dart.

## 4. Asistente de compras con IA
La web tiene «Asistente de compras» (`asistente.page.ts`, `POST /asistente/chat`), solo para el plan Profesional. Agrega la pantalla de chat al móvil: burbujas de conversación, productos sugeridos que abren el detalle de la prenda, botones de sugerencias, y selector de sucursal opcional. La entrada del menú aparece solo si el plan de la empresa incluye `reportes_ia` (usa la información de plan que el móvil ya guarda en `sesion.dart`; si no está, agrégala sin tocar el backend). Con un plan sin IA, no aparece. Sin conexión: mensaje «Sin conexión: el asistente necesita Internet.» Pruebas de Dart con un doble del repositorio.

## 5. Crear cuenta de cliente
La web tiene «Crear cuenta» (`registro.page.ts`, CU de registro de cliente con código de empresa). Agrega «Crear cuenta» en el login del móvil con los mismos campos, validaciones, mensajes y endpoint, con ojito en la contraseña y volviendo al login al terminar. Pruebas de Dart del formulario.

## 6. Tarjetas guardadas (solo si el Prompt N lo dejó fácil)
La web permite guardar una tarjeta al pagar, usarla después y eliminarla (`/pagos/tarjetas`). Si con la hoja de pago de Stripe del Prompt N se puede ofrecer «Guardar esta tarjeta» y «Usar una tarjeta guardada» sin complicar el código, agrégalo; si no, **no lo hagas**: déjalo anotado en tu resumen como diferencia conocida entre web y móvil.

## Backend y web
No deberían cambiar. Verifica con pruebas (agrega las que falten en `backend/tests/`): `GET /api/compras/{id}/comprobante` entrega un PDF válido para una compra pagada con Stripe de EMP-A y de EMP-B, y un cliente de otra empresa recibe 404. Si al usar los endpoints desde el móvil encuentras un error de backend, corrígelo con su prueba.

## Documentación (regla 11)
Actualiza `docs/PRUEBAS_SISTEMA.md` (casos del móvil: comprobante tras pagar y desde el historial, sin conexión, entrega a domicilio con NIT, reserva en línea, asistente con plan Profesional y sin plan, crear cuenta), `docs/MENSAJES_PENDIENTES_WORD.md` (mensajes nuevos y la decisión «el Cliente tiene las mismas funciones en web y móvil, salvo el vestidor virtual, que es solo móvil; los reportes administrativos son solo web») y `docs/TRAZABILIDAD.md` si agregas pruebas.

## Cierre
Corre `cd backend && python -m pytest -q`, `cd frontend && npm run build`, y en `movil/` `flutter analyze` y `flutter test`. Si todo pasa: commits por bloque con mi identidad de git, mensaje corto en español, sin líneas de coautoría, y `git push`. Si algo falla: no hagas commit y explícame qué pasó.

Dame un resumen en español: qué cambiaste por punto, qué decidiste (dónde quedó cada botón), qué quedó pendiente (por ejemplo tarjetas guardadas) y qué debo probar a mano en el celular. Cuando termines avísame para que lance el workflow del APK desde el chat.

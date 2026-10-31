# Prompt M — Cierre del despliegue y APK listo para probar todo el sistema

Lee primero `CLAUDE.md` y `docs/DESPLIEGUE.md`. Todo lo que me escribas va en español. Trabaja en este orden y haz un commit por bloque (mensaje corto en español, sin líneas de coautoría, con mi identidad de git). Al final corre las pruebas y haz push. No toques variables de Railway, claves ni secretos: eso lo manejo yo desde el chat.

## Contexto (ya está hecho, no lo rehagas)
- Producción en Railway (plan Hobby): web https://frontend-production-13a8.up.railway.app · API https://fashionstore-saas-production.up.railway.app (docs en `/docs`, salud en `/salud`).
- Brevo ya envía correos reales (probado: llega el de restablecer contraseña). Stripe está en modo prueba. Gemini ya responde en producción (origen `IA`).
- La variable `API_URL` de GitHub Actions y el secreto `GOOGLE_SERVICES_JSON` ya existen. El workflow `apk.yml` ya compiló un APK bueno (run #1, artefacto `fashionstore-apk`).
- Causa del fallo de IA: el modelo `gemini-flash-latest` se queda colgado (ReadTimeout a los 20 s) con nuestra clave; `gemini-3.1-flash-lite` y `gemini-3-flash-preview` responden en 1–2 s. En Railway ya puse `IA_MODELO=gemini-3.1-flash-lite`.

## Bloque 1 — Cambio pendiente de `tsconfig`
`frontend/tsconfig.app.json` tiene `"rootDir": "./src"` sin commitear (arregla el aviso de VS Code). Comprueba que `npm run build` sigue pasando y haz un commit aparte solo con ese archivo.

## Bloque 2 — IA: modelo y diagnóstico
1. En `backend/app/core/ia.py` cambia el modelo por defecto de Gemini a `gemini-3.1-flash-lite`. Actualiza el mismo valor en `backend/.env.example`, `docs/DESPLIEGUE.md` (tabla de claves) y el Prompt L de `docs/PLAN_PRIMER_PARCIAL.md`.
2. Hoy el log solo dice «no respondió». Haz que registre el tipo de excepción (por ejemplo `ReadTimeout`, `ConnectError`, `JSONDecodeError`) y el código HTTP cuando no sea 200. Nunca el cuerpo completo ni la clave ni el prompt.
3. Sube el `timeout` de Gemini a 25 s solo si no rompe la experiencia del asistente; si no, déjalo en 20.
4. Agrega pruebas con el doble en memoria: timeout → respaldo + log con el tipo de excepción; respuesta 200 válida → origen `IA`.

## Bloque 3 — Revisión del móvil antes de recompilar el APK
Revisa `movil/` y dime en el resumen qué encontraste. Corrige lo que falte:
1. **URL del API:** el APK de release debe usar HTTPS y leer `API_URL` desde el workflow (no `localhost` ni `10.0.2.2`). Confirma cómo llega el valor (`--dart-define` o archivo) y que el release no permite tráfico sin cifrar.
2. **Permisos de Android** en el manifiesto de release: `INTERNET`, `POST_NOTIFICATIONS` (Android 13+, con solicitud en tiempo de ejecución), y cámara si el vestidor la usa.
3. **Firebase/FCM:** al iniciar sesión, la app debe registrar su token FCM en el backend. Comprueba el flujo completo y qué pasa si el usuario rechaza el permiso de notificaciones.
4. **Login móvil:** mostrar/ocultar contraseña y «¿Olvidó su contraseña?» funcionando contra la API real.
5. **Pagos en el móvil:** verifica cómo se paga con tarjeta y que funcione de punta a punta con la tarjeta de prueba `4242 4242 4242 4242`. Si el móvil usa el pago simulado (y no Stripe), está bien: no lo cambies, no agregues avisos ni etiquetas de «modo simulado» en la interfaz, y solo indícalo en tu resumen.
6. **Offline (RN11/RN12):** una compra hecha sin conexión queda `REGISTRADA_LOCAL`, se envía al volver la red y se confirma sin duplicarse.
7. **Contador de FPS en el vestidor:** necesito medir los FPS en un celular real para el Word. Agrega un contador pequeño (FPS actual y promedio) que se muestre al mantener presionado el título del vestidor, usando `SchedulerBinding.addTimingsCallback`, sin dependencias nuevas y sin afectar el rendimiento cuando está oculto.
8. Asegura que la app tenga nombre visible «FashionStore» y un ícono (el que haya, si no hay uno se deja el de Flutter), y que el `applicationId` siga siendo `com.example.fashionstore_movil` (coincide con `google-services.json`).
9. Corre `flutter analyze` y `flutter test`. Si algo falla, no hagas commit y explícame qué pasó.

## Bloque 4 — Documentación del despliegue
Actualiza `docs/DESPLIEGUE.md` con lo que aprendimos en la práctica (sin ninguna clave ni contraseña real):
1. Las URLs reales de web y API.
2. Railway: cada servicio necesita su **Root Directory** (`/backend` y `/frontend`) para que se use su Dockerfile; el dominio público necesita el **puerto de destino 8080** y la variable `PORT=8080`; el healthcheck `/salud` se configura en la interfaz porque `railway.toml` puede ser ignorado.
3. `CORS_ORIGINS` lleva el dominio literal del frontend (una referencia `${{frontend.RAILWAY_PUBLIC_DOMAIN}}` puede resolver vacía).
4. Las variables se cargan en bloque con el Raw Editor de Railway; el editor las reformatea con comillas y es normal.
5. Plan Hobby: costo aproximado de 5 USD al mes más uso; revisar la pestaña Usage.
6. Cuentas de demostración (públicas, solo para la defensa): SuperAdmin `superadmin@fashionstore.com`; EMP-A `admin@modaurbana.com`, `cliente@emp-a.com`; EMP-B `admin@estiloandino.com`, `cliente@emp-b.com`. Sus contraseñas están en el seed.
7. Cómo obtener el APK: GitHub → Actions → «Compilar APK» → Run workflow → al terminar, descargar el artefacto `fashionstore-apk` (zip con `app-release.apk`; se conserva 14 días) → instalar permitiendo orígenes desconocidos.
8. Sección «Qué pasa si falla la IA»: el sistema cae al modo de reglas locales y lo deja en el log.
9. Verifica que `.gitignore` excluya `google-services.json`, `claves-despliegue.env` y cualquier `.env`, y que no haya secretos en el historial reciente (`git log -p` sobre `docs/` y `backend/.env.example`). Avísame si encuentras alguno.

## Bloque 5 — Guía de pruebas y prueba de humo
1. Crea `docs/PRUEBAS_SISTEMA.md`: lista de verificación para probar web y móvil juntos, con cuenta a usar, pasos y resultado esperado, en este orden: login y recuperación de contraseña (correo real), catálogo por empresa (EMP-A sin IA y EMP-B con IA), asistente (en EMP-A debe dar 403 «Su plan no incluye esta funcionalidad»), vestidor, carrito y compra con tarjeta de prueba, comprobante PDF, reservas, devolución, aviso push al cliente (web y móvil), compra offline y conflicto, bitácora y panel del SuperAdmin.
2. Crea `scripts/humo_produccion.py` (solo biblioteca estándar o `httpx`, que ya está en `requirements.txt`): recibe la URL del API como argumento, inicia sesión con las cuentas demo, y revisa `/salud`, el catálogo, `/api/pagos/config` (modo `stripe`), el asistente de EMP-B (origen `IA`) y el 403 de EMP-A. Imprime un resumen con ✔/✘ y sale con código distinto de cero si algo falla. No imprime tokens.

## Bloque 6 — Word y trazabilidad (regla 11)
Agrega a `docs/MENSAJES_PENDIENTES_WORD.md` lo nuevo de este bloque: el modelo de IA y su respaldo, el despliegue en Railway y los pasos del APK. Si cambias algún mensaje HTTP, inclúyelo con su código. Actualiza `docs/TRAZABILIDAD.md` si agregas pruebas.

## Cierre
1. Corre `cd backend && python -m pytest -q`, `cd frontend && npm run build`, y en `movil/` `flutter analyze` y `flutter test`.
2. Si todo pasa: commits por bloque y `git push`. Railway redespliega solo al recibir el push; no toques nada ahí.
3. Muéstrame un resumen en español: qué cambió por bloque, qué encontraste en la revisión del móvil (Bloque 3) y qué decisiones tomaste. Termina con la lista de cosas que sigan pendientes y que yo deba hacer a mano.
4. Cuando termines, avísame para que desde el chat vuelva a lanzar el workflow del APK con este código y te pase el enlace de descarga.

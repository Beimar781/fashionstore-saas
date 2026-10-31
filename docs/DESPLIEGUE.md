# Despliegue en Railway

Guía paso a paso, para quien nunca usó Railway. Al terminar, FashionStore queda en internet con **HTTPS** y todo funcionando de verdad: correo (Brevo), pago con tarjeta de prueba (Stripe), IA gratuita (Google Gemini), push web y push móvil (Firebase).

> **Regla de oro:** las claves **nunca** se pegan en el chat, en el código ni en el repositorio. Solo van en las **variables de Railway** (y, para trabajar en tu PC, en `backend/.env`, que git ignora).

## URLs del despliegue real

| Qué | URL |
|---|---|
| Web (tienda y panel) | <https://frontend-production-13a8.up.railway.app> |
| API | <https://fashionstore-saas-production.up.railway.app> (documentación en `/docs`, salud en `/salud`) |
| `API_URL` del APK y del frontend | `https://fashionstore-saas-production.up.railway.app/api` |

## 1. Qué se despliega

Un proyecto de Railway con **tres servicios**:

| Servicio | Qué es | Carpeta | Se construye con |
|---|---|---|---|
| **Postgres** | Base de datos | — | Plugin de Railway |
| **backend** | API FastAPI | `backend/` | `backend/Dockerfile` |
| **frontend** | PWA de Angular servida con nginx | `frontend/` | `frontend/Dockerfile` |

Las imágenes de los productos y los PNG del vestidor se guardan en disco: el backend lleva un **Volume** montado en `/app/media`. La app móvil (APK) se compila aparte, en GitHub Actions, y apunta al backend ya desplegado.

## 2. Antes de empezar: las cuentas

Crea estas cuentas (todas tienen plan gratis o de prueba) y guarda las claves en un lugar privado, **no en el chat**:

1. **GitHub** (ya la tienes): el repositorio `fashionstore-saas`.
2. **Railway**: <https://railway.com> → *Login with GitHub*.
3. **Brevo** (correo): <https://www.brevo.com>.
4. **Stripe** (pagos, modo de prueba): <https://dashboard.stripe.com/register>.
5. **Google AI Studio** (IA gratis, sin tarjeta): <https://aistudio.google.com>.
6. **Firebase** (push móvil): <https://console.firebase.google.com>.

Qué clave sale de dónde está en la **tabla del apartado 5**.

## 3. Paso a paso en Railway

### 3.1 Crear el proyecto y la base de datos

1. En Railway: **New Project → Deploy from GitHub repo** → elige `fashionstore-saas` (autoriza a Railway a ver el repositorio si te lo pide).
   Railway crea un servicio con el repo completo; lo vamos a usar para el backend.
2. Dentro del proyecto: **+ New → Database → Add PostgreSQL**. Aparece un servicio **Postgres**.

### 3.2 Servicio backend

1. Entra al servicio creado desde GitHub y renómbralo a **backend** (Settings → nombre del servicio). Los nombres importan para las referencias de las variables.
2. **Settings → Source → Root Directory** = `/backend`. **Cada servicio necesita su Root Directory** (`/backend` y `/frontend`): sin él Railway construye desde la raíz del repositorio y no encuentra el Dockerfile del servicio.
   **Health check:** en **Settings → Deploy → Healthcheck Path** escribe `/salud`. Se configura en la interfaz porque Railway puede ignorar `backend/railway.toml`.
3. **Volume:** en el lienzo del proyecto, **+ New → Volume** (o clic derecho sobre el servicio → *Attach volume*), conéctalo al servicio **backend** con **Mount path** = `/app/media`.
4. **Variables** (pestaña *Variables* del servicio backend → *Raw Editor* permite pegar varias de una vez):

   ```
   DATABASE_URL=${{Postgres.DATABASE_URL}}
   SECRET_KEY=<la clave larga que generaste, ver tabla>
   MEDIA_DIR=/app/media
   CARGAR_DATOS_DEMO=true
   IA_PROVEEDOR=gemini
   GEMINI_API_KEY=<tu clave de Google AI Studio>
   BREVO_API_KEY=<tu clave de API de Brevo>
   BREVO_SENDER_EMAIL=<el remitente verificado en Brevo>
   BREVO_SENDER_NAME=FashionStore
   STRIPE_SECRET_KEY=<sk_test_...>
   STRIPE_PUBLISHABLE_KEY=<pk_test_...>
   VAPID_PUBLIC_KEY=<ver tabla>
   VAPID_PRIVATE_KEY=<ver tabla>
   VAPID_SUBJECT=mailto:<tu correo>
   FCM_PROYECTO=<ID del proyecto de Firebase>
   FCM_CREDENCIALES_JSON=<contenido completo del JSON de la cuenta de servicio>
   ```

   `CORS_ORIGINS` y `FRONTEND_URL` se completan en el paso 3.4, cuando exista la URL del frontend.
   Todas las variables posibles, comentadas, están en [`backend/.env.example`](../backend/.env.example). Las que no tengas todavía puedes omitirlas: esa función queda en **modo simulado** (el correo se imprime en los registros, el pago es simulado, la IA usa reglas locales, el push queda en la campana).
5. **Puerto:** agrega la variable `PORT=8080`. **Settings → Networking → Generate Domain** y, cuando pregunte el puerto de destino (*target port*), escribe **8080**; si el dominio apunta a otro puerto, la web responde «Application failed to respond». Obtienes una URL como `https://backend-production-xxxx.up.railway.app`. Apúntala.

### 3.3 Servicio frontend

1. **+ New → GitHub Repo** → el mismo repositorio. Renombra el servicio a **frontend**.
2. **Settings → Source → Root Directory** = `/frontend` (así se usa `frontend/Dockerfile`).
3. **Variables:**

   ```
   API_URL=https://<dominio-del-backend>/api
   ```

   Es la URL del paso 3.2.5 **terminada en `/api`**. No se graba al compilar: el contenedor genera `/config.js` con este valor cada vez que arranca, así que si cambia el dominio solo hay que cambiar la variable y reiniciar.
4. **Settings → Networking → Generate Domain** con el **puerto de destino 8080** (el frontend ya trae `PORT=8080` en su Dockerfile). Apunta la URL (`https://frontend-production-yyyy.up.railway.app`). Esa es la dirección pública de la tienda.

### 3.4 Conectar backend y frontend

En las variables del **backend** agrega la URL pública del **frontend** (sin barra final):

```
CORS_ORIGINS=https://<dominio-del-frontend>
FRONTEND_URL=https://<dominio-del-frontend>
```

Railway reinicia el backend solo. **Escribe el dominio literal del frontend** en `CORS_ORIGINS`: una referencia como `https://${{frontend.RAILWAY_PUBLIC_DOMAIN}}` puede resolver vacía y entonces el navegador bloquea todas las llamadas por CORS.

**Cargar variables en bloque:** en la pestaña *Variables* usa **Raw Editor** y pega todas las líneas `NOMBRE=valor`. El editor las reformatea con comillas al guardarlas: es normal.

### 3.5 Primer arranque

Con `CARGAR_DATOS_DEMO=true`, al arrancar el backend: aplica las migraciones → **si la base está vacía** carga los datos de demostración (dos empresas, planes, usuarios, catálogo, las 7 prendas con su foto y su PNG del vestidor) → arranca la API. Si la base ya tiene datos **no vuelve a cargar nada** (nunca duplica), y si el volumen de imágenes estaba vacío solo repone las imágenes de demostración. Puedes dejarla en `true` o ponerla en `false` después del primer arranque.

**Ver los registros:** servicio → pestaña **Deployments** → el despliegue activo → **View logs**. Busca estas líneas del backend:

- `Datos de demostración cargados.` (primer arranque) o `La base ya tiene datos: no se carga el seed...`.
- `Uvicorn running on http://0.0.0.0:<puerto>`.

**Comprobar que funciona:**

1. `https://<dominio-del-backend>/salud` → debe mostrar `{"estado":"ok"}`.
2. `https://<dominio-del-backend>/docs` → la documentación de la API.
3. Abre `https://<dominio-del-frontend>` e inicia sesión:

   | Quién | Código de empresa | Correo |
   |---|---|---|
   | SuperAdministrador | (vacío) | `superadmin@fashionstore.com` |
   | Administrador EMP-A | `EMP-A` | `admin@modaurbana.com` |
   | Cliente EMP-A | `EMP-A` | `cliente@emp-a.com` |
   | Administrador EMP-B | `EMP-B` | `admin@estiloandino.com` |
   | Cliente EMP-B | `EMP-B` | `cliente@emp-b.com` |

   Las contraseñas de estas cuentas de demostración están en el seed ([`backend/app/seed.py`](../backend/app/seed.py)).

   Son cuentas de demostración públicas, solo para la defensa: para un uso real, cámbialas.
4. Si el backend **no arranca** y el registro dice «En producción la SECRET_KEY no puede ser la de por defecto», falta definir `SECRET_KEY`.

### 3.6 La app móvil (APK)

1. En GitHub: **Settings → Secrets and variables → Actions → pestaña Variables → New repository variable**: nombre `API_URL`, valor `https://<dominio-del-backend>/api`. (Es una **variable**, no un secreto.)
2. Para los avisos push nativos: pestaña **Secrets → New repository secret**: nombre `GOOGLE_SERVICES_JSON`, valor = el **contenido completo** de `google-services.json` (ver tabla). Sin este secreto el APK se compila igual, pero **sin Firebase** (los avisos se ven dentro de la app).
3. **Cómo obtener el APK:** en GitHub → **Actions → «Compilar APK» → Run workflow**. Al terminar, entra a la ejecución y descarga el artefacto `fashionstore-apk` (un `.zip` con `app-release.apk`; se conserva **14 días**). Pásalo al celular e instálalo permitiendo **orígenes desconocidos**. El flujo falla a propósito si `API_URL` no empieza con `https://` y termina en `/api`.

El pago con tarjeta del APK usa **Stripe en modo prueba** (hoja de pago de Stripe): la clave pública se la da el backend, no hay que configurar nada en GitHub. Tarjetas de prueba en `docs/PRUEBAS_SISTEMA.md`. Con la `flutter_stripe` el APK pesa unos 104 MB.

El release se compila **sin reducción de código** (`isMinifyEnabled = false`) por problemas de R8 con WorkManager y Stripe, que cerraban la app al abrir; por eso el APK pesa más. Después de compilar, el flujo corre una **prueba de arranque en un emulador de GitHub** (trabajo `prueba_arranque`, API 34): instala el APK, lo abre y falla si la app se cierra; el `logcat` queda como artefacto `logcat-arranque`. Si el emulador no estuviera disponible, el APK igual se entrega y el resultado se ve en el resumen del run.

El APK solo habla por **https**: ya no admite `http://`. Para probar contra el backend de tu PC por Wi‑Fi, usa una compilación de depuración (`flutter run`), que sí lo permite.

## 4. Costos

Se usa el **plan Hobby** de Railway: cuesta unos **5 USD al mes** más el uso (memoria, CPU, disco del Volume y tráfico) que exceda lo incluido. Revisa los precios vigentes en <https://railway.com/pricing> y mira el consumo en la pestaña **Usage** del proyecto. Brevo, Stripe en modo de prueba, Google Gemini (con sus límites gratuitos) y Firebase Cloud Messaging no cobran para este uso.

## Qué pasa si falla la IA

El asistente (CU-07), los reportes generativos (CU-23) y el resto de funciones de IA piden la respuesta a Gemini (o Claude). Si no hay clave, el modelo no responde a tiempo (20 s), responde con error (429 límite gratuito, 503 saturado, otros 4xx/5xx) o devuelve algo que no es JSON, **el sistema cae al modo de reglas locales** y el usuario recibe igualmente una respuesta (origen `REGLAS` en lugar de `IA`). El motivo queda en el registro del backend, por ejemplo `La IA externa (gemini) no respondió (ReadTimeout); se usa el modo de respaldo.` o `Gemini respondió 503; ...`; nunca se registran la clave, el prompt ni el cuerpo de la respuesta. Si el modelo por defecto se cuelga, se cambia con la variable `IA_MODELO` sin tocar el código.

## 5. Clave · dónde se genera · dónde se pone

| Clave | Dónde se genera | Dónde se pone |
|---|---|---|
| **SECRET_KEY** | En tu PC: `python -c "import secrets; print(secrets.token_urlsafe(48))"` y copia el resultado. | Railway → backend → Variables → `SECRET_KEY`. (Local: `backend/.env`.) |
| **Brevo · clave de API** (`BREVO_API_KEY`) | Brevo → tu nombre (arriba a la derecha) → **SMTP & API → pestaña API Keys → Generate a new API key**. Es una clave de API v3 (empieza con `xkeysib-`), no una clave SMTP. | Railway → backend → `BREVO_API_KEY`. |
| **Brevo · remitente verificado** (`BREVO_SENDER_EMAIL`) | Brevo → **Senders, Domains & Dedicated IPs → Senders → Add a sender**: escribe un correo tuyo y abre el enlace de verificación que Brevo te manda. Si en **Security → Authorized IPs** hay restricción de IP, desactívala (las IP de Railway cambian). | Railway → backend → `BREVO_SENDER_EMAIL` con **exactamente** ese correo (y `BREVO_SENDER_NAME`). Prueba: con las dos variables en tu `backend/.env`, `python scripts/probar_correo.py tu-correo@x.com`: si falla, imprime la causa. |
| **Stripe · claves de prueba** (`STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY`) | Stripe Dashboard → activa **Test mode** (interruptor arriba) → **Developers → API keys**: «Publishable key» (`pk_test_...`) y «Secret key» → *Reveal* (`sk_test_...`). Nunca uses las claves reales (`sk_live_`). | Railway → backend → las dos variables. Tarjeta de prueba: `4242 4242 4242 4242`, cualquier fecha futura y CVC. |
| **Google Gemini** (`GEMINI_API_KEY`) | <https://aistudio.google.com/apikey> → **Create API key** (gratis, sin tarjeta). Tiene límites de uso gratuitos: si se superan (error 429) el sistema responde con las reglas locales de respaldo. | Railway → backend → `GEMINI_API_KEY` (y `IA_PROVEEDOR=gemini`). El modelo por defecto es `gemini-3.1-flash-lite`; se cambia con `IA_MODELO` sin tocar el código. |
| **VAPID** (push web: `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`) | En tu PC, en `backend`: `python scripts/generar_vapid.py` agrega las dos claves a tu `backend/.env` (la privada no se imprime). Ábrelo y copia las dos líneas. | Railway → backend → `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY` y `VAPID_SUBJECT=mailto:tu-correo`. Usa **las mismas** en local y en la nube; si las cambias, los navegadores ya suscritos dejan de recibir avisos. |
| **Firebase · proyecto** (`FCM_PROYECTO`) | <https://console.firebase.google.com> → **Add project** (puedes desactivar Google Analytics). El **ID del proyecto** está en ⚙ → **Project settings → General → Project ID**. | Railway → backend → `FCM_PROYECTO`. |
| **Firebase · `google-services.json`** | En el mismo proyecto: **Add app → Android**, nombre del paquete **`com.example.fashionstore_movil`** (debe ser exactamente ese) → *Register app* → **Download google-services.json**. | Para compilar en tu PC: `movil/android/app/google-services.json` (git lo ignora). Para GitHub Actions: secreto `GOOGLE_SERVICES_JSON` con **todo** el contenido del archivo. |
| **Firebase · clave privada de la cuenta de servicio** (`FCM_CREDENCIALES_JSON`) | ⚙ → **Project settings → Service accounts → Generate new private key** → se descarga un JSON. Si al enviar el push Google responde que la API está desactivada, habilita «Firebase Cloud Messaging API» en Google Cloud Console → APIs y servicios. | Railway → backend → `FCM_CREDENCIALES_JSON`: pega el **contenido completo** del JSON como valor de una sola variable. Borra el archivo descargado de tu PC cuando termines. (Local, con archivo: `FCM_CREDENCIALES=ruta/al/archivo.json` en `backend/.env`.) |

## 6. Problemas frecuentes

| Síntoma | Causa y solución |
|---|---|
| La web muestra errores de red o de CORS | `CORS_ORIGINS` del backend no coincide con la URL del frontend (sin barra final), o `API_URL` del frontend no termina en `/api`. |
| El despliegue del backend falla en el health check | Mira los registros: suele ser `SECRET_KEY` sin definir, `DATABASE_URL` mal referenciada (`${{Postgres.DATABASE_URL}}`) o una migración con error. |
| Después de redesplegar, las imágenes de los productos no cargan | Falta el Volume en `/app/media`, o `MEDIA_DIR` no es `/app/media`. Con el Volume y `CARGAR_DATOS_DEMO=true`, las imágenes de demostración se reponen solas. |
| «No se pudo enviar el correo...» al recuperar la contraseña | Brevo rechazó el envío. El detalle está en los registros del backend (remitente no verificado, clave de API incorrecta o IP no autorizada). Pruébalo con `python scripts/probar_correo.py`. |
| El asistente de IA responde con reglas simples | No hay `GEMINI_API_KEY`, o se alcanzó el límite gratuito (429), o el modelo está saturado (503) o no responde (`ReadTimeout` en el registro): es el modo de respaldo. Ver «Qué pasa si falla la IA». |
| «Application failed to respond» en el dominio público | El dominio no apunta al puerto del contenedor: el **puerto de destino** debe ser 8080 y el backend necesita `PORT=8080`. |
| Railway no encuentra el Dockerfile | Falta el **Root Directory** del servicio (`/backend` o `/frontend`). |
| El navegador bloquea las llamadas a la API por CORS | `CORS_ORIGINS` quedó vacío (referencia `${{...}}` sin resolver): escribe el dominio literal del frontend. |
| El push web no pide permiso | El navegador exige HTTPS (Railway ya lo da) y que la PWA esté cargada con el service worker; abre el sitio en una pestaña nueva e inicia sesión como Cliente. |
| El APK no recibe push | Se compiló sin `google-services.json` (revisa el aviso amarillo del flujo), el paquete de la app en Firebase no es `com.example.fashionstore_movil`, o falta `FCM_PROYECTO`/`FCM_CREDENCIALES_JSON` en el backend. |

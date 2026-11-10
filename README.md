# FashionStore SaaS

Plataforma de comercio electrónico **multitenant** para tiendas de ropa: cada empresa (tenant) tiene su catálogo, sucursales, inventario, ventas, usuarios y plan de suscripción, aislados por `empresa_id`. Incluye panel web (PWA), aplicación móvil Android y backend REST.

Proyecto de **Sistemas de Información 2** (INF 412-SA, UAGRM) · Grupo 20.

**En producción (Railway)**

- Web: <https://frontend-production-13a8.up.railway.app>
- APK: se compila en GitHub Actions (ver [Aplicación móvil](#aplicación-móvil-apk))

## Contexto del sistema

| Actor | Qué hace |
|---|---|
| **SuperAdministrador** | Gestiona las empresas, los planes (Prueba gratuita, Básico, Profesional), las suscripciones y la bitácora de la plataforma |
| **Administrador** | Gestiona su empresa: sucursales, usuarios, catálogo, promociones, proveedores, reportes, indicadores, plan y bitácora |
| **Encargado / Cajero** | Operan la sucursal: inventario, recepción de mercadería, reservas en mostrador, punto de venta, devoluciones y cambios, cierre de caja |
| **Cliente** | Consulta el catálogo, usa el vestidor virtual, arma su carrito, paga con tarjeta, reserva prendas y descarga sus comprobantes |
| **Proveedor** | Portal para ver y atender los pedidos de abastecimiento |

**Funciones principales**

- Multitenancia con roles y permisos; las funciones disponibles dependen del plan de la empresa (por ejemplo, la IA solo en el plan Profesional).
- Catálogo con variantes (color × talla), existencias por sucursal, promociones y fotografías.
- Carrito, compra con retiro o entrega a domicilio, pago con tarjeta (Stripe en modo de prueba), comprobante en PDF.
- Reservas en sucursal con código y avisos (campana y notificaciones push).
- Punto de venta, devoluciones y cambios, cierre de caja.
- **Modo sin conexión** en web y móvil: catálogo descargado, reservas, compras y ventas de contado en una cola que se sincroniza sola al volver la red, con estados y manejo de conflictos.
- **Vestidor virtual** en el móvil: prueba de la prenda con la cámara (detección de pose en el dispositivo).
- IA: asistente de compras, reportes generativos (escritos o por voz) y analítica con ML; con respaldo por reglas si no hay clave de IA.
- Bitácora de auditoría y notificaciones push (web y móvil).

**Estado:** los casos de uso del enunciado están implementados y desplegados. En curso: vestidor virtual también en la web, funciones del Cliente completas sin conexión, exportación de reportes y nueva navegación del móvil.

## Tecnología

| Carpeta | Contenido | Tecnología |
|---|---|---|
| `backend/` | API REST, reglas de negocio y migraciones | Python 3.13 · FastAPI · SQLAlchemy · Alembic · PostgreSQL |
| `frontend/` | Paneles web y tienda, PWA instalable | Angular 21 · Service Worker · IndexedDB |
| `movil/` | Aplicación móvil para el Cliente y el personal de tienda | Flutter · Dart · SQLite · ML Kit |
| `.github/workflows/` | Compilación del APK | GitHub Actions |

Servicios externos (todos con plan gratuito o modo de prueba): Brevo (correo), Stripe (pagos de prueba), Google Gemini (IA), Firebase Cloud Messaging (push móvil).

## Cómo correr el sistema en local

Los comandos son para Windows (PowerShell). Se usan **dos terminales**: una para el backend y otra para la web.

### Requisitos

- [Python 3.13](https://www.python.org/downloads/)
- [Node.js 22 o superior](https://nodejs.org/) (incluye npm)
- [PostgreSQL 16 o superior](https://www.postgresql.org/download/) en marcha
- Para el móvil: Flutter y Android Studio (ver [`movil/README.md`](movil/README.md))

### 1. Clonar

```powershell
git clone https://github.com/Beimar781/fashionstore-saas.git
cd fashionstore-saas
```

### 2. Backend (terminal 1)

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Abre `backend/.env` y ajusta:

- `DATABASE_URL`: tu usuario y contraseña de PostgreSQL, por ejemplo `postgresql+psycopg://postgres:MI_CLAVE@localhost:5432/fashionstore_saas`.
- `SECRET_KEY`: cualquier texto largo.

Con el entorno virtual activado:

```powershell
python scripts/crear_bd.py      # crea la base de datos
alembic upgrade head            # crea las tablas
python -m app.seed              # roles, planes, SuperAdmin y dos empresas de ejemplo con catálogo, existencias y datos de demostración
uvicorn app.main:app --reload   # inicia la API
```

API en <http://localhost:8000>.

### 3. Web (terminal 2)

```powershell
cd frontend
npm install
npm start
```

Abre <http://localhost:4200>.

### 4. Móvil (opcional)

Con el backend en marcha y un emulador Android o un celular con depuración USB:

```powershell
cd movil
flutter pub get
flutter run
```

El emulador usa `http://10.0.2.2:8000/api` por defecto. Para un celular físico en la misma red Wi‑Fi: `flutter run --dart-define=API_URL=http://192.168.X.X:8000/api`. Detalles en [`movil/README.md`](movil/README.md).

### Pruebas automáticas

```powershell
cd backend ; python -m pytest -q          # API y reglas de negocio
cd frontend ; npm run build               # compila la web de producción
cd movil ; flutter analyze ; flutter test # análisis y pruebas del móvil
```

### Opcionales (sin ellos todo funciona con modos simulados)

Se definen en `backend/.env` (el archivo nunca se sube a git; la lista completa está en `backend/.env.example`):

| Variable | Para qué |
|---|---|
| `STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY` | Pagos con Stripe en modo de prueba (`sk_test_…`, `pk_test_…`). Sin ellas el pago es simulado |
| `GEMINI_API_KEY` (o `IA_PROVEEDOR=anthropic` + `ANTHROPIC_API_KEY`) | IA real. Sin clave se usan reglas de respaldo |
| `BREVO_API_KEY`, `BREVO_SENDER_EMAIL` | Envío real de correos. Sin ellas el enlace de recuperar contraseña se imprime en la terminal del backend |
| `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY` | Push web (se generan con `python scripts/generar_vapid.py`) |
| `FCM_PROYECTO`, `FCM_CREDENCIALES` | Push nativo del móvil (Firebase) |
| `CARGAR_DATOS_DEMO=true` | Carga el seed solo si la base está vacía (se usa en Railway) |

## Cuentas de demostración

El campo **Código de empresa** se deja vacío solo para el SuperAdministrador.

| Rol | Código de empresa | Correo | Contraseña |
|---|---|---|---|
| SuperAdministrador | *(vacío)* | superadmin@fashionstore.com | Super2026* |
| Administrador | EMP-A (plan Básico) | admin@modaurbana.com | Demo2026* |
| Administrador | EMP-B (plan Profesional) | admin@estiloandino.com | Demo2026* |
| Encargado | EMP-A o EMP-B | encargado@tienda.com | Demo2026* |
| Cajero | EMP-A o EMP-B | cajero@tienda.com | Demo2026* |
| Cliente | EMP-A | cliente@emp-a.com | Demo2026* |
| Cliente | EMP-B | cliente@emp-b.com | Demo2026* |
| Proveedor (portal) | EMP-A o EMP-B | proveedor@tienda.com | Demo2026* |

EMP-A tiene el plan **Básico** (sin IA: los reportes con IA, la analítica con ML y el asistente salen bloqueados). EMP-B tiene el plan **Profesional** (todo habilitado).

**Otras empresas del despliegue.** EMP-C (**Moda Juvenil**, plan Básico) se creó a mano desde el panel del SuperAdministrador; su administrador es `Juvenil@gmail.com` con la clave que se le asignó al crearla (no se escribe aquí). EMP-D a EMP-G las crea y puebla `scripts/poblar_via_api.py`; todas usan la contraseña `Demo2026*`:

| Código | Empresa | Plan | Sucursales | Administrador | Encargados (uno por sucursal) |
|---|---|---|---|---|---|
| EMP-D | Boutique Altiplano S.A. | Profesional | 3 | admin@boutiquealtiplano.com.bo | encargado1@, encargado2@ y encargado3@boutiquealtiplano.com.bo |
| EMP-E | Ropa Valle Dorado Ltda. | Básico | 2 | admin@valledorado.com.bo | encargado1@ y encargado2@valledorado.com.bo |
| EMP-F | Textiles del Oriente S.R.L. | Básico | 2 | admin@textilesdeloriente.com.bo | encargado1@ y encargado2@textilesdeloriente.com.bo |
| EMP-G | Moda Sucre Express | Prueba gratuita | 1 | admin@modasucreexpress.com.bo | encargado1@modasucreexpress.com.bo |

**Nota.** El inicio de sesión del Administrador, el Encargado, el Cajero y el Cliente pide el **código de empresa** (EMP-A a EMP-G). El SuperAdministrador (`superadmin@fashionstore.com` / `Super2026*`) lo deja vacío. EMP-D a EMP-G tienen las mismas 10 prendas con foto que EMP-B.

### Poblar el despliegue

`scripts/poblar_via_api.py` crea EMP-D a EMP-G (con sus administradores, sucursales y encargados) y copia a cada una el catálogo de EMP-B con fotos, PNG del vestidor y existencias, todo por la API (necesita `requests` y `pillow`, que ya están en `backend/requirements.txt`):

```bash
python scripts/poblar_via_api.py --url https://fashionstore-saas-production.up.railway.app \
  --super-email superadmin@fashionstore.com --super-pass '<CLAVE_SUPERADMIN>' \
  --plantilla-pass '<CLAVE_ADMIN>' --admin-pass '<CLAVE_ADMIN>'
```

Es **idempotente** (se puede correr varias veces: lo que ya existe se omite) y **no modifica la aplicación**: solo usa los endpoints públicos. Con `--destino-existente CODIGO,correo,clave` también copia el catálogo a una empresa que ya existe (por ejemplo EMP-C). Con `--url http://localhost:8000` sirve para probarlo en local.

**Tarjetas de prueba de Stripe** (cualquier fecha futura y cualquier CVC): `4242 4242 4242 4242` aprueba · `4000 0000 0000 0002` rechaza · `4000 0027 6000 3184` pide 3D Secure.

## Aplicación móvil (APK)

El APK se compila en GitHub: **Actions → «Compilar APK» → Run workflow**. Al terminar, en la ejecución se descarga el artefacto `fashionstore-apk` (un `.zip` con `app-release.apk`, disponible 14 días). Se instala en Android permitiendo «instalar apps de orígenes desconocidos». El flujo incluye una prueba de arranque en un emulador. El APK se conecta al backend de Railway por HTTPS.

## Problemas frecuentes

- **`password authentication failed`**: la contraseña de `DATABASE_URL` no es la de tu PostgreSQL.
- **`.venv\Scripts\Activate.ps1` no se puede ejecutar**: en PowerShell, `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.
- **La web carga pero no inicia sesión**: confirma que el backend sigue corriendo en el puerto 8000.
- **Empezar de cero**: elimina la base `fashionstore_saas` (pgAdmin o `psql`) y repite `crear_bd`, `alembic upgrade head` y `app.seed`.
- **El APK no abre o no conecta**: debe instalarse la versión más reciente del artefacto; el APK solo habla con el backend por HTTPS.

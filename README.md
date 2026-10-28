# FashionStore SaaS

Plataforma de comercio electrónico **multitenant** para tiendas de ropa. Proyecto de Sistemas de Información 2 (Grupo 20).

| Carpeta | Contenido | Tecnología |
|---|---|---|
| `backend/` | API REST, reglas de negocio y migraciones | Python · FastAPI · SQLAlchemy · Alembic · PostgreSQL |
| `frontend/` | Paneles web (SuperAdmin y Administrador), PWA instalable | Angular · Service Worker · IndexedDB |
| `movil/` | Aplicación móvil con almacenamiento local | Flutter · Dart · SQLite |
| `docs/` | Trazabilidad de casos de uso y pendientes | — |

## Requisitos

- [Python 3.13](https://www.python.org/downloads/)
- [Node.js 22 o superior](https://nodejs.org/) (incluye npm)
- [PostgreSQL 16 o superior](https://www.postgresql.org/download/) en marcha (con o sin pgAdmin)
- Para la app móvil: Flutter y Android Studio (ver [`movil/README.md`](movil/README.md))

## Instalación

Los comandos son para Windows (PowerShell). Se usan **dos terminales**: una para el backend y otra para la web.

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

Abre `backend/.env` y cambia **tu usuario y contraseña de PostgreSQL** en `DATABASE_URL`
(por ejemplo `postgresql+psycopg://postgres:MI_CLAVE@localhost:5432/fashionstore_saas`).
En `SECRET_KEY` escribe cualquier texto largo.

Luego, con el entorno virtual activado:

```powershell
python scripts/crear_bd.py      # crea la base de datos
alembic upgrade head            # crea las tablas
python -m app.seed              # carga roles, planes, SuperAdmin y dos empresas de ejemplo (con catálogo y existencias)
uvicorn app.main:app --reload   # inicia la API
```

La API queda en <http://localhost:8000> y su documentación en <http://localhost:8000/docs>.

### 3. Web (terminal 2)

```powershell
cd frontend
npm install
npm start
```

Abre <http://localhost:4200>.

## Cuentas iniciales

El campo **Código de empresa** se deja vacío solo para el SuperAdministrador.

| Rol | Código de empresa | Correo | Contraseña |
|---|---|---|---|
| SuperAdministrador | *(vacío)* | superadmin@fashionstore.com | Super2026* |
| Administrador | EMP-A | admin@modaurbana.com | Demo2026* |
| Administrador | EMP-B | admin@estiloandino.com | Demo2026* |
| Encargado | EMP-A o EMP-B | encargado@tienda.com | Demo2026* |
| Cajero | EMP-A o EMP-B | cajero@tienda.com | Demo2026* |
| Cliente | EMP-A | cliente@emp-a.com | Demo2026* |
| Proveedor (portal) | EMP-A o EMP-B | proveedor@tienda.com | Demo2026* |

## Catálogo de ejemplo

El seed crea para EMP-A (Moda Urbana) y EMP-B (Estilo Andino) categorías, tallas, colores, una temporada, una colección, productos con
variantes, existencias por sucursal y una promoción. El Administrador gestiona todo en **Productos**, **Categorías, tallas y colores**,
**Temporadas y colecciones** y **Promociones**; el Cliente lo ve en **Catálogo**. Un cliente nuevo se registra en `/registro` con el código de la tienda.
También deja dos reservas del cliente demo en la primera sucursal (una pendiente y una preparada): el Encargado las ve en **Reservas** y las atiende con su código en **Atención en mostrador**; el cliente las ve en **Mis reservas**, y la campana 🔔 muestra los avisos (RF11).
El seed también deja un proveedor con acceso al portal, un lote en tránsito (el Encargado lo recibe en **Recepción de mercadería**) y una propuesta de producto por revisar (**Abastecimiento**).
Las fotografías de los productos se guardan en `backend/media/` (una carpeta por empresa); si actualizó el proyecto, ejecute de nuevo
`pip install -r requirements.txt` y `alembic upgrade head`.

## Recuperar contraseña

En el inicio de sesión, **¿Olvidaste tu contraseña?** pide el correo y genera un enlace de un solo uso.
Sin configurar un servicio de correo, el enlace aparece en la terminal del backend; copia esa dirección en el navegador.

## Aplicación móvil

Instrucciones en [`movil/README.md`](movil/README.md). Requiere el backend en ejecución.

## Problemas frecuentes

- **`password authentication failed`**: la contraseña de `DATABASE_URL` no es la de tu PostgreSQL.
- **`.venv\Scripts\Activate.ps1` no se puede ejecutar**: abre PowerShell y ejecuta `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.
- **La web carga pero no inicia sesión**: confirma que el backend sigue corriendo en el puerto 8000.
- **Para empezar de cero**: elimina la base `fashionstore_saas` desde pgAdmin y repite los pasos `crear_bd`, `alembic` y `seed`.

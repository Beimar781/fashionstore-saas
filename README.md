# FashionStore SaaS — Segundo parcial · Sistemas de Información 2 (Grupo 20)

Plataforma de comercio electrónico **multitenant** para tiendas de ropa. Un solo repositorio:

| Carpeta | Contenido | Tecnología |
|---|---|---|
| `backend/` | API REST, reglas de negocio, aislamiento por empresa, migraciones | Python · FastAPI · SQLAlchemy · Alembic · PostgreSQL |
| `frontend/` | Paneles web (SuperAdmin, Administrador) y tienda — **PWA** instalable y offline | Angular · Service Worker · Web App Manifest · IndexedDB |
| `movil/` | Aplicación móvil con persistencia local | Flutter · Dart · SQLite |
| `docs/` | Trazabilidad CU → código → pruebas, pendientes por lote | — |

## Estado: Presentación 1 (Lote 1)
CU-02 Iniciar sesión · CU-13 Usuarios y roles · CU-14 Ciudades y sucursales · CU-33 Empresas (tenants) · CU-34 Planes · CU-35 Suscripciones.
Detalle y lo que sigue: [`docs/TRAZABILIDAD.md`](docs/TRAZABILIDAD.md) y [`docs/PENDIENTES.md`](docs/PENDIENTES.md).

## 1. Backend (Windows / PowerShell)
```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env          # editar DATABASE_URL con TU usuario y contraseña de PostgreSQL (los de pgAdmin)
python scripts/crear_bd.py      # crea la base fashionstore_saas
alembic upgrade head            # crea las tablas (script 3.5.4 del documento)
python -m app.seed              # roles, planes, SuperAdmin y 2 empresas de prueba
uvicorn app.main:app --reload   # API en http://localhost:8000  ·  documentación: http://localhost:8000/docs
```
Pruebas automatizadas (usan una base aparte `fashionstore_test`, que se crea sola):
```powershell
$env:TEST_DATABASE_URL="postgresql+psycopg://postgres:SU_CLAVE@localhost:5432/fashionstore_test"
python -m pytest -q
```

## 2. Web
```powershell
cd frontend
npm install
npm start                        # http://localhost:4200
```

## 3. Móvil (Flutter)
Ver [`movil/README.md`](movil/README.md).

## Cuentas de prueba (seed)
| Rol | Código de empresa | Correo | Contraseña |
|---|---|---|---|
| SuperAdministrador | *(vacío)* | superadmin@fashionstore.com | Super2026* |
| Administrador | EMP-A (plan Básico) | admin@modaurbana.com | Demo2026* |
| Administrador | EMP-B (plan Profesional) | admin@estiloandino.com | Demo2026* |
| Encargado / Cajero / Cliente | EMP-A o EMP-B | encargado@tienda.com · cajero@tienda.com · cliente@emp-a.com | Demo2026* |

El mismo correo (`cajero@tienda.com`) existe en las dos empresas: cada una solo ingresa con su código (RN09).

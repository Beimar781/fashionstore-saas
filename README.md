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
También deja en cada empresa una compra pagada del cliente demo (con su comprobante y su tarjeta guardada) y un carrito listo para pagar.
**Pago con tarjeta:** sin claves de Stripe, el pago es simulado y se prueba con las tarjetas de prueba que muestra la pantalla de pago (por ejemplo
`4242 4242 4242 4242` aprueba y `4000 0000 0000 9995` rechaza por fondos insuficientes). Para usar Stripe en modo de prueba, agregue en `backend/.env`
`STRIPE_SECRET_KEY=sk_test_...` y `STRIPE_PUBLISHABLE_KEY=pk_test_...` (claves de prueba, nunca reales) y reinicie el backend.
**Punto de venta:** `cajero@tienda.com` entra a **Caja** (escanear o buscar prendas, cobrar en efectivo o con tarjeta de prueba, imprimir el comprobante) y
`encargado@tienda.com` a **Ventas de la sucursal** (resumen del día, cierre de caja y tickets). El seed deja ventas de caja de ejemplo. Para ver el comprobante interno
temporal de la ficha CU-30, agregue `IMPUESTOS_SIMULAR_FALLA=true` en `backend/.env` y reinicie el backend.
**Devoluciones y cambios (CU-41):** `cajero@tienda.com` o `encargado@tienda.com` entran a **Devoluciones y cambios**, escriben el N.° de comprobante de una venta (por ejemplo el que
muestra el ticket de **Caja**), eligen las prendas y registran la devolución o el cambio (si la prenda nueva cuesta más, el cliente paga la diferencia en efectivo o con tarjeta de prueba); la prenda vuelve al inventario de su sucursal y se imprime la nota. El Administrador
fija el plazo (15 días por defecto) y consulta todas las notas en **Devoluciones y cambios**. El seed deja una devolución de ejemplo por empresa.
**Reportes, IA y plan (Fase G):** el seed deja 10 semanas de ventas de demostración. EMP-A (`admin@modaurbana.com`) tiene el plan **Básico**: ve **Reportes**, **Indicadores** y **Mi plan**, y
**Reportes con IA**, **Analítica con ML** y el **Asistente** del cliente salen bloqueados (🔒). EMP-B (`admin@estiloandino.com`, plan **Profesional**) tiene todo: pida un reporte escrito o dictado con el micrófono
(Chrome o Edge), vea el pronóstico de demanda y, como `cliente@emp-b.com`, pruebe el **Asistente de compras**. El asistente aprende de lo que el cliente compra, busca y mira (el seed ya deja búsquedas y prendas vistas del cliente demo), y el cliente puede apagarlo o borrarlo en **Mi privacidad**. Sin clave de IA todo funciona con reglas de respaldo; para usar Claude agregue
`ANTHROPIC_API_KEY=` en `backend/.env` (la clave nunca va en el código ni se sube a git) y reinicie el backend.
**Modo sin conexión (Fase H):** el Cajero (`cajero@tienda.com`), el Encargado y el Cliente tienen **Modo sin conexión**: descargue el catálogo con Internet, apague la red (en Chrome: F12 → Network → Offline),
registre una venta de contado (o una reserva, como cliente) y vuelva a conectar: se envía sola y pasa de «Registrada» a «Confirmada». El seed deja una venta que no alcanzó en el inventario: el Encargado la ve en
**Conflictos de sincronización** y la reintenta o la descarta. En el móvil (`flutter run`) es la misma pantalla «Modo sin conexión»; el catálogo descargado también se usa si no hay Internet.
**Bitácora (Fase J):** el Administrador (`admin@modaurbana.com`) entra a **Bitácora** y ve solo lo de su empresa; el SuperAdministrador (`superadmin@fashionstore.com`) ve la de todas las empresas con la columna **Empresa**
y las operaciones de la plataforma. Cada inicio y cierre de sesión, cada intento fallido y cada alta, cambio, cobro o devolución queda registrado con quién, qué, cuándo y la IP; las consultas no. Se puede filtrar y buscar, y no se puede
editar ni borrar. El seed deja unas 40 filas de ejemplo.
**Plan de prueba y avisos push (Fase K):** el SuperAdministrador ve tres planes; **Prueba gratuita** dura 1 mes, una sola vez por empresa, sin IA. Los avisos push funcionan en modo simulado sin claves: como cliente, abra la campana 🔔 y
pulse **Activar avisos**; cuando el Cajero registre una devolución o cambio de una venta vinculada a su correo, le llega el aviso (campana y registro en `push_envios`). Para Web Push de verdad ejecute `python scripts/generar_vapid.py`
(agrega las claves VAPID a `backend/.env` sin imprimirlas) y reinicie el backend; para el móvil real se necesita una cuenta de servicio de Firebase (`FCM_CREDENCIALES` y `FCM_PROYECTO` en `backend/.env`).
**Compra sin conexión (Fase K):** como cliente, en **Modo sin conexión** elija «Comprar», descargue el catálogo, apague la red y registre la compra; al volver la conexión se verifica el stock: si alcanza, queda un pedido por pagar (avisa la campana, el push y un mensaje emergente) y se paga con
tarjeta en **Mis compras**; si la prenda se agotó, el aviso dice que no se cobró nada. Para ver el conflicto: deje una sola unidad, compre esa prenda con otro cliente y sincronice la compra sin conexión del primero; el Encargado la ve en **Conflictos de sincronización**
y, si fue una venta de contado ya cobrada en caja, puede **descartarla devolviendo el dinero** (se revisa la prenda y la devolución pasa por el inventario con su talla y color). En **Devoluciones y cambios** el Cajero ahora marca la revisión de la prenda (sin daños, sin desgaste, con etiquetas).
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

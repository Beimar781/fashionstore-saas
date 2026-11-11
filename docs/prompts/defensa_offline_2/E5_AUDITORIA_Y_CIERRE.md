# E5 · Auditoría de «sin conexión», pruebas de punta a punta y cierre

(Pega antes `00_BLOQUE_COMUN.md`. Corre al final, cuando E1–E4 estén hechos.)

## 1. Auditoría automática de pantallas (busca errores parecidos que no vimos)
- **Web:** script o spec que recorra todas las rutas por rol (`app.routes.ts` y los `*.routes.ts`) con la red apagada (simulación Y `context.setOffline(true)` de Playwright con el service worker activo en un build de producción) y falle si en algún momento hay «Cargando…» más de 3 s, un vacío engañoso, o un botón de escritura habilitado que no se pueda encolar ni deshabilitar. Arrojar una tabla actor × pantalla × resultado y guardarla en `docs/AUDITORIA_OFFLINE.md`.
- **Móvil:** revisar con `grep` y pruebas todos los `CircularProgressIndicator`, `catch (ApiException)` y `FutureBuilder` de `lib/` para que cada uno tenga salida sin conexión; listar los que se corrigieron.
- **Código:** buscar patrones del mismo tipo que los ya hallados (`ngOnInit` que solo carga `if (online)`, `cargando = signal(true)` sin ruta de error, endpoints llamados sin respaldo local, `ApiException` sin tratar `sinConexion`) y corregirlos o dejarlos documentados como «necesita Internet».

## 2. Recorridos de la demo (pruebas automáticas)
Para cada guion de `docs/PRUEBAS_SISTEMA.md` sección 16 (a–e): Cajero vende sin red y sincroniza; dos cajeros y la última unidad (conflicto con monto a devolver); Cliente compra con tarjeta guardada sin red y se cobra al sincronizar (Stripe en modo simulado); Encargado/Proveedor/Admin con y sin red; reporte CU-23 por sucursal. Que existan en web y, donde aplique, en móvil.

## 3. Datos de demo
Script idempotente `scripts/preparar_demo.py` (sin credenciales en el código): asegura en EMP-B stock en las sucursales del cajero, 2 cajeros, 1 cliente con tarjeta guardada de prueba, productos con foto, y un catálogo mínimo en EMP-C. Documentar cómo correrlo contra Railway.

## 4. Suite completa y cierre
- `cd backend && python -m pytest -q`, `cd frontend && npm run build` y `npm test`, y en el móvil `flutter analyze` y `flutter test`. Si algo falla, corregir antes de seguir.
- Actualizar `docs/PRUEBAS_SISTEMA.md` (sección de la demo), `docs/TRAZABILIDAD.md` y `docs/MENSAJES_PENDIENTES_WORD.md`.
- Commit y push (sin coautoría). Recordar al usuario: lanzar «Compilar APK» (GitHub Actions, `workflow_dispatch`), esperar el despliegue de Railway y correr `python scripts/humo_produccion.py <url>`.
- Mostrar el resumen en español con la tabla de la auditoría.

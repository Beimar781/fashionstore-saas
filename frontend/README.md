# FashionStore · Web (Angular PWA)

- `npm install` y luego `npm start` → http://localhost:4200 (el backend debe estar en http://localhost:8000).
- **Probar la PWA** (Service Worker, instalación y modo sin conexión; solo existe en la compilación de producción):
  `npm run build:pwa` y `npm run serve:pwa`, abrir http://localhost:4200 en Chrome (icono de instalar en la barra de direcciones).
  Para probar offline: iniciar sesión, visitar Sucursales, y en DevTools → Network marcar *Offline* y recargar.
- Estructura: `core/` (auth, API, offline/IndexedDB, interceptores), `layout/`, `features/<paquete>/` con carga diferida
  (`auth`, `plataforma`, `administracion`).

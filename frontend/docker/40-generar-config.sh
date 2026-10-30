#!/bin/sh
# Genera /config.js con la dirección de la API (variable API_URL) cada vez que arranca el contenedor.
# index.html lo carga antes que la aplicación y api.config.ts lee window.__API_URL__. Sin API_URL se usa /api (mismo origen).
set -e
DESTINO=/usr/share/nginx/html/config.js
if [ -n "$API_URL" ]; then
  case "$API_URL" in
    http://*|https://*) ;;
    *) echo "API_URL debe empezar con http:// o https:// (por ejemplo https://backend-produccion.up.railway.app/api)"; exit 1 ;;
  esac
  case "$API_URL" in
    *[\"\'\\\<\>\ ]*) echo "API_URL tiene caracteres no permitidos"; exit 1 ;;
  esac
  echo "window.__API_URL__ = \"$API_URL\";" > "$DESTINO"
  echo "config.js generado con API_URL=$API_URL"
else
  echo "// sin API_URL: la aplicación usa /api (mismo origen)" > "$DESTINO"
  echo "API_URL no está definida: la aplicación usará /api"
fi

# Etapa 1: compila la PWA de Angular
FROM node:22-alpine AS compilar
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

# Etapa 2: la sirve con nginx en el puerto PORT que da Railway
FROM nginx:1.27-alpine
# nginx reemplaza ${PORT} de la plantilla al arrancar; la dirección de la API NO se graba al compilar: el script genera /config.js con la variable API_URL
COPY docker/nginx.conf.template /etc/nginx/templates/default.conf.template
COPY docker/40-generar-config.sh /docker-entrypoint.d/40-generar-config.sh
RUN chmod +x /docker-entrypoint.d/40-generar-config.sh
COPY --from=compilar /app/dist/frontend/browser /usr/share/nginx/html
ENV PORT=8080
EXPOSE 8080

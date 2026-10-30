FROM python:3.12-slim
WORKDIR /app
# Las imágenes de productos y los PNG del vestidor van en /app/media: en Railway se monta ahí un Volume para que sobrevivan a cada despliegue
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 MEDIA_DIR=/app/media
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN mkdir -p /app/media
EXPOSE 8000
# 1) migraciones  2) comprobaciones y datos de demostración (solo con CARGAR_DATOS_DEMO=true y base vacía)  3) API en el puerto PORT que da Railway.
# --proxy-headers: detrás del proxy de Railway, la bitácora guarda la IP real del cliente (no la del proxy).
CMD ["sh", "-c", "alembic upgrade head && python -m app.arranque && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]

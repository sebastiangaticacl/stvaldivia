# Dockerfile para Sistema BIMBA en Google Cloud Run
# Optimizado para producción con soporte para Socket.IO y notificaciones

FROM python:3.9-slim

# Establecer directorio de trabajo
WORKDIR /app

# Variables de entorno para Python
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements
COPY requirements.txt .

# Instalar dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Instalar gunicorn y eventlet para Socket.IO
RUN pip install --no-cache-dir gunicorn eventlet

# Copiar código de la aplicación
COPY . .

# Crear directorio para base de datos (se usará /tmp en Cloud Run)
RUN mkdir -p /app/instance

# Exponer puerto (Cloud Run usa PORT env var)
EXPOSE 8080

# Usuario no-root para seguridad
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# Comando de inicio con gunicorn y eventlet para Socket.IO
# Cloud Run requiere escuchar en 0.0.0.0 y usar la variable PORT
CMD exec gunicorn \
    --bind 0.0.0.0:${PORT:-8080} \
    --workers 2 \
    --worker-class eventlet \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    "app:create_app()"

#!/bin/bash
# Script para reiniciar gunicorn correctamente en producción

cd /var/www/stvaldivia
source venv/bin/activate

# Matar procesos de gunicorn existentes
sudo pkill -9 -f 'gunicorn.*app:create_app' || true
sleep 2

# Iniciar gunicorn correctamente (sin paréntesis en create_app)
gunicorn \
    --pythonpath /var/www/stvaldivia \
    --bind 127.0.0.1:5001 \
    --workers 4 \
    --worker-class eventlet \
    --timeout 30 \
    --access-logfile /var/www/stvaldivia/logs/access.log \
    --error-logfile /var/www/stvaldivia/logs/error.log \
    --daemon \
    app:create_app

sleep 3

# Verificar que está corriendo
if ps aux | grep -E 'gunicorn.*app:create_app' | grep -v grep > /dev/null; then
    echo "✅ Gunicorn iniciado correctamente"
    ps aux | grep -E 'gunicorn.*app:create_app' | grep -v grep | head -2
else
    echo "❌ Error: Gunicorn no está corriendo"
    exit 1
fi

# Probar conexión
curl -s http://127.0.0.1:5001/api/v1/public/evento/hoy > /dev/null && echo "✅ Aplicación respondiendo" || echo "⚠️  Aplicación no responde"




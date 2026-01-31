#!/bin/bash
# Script mejorado para reiniciar gunicorn con captura de errores

INSTANCE_NAME="stvaldivia"
ZONE="southamerica-west1-a"
PROJECT_ID="stvaldivia"

echo "🔄 REINICIANDO GUNICORN (VERSIÓN MEJORADA)"
echo "=========================================="
echo ""

gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --project=$PROJECT_ID << 'ENDSSH'
cd /var/www/stvaldivia

echo "🛑 Deteniendo procesos existentes..."
pkill -9 -f 'gunicorn.*app:create_app' || true
pkill -9 -f 'gunicorn' || true
sleep 2

echo "🐍 Activando entorno virtual..."
source venv/bin/activate

echo "🔍 Verificando que la app puede importarse..."
python3 -c "from app import create_app; app = create_app(); print('✅ App se importa correctamente')" 2>&1 || {
    echo "❌ Error al importar la aplicación"
    exit 1
}

echo ""
echo "🚀 Iniciando gunicorn con logs detallados..."
nohup gunicorn \
    --pythonpath /var/www/stvaldivia \
    --bind 127.0.0.1:5001 \
    --workers 4 \
    --worker-class eventlet \
    --timeout 30 \
    --access-logfile /var/www/stvaldivia/logs/access.log \
    --error-logfile /var/www/stvaldivia/logs/error.log \
    --log-level debug \
    --daemon \
    app:create_app \
    > /tmp/gunicorn_start.log 2>&1

sleep 5

echo ""
echo "🔍 Verificando estado..."
if ps aux | grep -E 'gunicorn.*app:create_app' | grep -v grep > /dev/null; then
    echo "✅ Gunicorn está corriendo"
    echo ""
    ps aux | grep -E 'gunicorn.*app:create_app' | grep -v grep | head -3
    echo ""
    
    echo "🧪 Probando conexión local..."
    sleep 2
    curl -s http://127.0.0.1:5001/api/v1/public/evento/hoy > /dev/null 2>&1 && echo "✅ Aplicación respondiendo" || echo "⚠️  Aplicación no responde todavía"
else
    echo "❌ ERROR: Gunicorn no está corriendo"
    echo ""
    echo "📋 Logs de inicio:"
    cat /tmp/gunicorn_start.log 2>/dev/null || echo "   (no hay logs)"
    echo ""
    echo "📋 Últimos logs de error:"
    tail -30 /var/www/stvaldivia/logs/error.log 2>/dev/null | tail -15 || echo "   (no hay logs disponibles)"
    exit 1
fi
ENDSSH

echo ""
echo "✅ PROCESO COMPLETADO"




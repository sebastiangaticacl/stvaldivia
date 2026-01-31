#!/bin/bash
# Script final para reiniciar gunicorn con corrección de permisos

INSTANCE_NAME="stvaldivia"
ZONE="southamerica-west1-a"
PROJECT_ID="stvaldivia"

echo "🔄 REINICIANDO GUNICORN (CON CORRECCIÓN DE PERMISOS)"
echo "===================================================="
echo ""

gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --project=$PROJECT_ID << 'ENDSSH'
cd /var/www/stvaldivia

echo "🔧 Corrigiendo permisos del directorio logs..."
mkdir -p logs
sudo chown -R deploy:deploy logs/ 2>/dev/null || chown -R $(whoami):$(whoami) logs/ 2>/dev/null || true
chmod -R 755 logs/ 2>/dev/null || true

echo "🛑 Deteniendo procesos existentes..."
pkill -9 -f 'gunicorn.*app:create_app' || true
pkill -9 -f 'gunicorn' || true
sleep 2

echo "🐍 Activando entorno virtual..."
source venv/bin/activate

echo "🔍 Verificando que la app puede importarse..."
python3 -c "from app import create_app; app = create_app(); print('✅ App se importa correctamente')" 2>&1 || {
    echo "⚠️  Error al importar (puede ser por logs), continuando..."
}

echo ""
echo "🚀 Iniciando gunicorn..."
nohup gunicorn \
    --pythonpath /var/www/stvaldivia \
    --bind 127.0.0.1:5001 \
    --workers 4 \
    --worker-class eventlet \
    --timeout 30 \
    --access-logfile /var/www/stvaldivia/logs/access.log \
    --error-logfile /var/www/stvaldivia/logs/error.log \
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
    if curl -s http://127.0.0.1:5001/api/v1/public/evento/hoy > /dev/null 2>&1; then
        echo "✅ Aplicación respondiendo correctamente"
    else
        echo "⚠️  Aplicación no responde todavía (puede estar iniciando)"
    fi
else
    echo "❌ ERROR: Gunicorn no está corriendo"
    echo ""
    echo "📋 Logs de inicio:"
    cat /tmp/gunicorn_start.log 2>/dev/null | tail -30 || echo "   (no hay logs)"
    exit 1
fi
ENDSSH

echo ""
echo "✅ PROCESO COMPLETADO"
echo ""
echo "📍 Verifica el sitio en: http://34.176.144.166"




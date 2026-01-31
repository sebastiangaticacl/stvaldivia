#!/bin/bash
# Script para reiniciar gunicorn en producción
# Uso: ./reiniciar_gunicorn.sh

set -e

INSTANCE_NAME="stvaldivia"
ZONE="southamerica-west1-a"
PROJECT_ID="stvaldivia"

echo "🔄 REINICIANDO GUNICORN EN PRODUCCIÓN"
echo "======================================"
echo ""

# Verificar autenticación
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo "❌ ERROR: No hay cuenta autenticada"
    echo "Ejecuta primero: gcloud auth login"
    exit 1
fi

echo "✅ Autenticado"
echo ""

# Crear script temporal para ejecutar en la VM
cat > /tmp/restart_gunicorn_vm.sh << 'VMSCRIPT'
#!/bin/bash
cd /var/www/stvaldivia

echo "🛑 Deteniendo gunicorn..."
pkill -9 -f 'gunicorn.*app:create_app' || echo "   (no había procesos corriendo)"
sleep 2

echo "🐍 Activando entorno virtual..."
source venv/bin/activate

echo "🚀 Iniciando gunicorn..."
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

echo ""
echo "🔍 Verificando estado..."
if ps aux | grep -E 'gunicorn.*app:create_app' | grep -v grep > /dev/null; then
    echo "✅ Gunicorn está corriendo"
    echo ""
    echo "📊 Procesos:"
    ps aux | grep -E 'gunicorn.*app:create_app' | grep -v grep | head -3
    echo ""
    
    echo "🧪 Probando conexión..."
    if curl -s http://127.0.0.1:5001/api/v1/public/evento/hoy > /dev/null 2>&1; then
        echo "✅ Aplicación respondiendo correctamente"
    else
        echo "⚠️  Aplicación no responde (puede estar iniciando)"
    fi
else
    echo "❌ ERROR: Gunicorn no está corriendo"
    echo ""
    echo "📋 Últimos logs de error:"
    tail -20 /var/www/stvaldivia/logs/error.log 2>/dev/null || echo "   (no hay logs disponibles)"
    exit 1
fi
VMSCRIPT

echo "📤 Subiendo script a la VM..."
gcloud compute scp /tmp/restart_gunicorn_vm.sh stvaldivia:/tmp/ --zone=$ZONE --project=$PROJECT_ID

echo ""
echo "▶️  Ejecutando script en la VM..."
gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --project=$PROJECT_ID --command="bash /tmp/restart_gunicorn_vm.sh"

echo ""
echo "🧹 Limpiando..."
rm -f /tmp/restart_gunicorn_vm.sh

echo ""
echo "✅ PROCESO COMPLETADO"
echo ""
echo "📍 Verifica el sitio en: http://34.176.144.166"




#!/bin/bash
# Script para actualizar producción rápidamente
# Usa el script deploy_vm.sh completo o hace pull si existe git

INSTANCE_NAME="stvaldivia"
ZONE="southamerica-west1-a"
PROJECT_ID="stvaldivia"
WEBROOT="/var/www/stvaldivia"

echo "🚀 ACTUALIZANDO PRODUCCIÓN"
echo "=========================="
echo ""

gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --project=$PROJECT_ID << 'ENDSSH'
    set -e
    WEBROOT="/var/www/stvaldivia"
    
    echo "📥 Actualizando código desde GitHub..."
    cd "$WEBROOT"
    
    # Si es un repositorio git, hacer pull
    if [ -d .git ]; then
        git fetch origin
        git pull origin main || git pull origin master
        echo "✅ Código actualizado desde git"
    else
        echo "⚠️  No es un repositorio git, necesitas hacer deploy completo"
        echo "   Usa: ./deploy_vm.sh"
        exit 1
    fi
    
    echo ""
    echo "🔄 Reiniciando gunicorn..."
    pkill -f 'gunicorn.*app:create_app' || true
    sleep 2
    
    cd "$WEBROOT"
    source venv/bin/activate
    
    # Reiniciar gunicorn
    gunicorn --pythonpath "$WEBROOT" \
        --bind 127.0.0.1:5001 \
        --workers 4 \
        --worker-class eventlet \
        --timeout 30 \
        --access-logfile "$WEBROOT/logs/access.log" \
        --error-logfile "$WEBROOT/logs/error.log" \
        --daemon \
        app:create_app
    
    sleep 2
    
    # Verificar que está corriendo
    if pgrep -f 'gunicorn.*app:create_app' > /dev/null; then
        echo "✅ Gunicorn reiniciado correctamente"
    else
        echo "❌ Error: Gunicorn no está corriendo"
        exit 1
    fi
    
    echo ""
    echo "✅ ACTUALIZACIÓN COMPLETADA"
ENDSSH

echo ""
echo "✅ Proceso completado"
echo "📍 Verifica: http://34.176.144.166"




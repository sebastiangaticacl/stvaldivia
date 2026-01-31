#!/bin/bash
# Script rápido para deployment a la VM

set -e

VM_IP="34.176.144.166"
SSH_USER="stvaldiviazal"
SSH_KEY="$HOME/.ssh/id_ed25519_gcp"

echo "🚀 DEPLOYMENT A VM"
echo "=================="
echo "📍 VM: $VM_IP"
echo "👤 Usuario: $SSH_USER"
echo ""

ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$SSH_USER@$VM_IP" << 'ENDSSH'
set -e
echo '🔄 Actualizando código...'
PROJECT_DIR="/var/www/stvaldivia"
cd "$PROJECT_DIR" || { echo "❌ No se pudo cambiar al directorio: $PROJECT_DIR"; exit 1; }
echo "✅ Directorio: $(pwd)"
if [ -d .git ]; then 
    echo '📥 Haciendo pull...'
    sudo -u deploy git pull origin main 2>/dev/null || sudo -u deploy git pull origin master 2>/dev/null || echo '⚠️  No se pudo hacer git pull (continuando...)'
fi
if [ -d venv ]; then source venv/bin/activate; fi
if [ -f requirements.txt ]; then pip install -q -r requirements.txt || true; fi
echo '🔄 Reiniciando servicio...'
if sudo systemctl is-active --quiet gunicorn.service; then
    sudo systemctl restart gunicorn.service && echo '✅ Gunicorn reiniciado (restart completo)' || echo '⚠️  No se pudo reiniciar gunicorn'
elif pgrep -f "gunicorn.*app:create_app" > /dev/null; then
    GUNICORN_PID=$(pgrep -f "gunicorn.*app:create_app" | head -1)
    if [ -n "$GUNICORN_PID" ]; then
        sudo kill -HUP "$GUNICORN_PID" 2>/dev/null && echo '✅ Gunicorn reiniciado (HUP signal)' || echo '⚠️  No se pudo reiniciar gunicorn'
    fi
else
    echo '⚠️  Servicio no encontrado'
    ps aux | grep -E 'gunicorn|python.*app' | grep -v grep | head -3
fi
echo '✅ Deploy completado'
ENDSSH

echo ""
echo "✅ DEPLOYMENT COMPLETADO"






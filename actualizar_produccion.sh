#!/bin/bash
# Actualizar producción: SSH a la VM, git pull y reiniciar gunicorn

VM_IP="${1:-34.176.144.166}"
VM_USER="${2:-stvaldiviazal}"
WEBROOT="/var/www/stvaldivia"

# Clave SSH
SSH_KEY="$HOME/.ssh/id_ed25519"
[ -f "$HOME/.ssh/id_rsa" ] && SSH_KEY="$HOME/.ssh/id_rsa"
[ ! -f "$SSH_KEY" ] && echo "❌ No se encuentra clave SSH" && exit 1

echo "🚀 ACTUALIZANDO PRODUCCIÓN"
echo "=========================="
echo "📍 $VM_USER@$VM_IP"
echo ""

ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$VM_USER@$VM_IP" << ENDSSH
    set -e
    WEBROOT="$WEBROOT"
    echo "📥 Actualizando código..."
    cd "\$WEBROOT"
    if [ -d .git ]; then
        git fetch origin
        git pull origin main || git pull origin master
        echo "✅ Código actualizado"
    else
        echo "⚠️  No es repo git. Usa ./deploy_completo.sh para subir código."
        exit 1
    fi
    echo "🔄 Reiniciando gunicorn..."
    sudo pkill -f 'gunicorn.*app:create_app' || true
    sleep 2
    cd "\$WEBROOT"
    source venv/bin/activate
    nohup gunicorn --pythonpath "\$WEBROOT" --bind 127.0.0.1:5001 --workers 4 --worker-class eventlet --timeout 30 --daemon app:create_app > /dev/null 2>&1 &
    sleep 2
    if pgrep -f 'gunicorn.*app:create_app' > /dev/null; then
        echo "✅ Gunicorn reiniciado"
    else
        echo "❌ Gunicorn no arrancó"
        exit 1
    fi
    echo "✅ ACTUALIZACIÓN COMPLETADA"
ENDSSH

echo ""
echo "📍 Verifica: http://$VM_IP"
echo ""

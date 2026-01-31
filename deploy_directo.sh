#!/bin/bash
# Deployment directo usando SSH (sin gcloud auth)
# Necesita la IP de la VM

set -e

# Si tienes la IP directamente, úsala aquí
VM_IP="${1:-}"
VM_USER="${2:-$USER}"

if [ -z "$VM_IP" ]; then
    echo "❌ ERROR: Necesitas proporcionar la IP de la VM"
    echo "Uso: ./deploy_directo.sh [IP_VM] [USUARIO]"
    echo ""
    echo "O ejecuta primero: gcloud auth login"
    echo "Luego: ./ejecutar_todo.sh"
    exit 1
fi

echo "🚀 DEPLOYMENT DIRECTO A VM"
echo "=========================="
echo "📍 IP: $VM_IP"
echo "👤 Usuario: $VM_USER"
echo ""

ssh $VM_USER@$VM_IP << 'ENDSSH'
    set -e
    echo '🔄 Actualizando código...'
    
    # Navegar al directorio del proyecto
    cd ~/tickets_cursor_clean || cd ~/tickets || cd ~/app || { echo '❌ Directorio del proyecto no encontrado'; exit 1; }
    
    # Hacer pull del código (si usas git)
    if [ -d .git ]; then
        echo '📥 Haciendo pull del repositorio...'
        git pull origin main || git pull origin master || echo '⚠️  No se pudo hacer pull (continuando...)'
    fi
    
    # Activar entorno virtual si existe
    if [ -d venv ]; then
        echo '🐍 Activando entorno virtual...'
        source venv/bin/activate
    fi
    
    # Instalar/actualizar dependencias
    if [ -f requirements.txt ]; then
        echo '📦 Instalando dependencias...'
        pip install -q -r requirements.txt || echo '⚠️  Algunas dependencias no se pudieron instalar'
    fi
    
    # Reiniciar servicio
    echo '🔄 Reiniciando servicio...'
    
    # Opción 1: systemd
    if systemctl is-active --quiet bimba.service 2>/dev/null; then
        sudo systemctl restart bimba.service
        echo '✅ Servicio systemd reiniciado'
    # Opción 2: supervisor
    elif command -v supervisorctl &>/dev/null && supervisorctl status bimba &>/dev/null; then
        sudo supervisorctl restart bimba
        echo '✅ Servicio supervisor reiniciado'
    # Opción 3: PM2
    elif command -v pm2 &>/dev/null; then
        pm2 restart bimba || pm2 restart all
        echo '✅ Servicio PM2 reiniciado'
    # Opción 4: screen
    elif screen -list | grep -q bimba; then
        screen -S bimba -X stuff '^C'
        sleep 2
        screen -S bimba -X stuff 'python3 run_local.py\n'
        echo '✅ Proceso en screen reiniciado'
    else
        echo '⚠️  No se encontró servicio configurado.'
        echo '   Busca el proceso con: ps aux | grep python'
    fi
    
    echo ''
    echo '✅ Deploy completado'
ENDSSH

echo ""
echo "✅ DEPLOYMENT COMPLETADO"
echo ""

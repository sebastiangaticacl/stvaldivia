#!/bin/bash
# Deployment usando SSH directo con claves de Google Cloud
# Este script intenta obtener la IP y conectarse

set -e

INSTANCE_NAME="stvaldivia"
ZONE="southamerica-west1-a"
PROJECT_ID="stvaldivia"

echo "🚀 DEPLOYMENT CON SSH DIRECTO"
echo "=============================="
echo ""

# Intentar obtener IP de la VM
echo "🔍 Obteniendo IP de la VM..."
VM_IP=""

# Método 1: Usando gcloud (si está autenticado)
if gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q . 2>/dev/null; then
    VM_IP=$(gcloud compute instances describe $INSTANCE_NAME --zone=$ZONE --project=$PROJECT_ID --format="get(networkInterfaces[0].accessConfigs[0].natIP)" 2>/dev/null || echo "")
fi

# Método 2: Si no se pudo obtener, pedir al usuario
if [ -z "$VM_IP" ]; then
    echo "⚠️  No se pudo obtener la IP automáticamente"
    echo "Por favor, proporciona la IP de la VM:"
    read -p "IP de la VM: " VM_IP
    
    if [ -z "$VM_IP" ]; then
        echo "❌ ERROR: Se necesita la IP de la VM"
        echo ""
        echo "Puedes obtenerla con:"
        echo "  gcloud compute instances list --format='table(name,EXTERNAL_IP)'"
        exit 1
    fi
fi

echo "✅ IP obtenida: $VM_IP"
echo ""

# Determinar usuario SSH
SSH_USER="${1:-$USER}"
if [ "$SSH_USER" = "$USER" ]; then
    # Intentar detectar usuario común en GCP
    SSH_USER="stvaldiviazal"  # Basado en el email proporcionado
fi

echo "👤 Usuario SSH: $SSH_USER"
echo ""

# Conectar y desplegar
echo "📦 Conectando y desplegando..."
echo ""

ssh -o StrictHostKeyChecking=no $SSH_USER@$VM_IP << 'ENDSSH'
    set -e
    echo '🔄 Actualizando código...'
    
    # Navegar al directorio del proyecto
    cd ~/tickets_cursor_clean || cd ~/tickets || cd ~/app || { 
        echo '❌ Directorio del proyecto no encontrado'
        echo 'Directorios disponibles:'
        ls -la ~ | grep -E '^d' | awk '{print $9}'
        exit 1
    }
    
    echo "✅ Directorio encontrado: $(pwd)"
    
    # Hacer pull del código (si usas git)
    if [ -d .git ]; then
        echo '📥 Haciendo pull del repositorio...'
        git pull origin main || git pull origin master || echo '⚠️  No se pudo hacer pull (continuando...)'
    else
        echo '⚠️  No es un repositorio git, saltando pull'
    fi
    
    # Activar entorno virtual si existe
    if [ -d venv ]; then
        echo '🐍 Activando entorno virtual...'
        source venv/bin/activate
    elif [ -d .venv ]; then
        echo '🐍 Activando entorno virtual (.venv)...'
        source .venv/bin/activate
    else
        echo '⚠️  No se encontró entorno virtual'
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
    elif command -v supervisorctl &>/dev/null && supervisorctl status bimba &>/dev/null 2>/dev/null; then
        sudo supervisorctl restart bimba
        echo '✅ Servicio supervisor reiniciado'
    # Opción 3: PM2
    elif command -v pm2 &>/dev/null && pm2 list | grep -q bimba; then
        pm2 restart bimba || pm2 restart all
        echo '✅ Servicio PM2 reiniciado'
    # Opción 4: screen
    elif screen -list 2>/dev/null | grep -q bimba; then
        screen -S bimba -X stuff '^C'
        sleep 2
        screen -S bimba -X stuff 'python3 run_local.py\n'
        echo '✅ Proceso en screen reiniciado'
    # Opción 5: Buscar proceso Python y reiniciarlo
    else
        echo '⚠️  No se encontró servicio configurado.'
        echo '   Buscando procesos Python...'
        ps aux | grep -E 'python.*run_local|python.*app' | grep -v grep || echo '   No se encontraron procesos'
        echo ''
        echo '   Para reiniciar manualmente:'
        echo '   - Busca el proceso: ps aux | grep python'
        echo '   - Mátalo: kill <PID>'
        echo '   - Reinicia: python3 run_local.py'
    fi
    
    echo ''
    echo '✅ Deploy completado'
    echo "📍 Directorio: $(pwd)"
ENDSSH

echo ""
echo "✅ DEPLOYMENT COMPLETADO"
echo ""
echo "📍 Verifica el servicio en: http://$VM_IP:5001"
echo ""






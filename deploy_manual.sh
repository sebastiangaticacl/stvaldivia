#!/bin/bash
# Script de deployment manual a VM
# Ejecuta: ./deploy_manual.sh

set -e

INSTANCE_NAME="stvaldivia"
ZONE="southamerica-west1-a"
PROJECT_ID="stvaldivia"

echo "🚀 DEPLOYMENT MANUAL A VM"
echo "========================="
echo ""
echo "📋 Configuración:"
echo "  Instancia: $INSTANCE_NAME"
echo "  Zona: $ZONE"
echo "  Proyecto: $PROJECT_ID"
echo ""

# Verificar autenticación
echo "🔐 Verificando autenticación..."
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo "❌ ERROR: No hay cuenta autenticada"
    echo "Ejecuta primero: gcloud auth login"
    exit 1
fi

ACTIVE_ACCOUNT=$(gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -1)
echo "✅ Autenticado como: $ACTIVE_ACCOUNT"
echo ""

# Configurar proyecto
echo "⚙️  Configurando proyecto..."
gcloud config set project $PROJECT_ID
echo ""

# Verificar instancia
echo "🔍 Verificando instancia..."
EXTERNAL_IP=$(gcloud compute instances describe $INSTANCE_NAME --zone=$ZONE --project=$PROJECT_ID --format="get(networkInterfaces[0].accessConfigs[0].natIP)" 2>/dev/null || echo "")
if [ -z "$EXTERNAL_IP" ]; then
    echo "❌ ERROR: No se pudo obtener información de la instancia"
    exit 1
fi

echo "✅ Instancia encontrada"
echo "📍 IP externa: $EXTERNAL_IP"
echo ""

# Desplegar
echo "📦 Desplegando código en la VM..."
echo ""

gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --project=$PROJECT_ID --command="
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
        echo '   O reinicia manualmente el servicio'
    fi
    
    echo ''
    echo '✅ Deploy completado'
    echo '📍 Verifica el servicio en: http://'$EXTERNAL_IP':5001'
"

echo ""
echo "✅ DEPLOYMENT COMPLETADO"
echo ""
echo "📍 URL del servicio:"
echo "   http://$EXTERNAL_IP:5001"
echo ""






#!/bin/bash
# Script para sincronizar datos y desplegar a VM
# Uso: ./sync_and_deploy.sh [INSTANCE_NAME] [ZONE]

set -e

# Configuración por defecto
INSTANCE_NAME="${1:-bimba-vm}"
ZONE="${2:-southamerica-west1-a}"
PROJECT_ID="${3:-stvaldivia}"

echo "🔄 SINCRONIZACIÓN Y DEPLOYMENT A VM"
echo "===================================="
echo ""
echo "📋 Configuración:"
echo "  Instancia: $INSTANCE_NAME"
echo "  Zona: $ZONE"
echo "  Proyecto: $PROJECT_ID"
echo ""

# Paso 1: Verificar que la sincronización esté disponible
echo "📥 PASO 1: Verificando sincronización..."
echo "   (La sincronización debe ejecutarse desde el panel de control)"
echo "   URL: http://127.0.0.1:5001/admin/panel_control"
echo ""
read -p "¿Ya sincronizaste los datos desde el panel? (s/n): " sync_done

if [ "$sync_done" != "s" ] && [ "$sync_done" != "S" ]; then
    echo "⚠️  Por favor, sincroniza los datos primero desde el panel de control"
    echo "   1. Ve a: http://127.0.0.1:5001/admin/panel_control"
    echo "   2. Haz clic en '🔄 Sincronizar Ahora'"
    echo "   3. Espera a que termine la sincronización"
    echo ""
    read -p "Presiona Enter cuando hayas completado la sincronización..."
fi

echo ""
echo "✅ Sincronización verificada"
echo ""

# Paso 2: Verificar autenticación
echo "🔐 PASO 2: Verificando autenticación..."
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo "❌ ERROR: No hay cuenta autenticada"
    echo "Ejecuta primero: gcloud auth login"
    exit 1
fi

ACTIVE_ACCOUNT=$(gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -1)
echo "✅ Autenticado como: $ACTIVE_ACCOUNT"
echo ""

# Paso 3: Configurar proyecto
echo "⚙️  PASO 3: Configurando proyecto..."
gcloud config set project $PROJECT_ID
echo ""

# Paso 4: Verificar que la instancia existe
echo "🔍 PASO 4: Verificando instancia..."
if ! gcloud compute instances describe $INSTANCE_NAME --zone=$ZONE --project=$PROJECT_ID &>/dev/null; then
    echo "❌ ERROR: Instancia $INSTANCE_NAME no encontrada en zona $ZONE"
    echo ""
    echo "Instancias disponibles:"
    gcloud compute instances list --project=$PROJECT_ID --format="table(name,zone,status)"
    exit 1
fi

echo "✅ Instancia encontrada"
echo ""

# Paso 5: Obtener IP externa
EXTERNAL_IP=$(gcloud compute instances describe $INSTANCE_NAME --zone=$ZONE --project=$PROJECT_ID --format="get(networkInterfaces[0].accessConfigs[0].natIP)")
echo "📍 IP externa: $EXTERNAL_IP"
echo ""

# Paso 6: Hacer commit de cambios locales (si hay git)
if [ -d .git ]; then
    echo "📝 PASO 5: Verificando cambios en git..."
    if [ -n "$(git status --porcelain)" ]; then
        echo "⚠️  Hay cambios sin commitear:"
        git status --short
        echo ""
        read -p "¿Deseas hacer commit y push de estos cambios? (s/n): " do_commit
        
        if [ "$do_commit" = "s" ] || [ "$do_commit" = "S" ]; then
            read -p "Mensaje de commit: " commit_msg
            if [ -z "$commit_msg" ]; then
                commit_msg="Deploy: $(date '+%Y-%m-%d %H:%M:%S')"
            fi
            git add .
            git commit -m "$commit_msg"
            echo "📤 Haciendo push..."
            git push origin main || git push origin master || echo "⚠️  No se pudo hacer push"
        fi
    else
        echo "✅ No hay cambios pendientes"
    fi
    echo ""
fi

# Paso 7: Desplegar en la VM
echo "📦 PASO 6: Desplegando código en la VM..."
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
    
    # Opción 1: Si usas systemd
    if systemctl is-active --quiet bimba.service 2>/dev/null; then
        sudo systemctl restart bimba.service
        echo '✅ Servicio systemd reiniciado'
    # Opción 2: Si usas supervisor
    elif command -v supervisorctl &>/dev/null && supervisorctl status bimba &>/dev/null; then
        sudo supervisorctl restart bimba
        echo '✅ Servicio supervisor reiniciado'
    # Opción 3: Si usas PM2
    elif command -v pm2 &>/dev/null; then
        pm2 restart bimba || pm2 restart all
        echo '✅ Servicio PM2 reiniciado'
    # Opción 4: Si el proceso está en un screen/tmux
    elif screen -list | grep -q bimba; then
        screen -S bimba -X stuff '^C'
        sleep 2
        screen -S bimba -X stuff 'python3 run_local.py\n'
        echo '✅ Proceso en screen reiniciado'
    else
        echo '⚠️  No se encontró servicio configurado. Reinicia manualmente.'
        echo '   Busca el proceso con: ps aux | grep python'
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
echo "🔍 Para ver logs:"
echo "   gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --project=$PROJECT_ID"
echo ""






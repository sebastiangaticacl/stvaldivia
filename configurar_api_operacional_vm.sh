#!/bin/bash
# Script para configurar la API Operacional en la VM de producción
# La API operacional proporciona contexto adicional (ventas, ambiente) para el chatbot

echo "📈 CONFIGURACIÓN DE API OPERACIONAL EN VM"
echo "=========================================="
echo ""

# Configuración de conexión a la VM
VM_USER="stvaldiviazal"
VM_IP="34.176.144.166"
SSH_KEY="$HOME/.ssh/id_ed25519_gcp"

# Verificar que existe la clave SSH
if [ ! -f "$SSH_KEY" ]; then
    echo "⚠️  No se encontró la clave SSH en $SSH_KEY"
    echo "   Usando conexión SSH estándar..."
    SSH_CMD="ssh"
else
    SSH_CMD="ssh -i $SSH_KEY"
fi

echo "🔍 Conectando a la VM: $VM_USER@$VM_IP"
echo ""

# Generar API Key si no se proporciona
if [ -n "$1" ]; then
    API_KEY="$1"
    echo "✅ Usando API Key proporcionada"
else
    # Generar una API key aleatoria segura
    API_KEY=$(openssl rand -hex 32)
    echo "🔑 API Key generada automáticamente: $API_KEY"
    echo ""
    read -p "¿Usar esta API Key? (s/n): " confirmar
    if [ "$confirmar" != "s" ] && [ "$confirmar" != "S" ]; then
        echo "❌ Configuración cancelada"
        exit 1
    fi
fi

# Determinar URL base
if [ -n "$2" ]; then
    BASE_URL="$2"
else
    # En producción, usar la misma URL del servidor
    BASE_URL="http://127.0.0.1:5001"
    echo "🌐 Usando URL base por defecto: $BASE_URL"
    echo ""
    read -p "¿Usar esta URL? (s/n, o ingresa otra URL): " respuesta
    if [ "$respuesta" != "s" ] && [ "$respuesta" != "S" ]; then
        if [ -n "$respuesta" ]; then
            BASE_URL="$respuesta"
        else
            echo "❌ Configuración cancelada"
            exit 1
        fi
    fi
fi

echo ""
echo "📋 Resumen de configuración:"
echo "   BIMBA_INTERNAL_API_KEY: ${API_KEY:0:10}... (${#API_KEY} caracteres)"
echo "   BIMBA_INTERNAL_API_BASE_URL: $BASE_URL"
echo ""
read -p "¿Continuar con esta configuración? (s/n): " confirmar

if [ "$confirmar" != "s" ] && [ "$confirmar" != "S" ]; then
    echo "❌ Configuración cancelada"
    exit 1
fi

echo ""
echo "🔧 Configurando API Operacional en la VM..."

# Conectar a la VM y configurar
$SSH_CMD -o StrictHostKeyChecking=no "$VM_USER@$VM_IP" "sudo bash << 'VM_CONFIG'
set -e

SERVICE_FILE=\"/etc/systemd/system/stvaldivia.service\"
ENV_FILE=\"/var/www/stvaldivia/.env\"

echo '📝 Verificando archivo de servicio systemd...'

# Método 1: Agregar al servicio systemd (recomendado)
if [ -f \"\$SERVICE_FILE\" ]; then
    echo '✅ Archivo de servicio encontrado'
    
    # Hacer backup
    cp \"\$SERVICE_FILE\" \"\$SERVICE_FILE.backup.\$(date +%Y%m%d_%H%M%S)\"
    
    # Verificar si ya existen las variables
    if grep -q 'Environment=\"BIMBA_INTERNAL_API_KEY=' \"\$SERVICE_FILE\"; then
        echo '⚠️  Variables de API Operacional ya existen, actualizando...'
        # Eliminar líneas existentes
        sed -i '/Environment=\"BIMBA_INTERNAL_/d' \"\$SERVICE_FILE\"
    fi
    
    # Agregar variables antes de ExecStart
    sed -i '/^ExecStart=/i Environment=\"BIMBA_INTERNAL_API_KEY='$API_KEY'\"' \"\$SERVICE_FILE\"
    sed -i '/^ExecStart=/i Environment=\"BIMBA_INTERNAL_API_BASE_URL='$BASE_URL'\"' \"\$SERVICE_FILE\"
    
    echo '✅ Variables agregadas al servicio systemd'
    
    # Recargar y reiniciar servicio
    systemctl daemon-reload
    systemctl restart stvaldivia.service
    sleep 2
    
    if systemctl is-active --quiet stvaldivia.service; then
        echo '✅ Servicio reiniciado correctamente'
    else
        echo '⚠️  El servicio no está activo, revisa los logs:'
        echo '   sudo journalctl -u stvaldivia.service -n 50'
    fi
else
    echo '⚠️  Archivo de servicio no encontrado en \$SERVICE_FILE'
    echo '   Intentando método alternativo con archivo .env...'
fi

# Método 2: Agregar a archivo .env (alternativo)
if [ -f \"\$ENV_FILE\" ]; then
    echo '📝 Agregando variables al archivo .env...'
    
    # Backup
    cp \"\$ENV_FILE\" \"\$ENV_FILE.backup.\$(date +%Y%m%d_%H%M%S)\"
    
    # Eliminar variables existentes
    sed -i '/^BIMBA_INTERNAL_/d' \"\$ENV_FILE\"
    
    # Agregar nuevas variables
    echo '' >> \"\$ENV_FILE\"
    echo '# API Operacional para contexto del chatbot' >> \"\$ENV_FILE\"
    echo \"BIMBA_INTERNAL_API_KEY=$API_KEY\" >> \"\$ENV_FILE\"
    echo \"BIMBA_INTERNAL_API_BASE_URL=$BASE_URL\" >> \"\$ENV_FILE\"
    
    echo '✅ Variables agregadas al archivo .env'
    echo '⚠️  IMPORTANTE: Reinicia el servicio manualmente:'
    echo '   sudo systemctl restart stvaldivia.service'
fi

echo ''
echo '✅ Configuración completada'
echo ''
echo '📋 Para verificar:'
echo '   1. Revisa los logs: sudo journalctl -u stvaldivia.service -f'
echo '   2. Ve al panel de configuración del bot: /admin/bot/config'
echo '   3. Deberías ver "✅ Habilitada" en API Operacional'
VM_CONFIG
" 2>&1

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ CONFIGURACIÓN COMPLETADA"
    echo ""
    echo "📋 Próximos pasos:"
    echo "   1. Verifica en el panel: /admin/bot/config"
    echo "   2. Deberías ver '✅ Habilitada' en API Operacional"
    echo "   3. El chatbot ahora tendrá contexto operativo (ventas, ambiente, etc.)"
    echo ""
    echo "🔍 Para ver logs en tiempo real:"
    echo "   ssh $VM_USER@$VM_IP 'sudo journalctl -u stvaldivia.service -f'"
    echo ""
    echo "💡 La API Operacional proporciona:"
    echo "   - Resumen de ventas del día"
    echo "   - Estado del ambiente (movido, tranquilo, etc.)"
    echo "   - Ranking de productos"
    echo "   - Información de entregas y bartenders"
    echo "   - Detección de fugas/antifraude"
else
    echo ""
    echo "❌ Error al configurar. Revisa los mensajes anteriores."
    exit 1
fi


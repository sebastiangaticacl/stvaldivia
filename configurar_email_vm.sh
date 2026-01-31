#!/bin/bash
# Script para configurar email SMTP en la VM de producción
# Uso: ./configurar_email_vm.sh [opcion] [parametros...]
#   opcion 3: ./configurar_email_vm.sh 3 hola@stvaldivia.cl contraseña
#   opcion 1: ./configurar_email_vm.sh 1 email@gmail.com app-password

echo "📧 CONFIGURACIÓN DE EMAIL EN VM DE PRODUCCIÓN"
echo "=============================================="
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

# Si se pasó la opción como parámetro
if [ -n "$1" ]; then
    opcion="$1"
    echo "✅ Usando opción $opcion (pasada como parámetro)"
else
    # Mostrar opciones de proveedores
    echo "Selecciona tu proveedor de email:"
    echo ""
    echo "1) Gmail (Recomendado - requiere App Password)"
    echo "2) Outlook/Hotmail"
    echo "3) Servidor SMTP del hosting (s3418.mex1.stableserver.net)"
    echo "4) SendGrid"
    echo "5) Mailgun"
    echo "6) Otro (configuración manual)"
    echo ""
    read -p "Opción (1-6): " opcion
fi

case $opcion in
    1)
        SMTP_SERVER="smtp.gmail.com"
        SMTP_PORT="587"
        echo ""
        if [ -n "$2" ] && [ -n "$3" ]; then
            SMTP_USER="$2"
            SMTP_PASSWORD="$3"
            SMTP_FROM="$2"
            echo "✅ Usando credenciales de Gmail pasadas como parámetros"
        else
            echo "📝 Para Gmail necesitas:"
            echo "   1. Habilitar verificación en 2 pasos en tu cuenta de Google"
            echo "   2. Generar una App Password"
            echo "   Ve a: https://myaccount.google.com/apppasswords"
            echo ""
            read -p "Email de Gmail: " SMTP_USER
            read -sp "App Password (16 caracteres, sin espacios): " SMTP_PASSWORD
            echo ""
            SMTP_FROM="$SMTP_USER"
        fi
        ;;
    2)
        SMTP_SERVER="smtp-mail.outlook.com"
        SMTP_PORT="587"
        read -p "Email de Outlook: " SMTP_USER
        read -sp "Contraseña: " SMTP_PASSWORD
        echo ""
        SMTP_FROM="$SMTP_USER"
        ;;
    3)
        SMTP_SERVER="s3418.mex1.stableserver.net"
        SMTP_PORT="465"
        echo ""
        echo "📝 Usando servidor SMTP del hosting stvaldivia.cl"
        if [ -n "$2" ] && [ -n "$3" ]; then
            SMTP_USER="$2"
            SMTP_PASSWORD="$3"
            SMTP_FROM="$2"
            echo "✅ Usando credenciales pasadas como parámetros"
        else
            read -p "Email (ej: hola@stvaldivia.cl): " SMTP_USER
            read -sp "Contraseña del email: " SMTP_PASSWORD
            echo ""
            SMTP_FROM="$SMTP_USER"
        fi
        ;;
    4)
        SMTP_SERVER="smtp.sendgrid.net"
        SMTP_PORT="587"
        echo ""
        echo "📝 Configuración de SendGrid"
        read -p "API Key de SendGrid: " SMTP_PASSWORD
        SMTP_USER="apikey"
        read -p "Email remitente (ej: noreply@stvaldivia.cl): " SMTP_FROM
        ;;
    5)
        SMTP_SERVER="smtp.mailgun.org"
        SMTP_PORT="587"
        echo ""
        echo "📝 Configuración de Mailgun"
        read -p "Usuario SMTP (ej: postmaster@tudominio.mailgun.org): " SMTP_USER
        read -sp "Contraseña SMTP: " SMTP_PASSWORD
        echo ""
        read -p "Email remitente (ej: noreply@stvaldivia.cl): " SMTP_FROM
        ;;
    6)
        read -p "Servidor SMTP: " SMTP_SERVER
        read -p "Puerto SMTP (587 para TLS, 465 para SSL): " SMTP_PORT
        read -p "Usuario SMTP: " SMTP_USER
        read -sp "Contraseña SMTP: " SMTP_PASSWORD
        echo ""
        read -p "Email remitente: " SMTP_FROM
        ;;
    *)
        echo "❌ Opción inválida"
        exit 1
        ;;
esac

# Verificar que no estén vacíos
if [ -z "$SMTP_SERVER" ] || [ -z "$SMTP_USER" ] || [ -z "$SMTP_PASSWORD" ]; then
    echo "❌ Error: Faltan datos requeridos"
    exit 1
fi

echo ""
echo "📋 Resumen de configuración:"
echo "   SMTP_SERVER: $SMTP_SERVER"
echo "   SMTP_PORT: $SMTP_PORT"
echo "   SMTP_USER: $SMTP_USER"
echo "   SMTP_FROM: $SMTP_FROM"
echo ""
read -p "¿Continuar con esta configuración? (s/n): " confirmar

if [ "$confirmar" != "s" ] && [ "$confirmar" != "S" ]; then
    echo "❌ Configuración cancelada"
    exit 1
fi

echo ""
echo "🔧 Configurando email en la VM..."

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
    
    # Verificar si ya existen las variables SMTP
    if grep -q 'Environment=\"SMTP_SERVER=' \"\$SERVICE_FILE\"; then
        echo '⚠️  Variables SMTP ya existen, actualizando...'
        # Eliminar líneas SMTP existentes
        sed -i '/Environment=\"SMTP_/d' \"\$SERVICE_FILE\"
    fi
    
    # Agregar variables SMTP antes de ExecStart
    sed -i '/^ExecStart=/i Environment=\"SMTP_SERVER='$SMTP_SERVER'\"' \"\$SERVICE_FILE\"
    sed -i '/^ExecStart=/i Environment=\"SMTP_PORT='$SMTP_PORT'\"' \"\$SERVICE_FILE\"
    sed -i '/^ExecStart=/i Environment=\"SMTP_USER='$SMTP_USER'\"' \"\$SERVICE_FILE\"
    sed -i '/^ExecStart=/i Environment=\"SMTP_PASSWORD='$SMTP_PASSWORD'\"' \"\$SERVICE_FILE\"
    sed -i '/^ExecStart=/i Environment=\"SMTP_FROM='$SMTP_FROM'\"' \"\$SERVICE_FILE\"
    
    echo '✅ Variables SMTP agregadas al servicio systemd'
    
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
    
    # Eliminar variables SMTP existentes
    sed -i '/^SMTP_/d' \"\$ENV_FILE\"
    
    # Agregar nuevas variables
    echo '' >> \"\$ENV_FILE\"
    echo '# Configuración SMTP para envío de emails' >> \"\$ENV_FILE\"
    echo \"SMTP_SERVER=$SMTP_SERVER\" >> \"\$ENV_FILE\"
    echo \"SMTP_PORT=$SMTP_PORT\" >> \"\$ENV_FILE\"
    echo \"SMTP_USER=$SMTP_USER\" >> \"\$ENV_FILE\"
    echo \"SMTP_PASSWORD=$SMTP_PASSWORD\" >> \"\$ENV_FILE\"
    echo \"SMTP_FROM=$SMTP_FROM\" >> \"\$ENV_FILE\"
    
    echo '✅ Variables SMTP agregadas al archivo .env'
    echo '⚠️  IMPORTANTE: Reinicia el servicio manualmente:'
    echo '   sudo systemctl restart stvaldivia.service'
fi

echo ''
echo '✅ Configuración completada'
echo ''
echo '📋 Para verificar:'
echo '   1. Revisa los logs: sudo journalctl -u stvaldivia.service -f'
echo '   2. Realiza una compra de prueba'
echo '   3. Verifica que el email se envía correctamente'
VM_CONFIG
" 2>&1

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ CONFIGURACIÓN COMPLETADA"
    echo ""
    echo "📋 Próximos pasos:"
    echo "   1. Verifica los logs del servicio en la VM"
    echo "   2. Realiza una compra de prueba"
    echo "   3. Revisa que el email se envía correctamente"
    echo ""
    echo "🔍 Para ver logs en tiempo real:"
    echo "   ssh $VM_USER@$VM_IP 'sudo journalctl -u stvaldivia.service -f'"
else
    echo ""
    echo "❌ Error al configurar. Revisa los mensajes anteriores."
    exit 1
fi


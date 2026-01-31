#!/bin/bash
# Script para configurar variables de email SMTP

echo "📧 Configuración de Email SMTP para BIMBA"
echo "=========================================="
echo ""

# Verificar si existe .env
if [ ! -f .env ]; then
    echo "⚠️  No se encontró archivo .env"
    read -p "¿Crear archivo .env? (s/n): " crear
    if [ "$crear" = "s" ] || [ "$crear" = "S" ]; then
        touch .env
        echo "✅ Archivo .env creado"
    else
        echo "❌ No se puede continuar sin archivo .env"
        exit 1
    fi
fi

echo ""
echo "Selecciona tu proveedor de email:"
echo "1) Gmail"
echo "2) Outlook/Hotmail"
echo "3) Otro (configuración manual)"
read -p "Opción (1-3): " opcion

case $opcion in
    1)
        SMTP_SERVER="smtp.gmail.com"
        SMTP_PORT="587"
        echo ""
        echo "📝 Para Gmail necesitas:"
        echo "   1. Habilitar verificación en 2 pasos"
        echo "   2. Generar una App Password"
        echo "   Ve a: https://myaccount.google.com/apppasswords"
        echo ""
        read -p "Email de Gmail: " SMTP_USER
        read -sp "App Password (16 caracteres, sin espacios): " SMTP_PASSWORD
        echo ""
        SMTP_FROM="$SMTP_USER"
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

# Backup del .env
cp .env .env.backup.$(date +%Y%m%d_%H%M%S) 2>/dev/null || true

# Eliminar variables SMTP existentes
sed -i.bak '/^SMTP_/d' .env 2>/dev/null || sed -i '' '/^SMTP_/d' .env 2>/dev/null

# Agregar nuevas variables
echo "" >> .env
echo "# Configuración SMTP para envío de emails" >> .env
echo "SMTP_SERVER=$SMTP_SERVER" >> .env
echo "SMTP_PORT=$SMTP_PORT" >> .env
echo "SMTP_USER=$SMTP_USER" >> .env
echo "SMTP_PASSWORD=$SMTP_PASSWORD" >> .env
echo "SMTP_FROM=$SMTP_FROM" >> .env

echo ""
echo "✅ Variables SMTP agregadas al archivo .env"
echo ""
echo "📋 Configuración guardada:"
echo "   SMTP_SERVER=$SMTP_SERVER"
echo "   SMTP_PORT=$SMTP_PORT"
echo "   SMTP_USER=$SMTP_USER"
echo "   SMTP_FROM=$SMTP_FROM"
echo ""
echo "⚠️  IMPORTANTE: Reinicia el servidor Flask para que los cambios surtan efecto"
echo ""
echo "💡 Para probar, realiza una compra y verifica los logs del servidor"



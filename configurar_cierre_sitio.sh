#!/bin/bash
# Script para configurar el cierre del sitio en producción
# Uso: ./configurar_cierre_sitio.sh [cerrar|abrir]

set -e

ACTION="${1:-cerrar}"
VM_IP="34.176.144.166"
SSH_USER="stvaldiviazal"
SSH_KEY="$HOME/.ssh/id_ed25519_gcp"
PROJECT_DIR="/var/www/stvaldivia"

if [ "$ACTION" == "cerrar" ]; then
    echo "🔒 Configurando cierre del sitio en producción..."
    SITE_CLOSED_VALUE="true"
elif [ "$ACTION" == "abrir" ]; then
    echo "🔓 Configurando apertura del sitio en producción..."
    SITE_CLOSED_VALUE="false"
else
    echo "Uso: $0 [cerrar|abrir]"
    exit 1
fi

ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$SSH_USER@$VM_IP" << ENDSSH
set -e

PROJECT_DIR="$PROJECT_DIR"
SITE_CLOSED_VALUE="$SITE_CLOSED_VALUE"

echo "📝 Configurando variable SITE_CLOSED=$SITE_CLOSED_VALUE..."

# Buscar archivo de configuración del servicio systemd
SERVICE_FILE="/etc/systemd/system/stvaldivia.service"
ENV_FILE="\$PROJECT_DIR/.env"

# Si existe archivo .env, actualizarlo
if [ -f "\$ENV_FILE" ]; then
    if grep -q "^SITE_CLOSED=" "\$ENV_FILE"; then
        # Actualizar valor existente
        sudo sed -i "s/^SITE_CLOSED=.*/SITE_CLOSED=\$SITE_CLOSED_VALUE/" "\$ENV_FILE"
        echo "✅ Actualizado SITE_CLOSED en \$ENV_FILE"
    else
        # Agregar nueva variable
        echo "SITE_CLOSED=\$SITE_CLOSED_VALUE" | sudo tee -a "\$ENV_FILE" > /dev/null
        echo "✅ Agregado SITE_CLOSED a \$ENV_FILE"
    fi
    sudo chown deploy:deploy "\$ENV_FILE"
    sudo chmod 600 "\$ENV_FILE"
fi

# Si existe servicio systemd, agregar variable SITE_CLOSED directamente
if [ -f "\$SERVICE_FILE" ]; then
    # Verificar si ya tiene SITE_CLOSED
    if grep -q "^Environment=\"SITE_CLOSED=" "\$SERVICE_FILE"; then
        # Actualizar valor existente
        sudo sed -i "s/^Environment=\"SITE_CLOSED=.*/Environment=\"SITE_CLOSED=\$SITE_CLOSED_VALUE\"/" "\$SERVICE_FILE"
        echo "✅ Actualizado SITE_CLOSED en servicio systemd"
    else
        # Agregar nueva variable después de [Service] y antes de Type
        sudo sed -i '/\[Service\]/a Environment="SITE_CLOSED='"\$SITE_CLOSED_VALUE"'"' "\$SERVICE_FILE"
        echo "✅ Agregado SITE_CLOSED a servicio systemd"
    fi
    
    # Recargar systemd y reiniciar servicio
    sudo systemctl daemon-reload
    echo "✅ Systemd recargado"
fi

# También configurar en /etc/environment para persistencia
if [ "\$SITE_CLOSED_VALUE" == "true" ]; then
    if ! grep -q "^SITE_CLOSED=" /etc/environment 2>/dev/null; then
        echo "SITE_CLOSED=true" | sudo tee -a /etc/environment > /dev/null
        echo "✅ Agregado SITE_CLOSED a /etc/environment"
    else
        sudo sed -i 's/^SITE_CLOSED=.*/SITE_CLOSED=true/' /etc/environment
        echo "✅ Actualizado SITE_CLOSED en /etc/environment"
    fi
else
    if grep -q "^SITE_CLOSED=" /etc/environment 2>/dev/null; then
        sudo sed -i '/^SITE_CLOSED=/d' /etc/environment
        echo "✅ Removido SITE_CLOSED de /etc/environment"
    fi
fi

# Reiniciar servicio stvaldivia
echo "🔄 Reiniciando servicio stvaldivia..."
if sudo systemctl is-active --quiet stvaldivia; then
    sudo systemctl restart stvaldivia
    echo "✅ Servicio stvaldivia reiniciado"
    sleep 3
    if sudo systemctl is-active --quiet stvaldivia; then
        echo "✅ Servicio stvaldivia está activo"
    else
        echo "⚠️  Advertencia: Servicio stvaldivia no está activo después del reinicio"
        sudo systemctl status stvaldivia || true
    fi
else
    echo "⚠️  Servicio stvaldivia no está activo, intentando iniciar..."
    sudo systemctl start stvaldivia || true
    sleep 2
    if sudo systemctl is-active --quiet stvaldivia; then
        echo "✅ Servicio stvaldivia iniciado"
    else
        echo "❌ Error: No se pudo iniciar el servicio"
        sudo systemctl status stvaldivia || true
    fi
fi

echo ""
echo "✅ Configuración completada"
echo "   SITE_CLOSED=\$SITE_CLOSED_VALUE"
echo ""
echo "El sitio ahora está $(if [ "\$SITE_CLOSED_VALUE" == "true" ]; then echo "CERRADO"; else echo "ABIERTO"; fi) al público"

ENDSSH

echo ""
echo "✅ Proceso completado"


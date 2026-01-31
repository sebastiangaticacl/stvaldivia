#!/bin/bash
# Script para configurar SSH para la VM de Google Cloud

set -e

VM_IP="34.176.144.166"
INSTANCE_NAME="stvaldivia"
ZONE="southamerica-west1-a"
PROJECT_ID="stvaldivia"
SSH_KEY_FILE="$HOME/.ssh/id_ed25519_gcp"
SSH_USER=$(whoami)

echo "🔐 CONFIGURACIÓN SSH PARA VM DE GOOGLE CLOUD"
echo "============================================"
echo "📍 VM: $INSTANCE_NAME ($VM_IP)"
echo "👤 Usuario: $SSH_USER"
echo ""

# Verificar si existe la clave SSH
if [ ! -f "$SSH_KEY_FILE" ]; then
    echo "📝 Generando clave SSH..."
    ssh-keygen -t ed25519 -f "$SSH_KEY_FILE" -C "$SSH_USER@gcp" -N ""
    echo "✅ Clave SSH generada: $SSH_KEY_FILE"
else
    echo "✅ Clave SSH ya existe: $SSH_KEY_FILE"
fi

# Mostrar clave pública
echo ""
echo "📋 CLAVE PÚBLICA (copia esto):"
echo "--------------------------------"
cat "$SSH_KEY_FILE.pub"
echo ""
echo "--------------------------------"
echo ""

# Intentar agregar usando gcloud
echo "🔄 Intentando agregar clave usando gcloud..."
if command -v gcloud &> /dev/null; then
    # Verificar autenticación
    if gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>/dev/null | grep -q .; then
        echo "✅ gcloud autenticado, agregando clave a la VM..."
        
        # Obtener clave pública
        PUBLIC_KEY=$(cat "$SSH_KEY_FILE.pub")
        
        # Obtener claves existentes
        EXISTING_KEYS=$(gcloud compute instances describe "$INSTANCE_NAME" \
            --zone="$ZONE" \
            --project="$PROJECT_ID" \
            --format="get(metadata.items[key=ssh-keys].value)" 2>/dev/null || echo "")
        
        # Agregar nueva clave
        if [ -z "$EXISTING_KEYS" ]; then
            NEW_KEYS="$SSH_USER:$PUBLIC_KEY"
        else
            # Verificar si la clave ya existe
            if echo "$EXISTING_KEYS" | grep -q "$PUBLIC_KEY"; then
                echo "⚠️  La clave ya está agregada en la VM"
            else
                NEW_KEYS="$EXISTING_KEYS"$'\n'"$SSH_USER:$PUBLIC_KEY"
            fi
        fi
        
        # Actualizar metadata
        echo "$NEW_KEYS" | gcloud compute instances add-metadata "$INSTANCE_NAME" \
            --zone="$ZONE" \
            --project="$PROJECT_ID" \
            --metadata-from-file ssh-keys=/dev/stdin 2>&1
        
        if [ $? -eq 0 ]; then
            echo "✅ Clave SSH agregada exitosamente a la VM"
            echo ""
            echo "🧪 Probando conexión..."
            sleep 2
            ssh -i "$SSH_KEY_FILE" -o StrictHostKeyChecking=no "$SSH_USER@$VM_IP" "echo '✅ SSH funciona correctamente'" 2>&1
        else
            echo "❌ Error al agregar clave con gcloud"
            echo ""
            echo "📋 INSTRUCCIONES MANUALES:"
            echo "1. Conecta a la VM usando la consola web de Google Cloud"
            echo "2. Ejecuta estos comandos en la VM:"
            echo "   mkdir -p ~/.ssh"
            echo "   chmod 700 ~/.ssh"
            echo "   echo '$SSH_USER:$(cat $SSH_KEY_FILE.pub)' >> ~/.ssh/authorized_keys"
            echo "   chmod 600 ~/.ssh/authorized_keys"
        fi
    else
        echo "⚠️  gcloud no está autenticado"
        echo ""
        echo "📋 OPCIONES:"
        echo "1. Autenticarse: gcloud auth login"
        echo "2. Luego ejecutar este script de nuevo"
        echo ""
        echo "O agregar la clave manualmente en la VM:"
        echo "   echo '$SSH_USER:$(cat $SSH_KEY_FILE.pub)' >> ~/.ssh/authorized_keys"
    fi
else
    echo "⚠️  gcloud no está instalado"
    echo ""
    echo "📋 Agrega la clave manualmente en la VM:"
    echo "   echo '$SSH_USER:$(cat $SSH_KEY_FILE.pub)' >> ~/.ssh/authorized_keys"
fi

echo ""
echo "✅ Configuración completada"
echo ""
echo "🧪 Para probar la conexión:"
echo "   ssh -i $SSH_KEY_FILE $SSH_USER@$VM_IP"






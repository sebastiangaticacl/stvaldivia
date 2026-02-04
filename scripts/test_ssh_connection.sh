#!/bin/bash
# Script para probar conexión SSH con diferentes combinaciones

echo "🔍 PROBANDO CONEXIONES SSH"
echo "=========================="
echo ""

# IPs y usuarios a probar
declare -a TESTS=(
    "sebagatica@34.176.144.166"
    "stvaldiviazal@34.125.123.45"
    "stvaldiviazal@34.176.144.166"
    "sebagatica@34.125.123.45"
)

# Probar con id_ed25519 o id_rsa
for key in "$HOME/.ssh/id_ed25519" "$HOME/.ssh/id_rsa"; do
    if [ -f "$key" ]; then
        SSH_KEY="$key"
        break
    fi
done
if [ -z "$SSH_KEY" ] || [ ! -f "$SSH_KEY" ]; then
    echo "❌ No se encuentra clave SSH en ~/.ssh/id_ed25519 ni ~/.ssh/id_rsa"
    exit 1
fi

echo "📋 Probando con clave: $SSH_KEY"
echo ""

for TEST in "${TESTS[@]}"; do
    USER_HOST=$TEST
    echo -n "🧪 Probando $USER_HOST ... "
    
    OUTPUT=$(ssh -i "$SSH_KEY" -o ConnectTimeout=5 -o StrictHostKeyChecking=no "$USER_HOST" "echo 'OK'" 2>&1)
    
    if [ $? -eq 0 ]; then
        echo "✅ FUNCIONA"
        echo ""
        echo "🎉 ¡Conexión exitosa!"
        echo "   Usa: ssh -i $SSH_KEY $USER_HOST"
        echo ""
        exit 0
    else
        if echo "$OUTPUT" | grep -q "Permission denied"; then
            echo "❌ Permission denied (clave no autorizada)"
        elif echo "$OUTPUT" | grep -q "Connection refused"; then
            echo "⚠️  Connection refused (servidor no responde en ese puerto)"
        elif echo "$OUTPUT" | grep -q "Connection timed out"; then
            echo "⚠️  Timeout (IP puede estar incorrecta o firewall bloqueando)"
        else
            echo "❌ Error: $OUTPUT"
        fi
    fi
done

echo ""
echo "❌ Ninguna conexión funcionó"
echo ""
echo "📋 SOLUCIÓN:"
echo "1. Agrega tu clave pública al servidor (authorized_keys)"
echo "2. Verifica IP y usuario correctos para la VM"
echo ""
echo "Tu clave pública:"
cat "$SSH_KEY.pub"
echo ""


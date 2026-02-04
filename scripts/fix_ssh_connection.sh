#!/bin/bash
# Diagnosticar y ayudar a configurar SSH para la VM de producción

echo "🔍 DIAGNÓSTICO DE CONEXIÓN SSH"
echo "==============================="
echo ""

SSH_KEY=""
for key in ~/.ssh/id_ed25519 ~/.ssh/id_rsa; do
    if [ -f "$key" ]; then
        SSH_KEY="$key"
        break
    fi
done

if [ -z "$SSH_KEY" ]; then
    echo "❌ No se encuentra ninguna clave SSH"
    echo "   Genera una con: ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -C 'tu@email'"
    exit 1
fi

echo "✅ Clave SSH: $SSH_KEY"
PERMS=$(stat -f "%OLp" "$SSH_KEY" 2>/dev/null || stat -c "%a" "$SSH_KEY" 2>/dev/null)
if [ "$PERMS" != "600" ]; then
    echo "⚠️  Corrigiendo permisos (600)..."
    chmod 600 "$SSH_KEY"
fi
echo ""

echo "📋 TU CLAVE PÚBLICA:"
echo "--------------------"
cat "${SSH_KEY}.pub"
echo "--------------------"
echo ""

VM_USER="${1:-stvaldiviazal}"
VM_IP="${2:-34.176.144.166}"
echo "🧪 Probando conexión a ${VM_USER}@${VM_IP}..."
if ssh -i "$SSH_KEY" -o ConnectTimeout=5 -o StrictHostKeyChecking=no "${VM_USER}@${VM_IP}" "echo '✅ SSH funciona'" 2>/dev/null; then
    echo ""
    echo "✅ Conexión SSH correcta."
    exit 0
fi

echo ""
echo "❌ Conexión fallida (Permission denied o timeout)"
echo ""
echo "📋 Agrega la clave pública al servidor:"
echo "   En la VM: echo '$(cat "${SSH_KEY}.pub")' >> ~/.ssh/authorized_keys"
echo "   O conéctate por otro medio y pega el contenido de ${SSH_KEY}.pub en ~/.ssh/authorized_keys"
echo ""
exit 1

#!/bin/bash
# Configurar SSH para la VM de producción (sin Google Cloud)

set -e

VM_IP="34.176.144.166"
SSH_USER=$(whoami)
SSH_KEY_FILE="$HOME/.ssh/id_ed25519"
[ -f "$HOME/.ssh/id_rsa" ] && SSH_KEY_FILE="$HOME/.ssh/id_rsa"

echo "🔐 CONFIGURACIÓN SSH PARA VM"
echo "============================="
echo "📍 VM: $VM_IP"
echo "👤 Usuario: $SSH_USER"
echo ""

if [ ! -f "$SSH_KEY_FILE" ]; then
    echo "📝 Generando clave SSH..."
    ssh-keygen -t ed25519 -f "$HOME/.ssh/id_ed25519" -C "$SSH_USER@vm" -N ""
    SSH_KEY_FILE="$HOME/.ssh/id_ed25519"
    echo "✅ Clave generada: $SSH_KEY_FILE"
else
    echo "✅ Clave SSH: $SSH_KEY_FILE"
fi

echo ""
echo "📋 CLAVE PÚBLICA (agrégala en la VM en ~/.ssh/authorized_keys):"
echo "--------------------------------"
cat "$SSH_KEY_FILE.pub"
echo "--------------------------------"
echo ""
echo "En la VM ejecuta:"
echo "  mkdir -p ~/.ssh && chmod 700 ~/.ssh"
echo "  echo '$(cat "$SSH_KEY_FILE.pub")' >> ~/.ssh/authorized_keys"
echo "  chmod 600 ~/.ssh/authorized_keys"
echo ""
echo "Probar conexión:"
echo "  ssh -i $SSH_KEY_FILE $SSH_USER@$VM_IP"
echo ""

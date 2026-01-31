#!/bin/bash
# Script para diagnosticar y ayudar a configurar SSH

echo "🔍 DIAGNÓSTICO DE CONEXIÓN SSH"
echo "==============================="
echo ""

# Verificar que la clave existe
if [ ! -f ~/.ssh/id_ed25519_gcp ]; then
    echo "❌ ERROR: No se encuentra la clave SSH"
    echo "   Ubicación esperada: ~/.ssh/id_ed25519_gcp"
    echo ""
    echo "📝 Para generar una nueva clave:"
    echo "   ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519_gcp -C 'sebagatica@gcp'"
    exit 1
fi

echo "✅ Clave SSH encontrada: ~/.ssh/id_ed25519_gcp"
echo ""

# Verificar permisos
PERMS=$(stat -f "%OLp" ~/.ssh/id_ed25519_gcp 2>/dev/null || stat -c "%a" ~/.ssh/id_ed25519_gcp 2>/dev/null)
if [ "$PERMS" != "600" ]; then
    echo "⚠️  Permisos incorrectos: $PERMS (debería ser 600)"
    echo "   Corrigiendo permisos..."
    chmod 600 ~/.ssh/id_ed25519_gcp
    echo "✅ Permisos corregidos"
else
    echo "✅ Permisos correctos: $PERMS"
fi
echo ""

# Mostrar clave pública
echo "📋 TU CLAVE PÚBLICA SSH:"
echo "------------------------"
cat ~/.ssh/id_ed25519_gcp.pub
echo "------------------------"
echo ""

# Probar conexión
echo "🧪 Probando conexión..."
ssh -i ~/.ssh/id_ed25519_gcp -o ConnectTimeout=5 -o StrictHostKeyChecking=no sebagatica@34.176.144.166 "echo '✅ SSH funciona'" 2>&1

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ ¡Conexión SSH exitosa!"
    exit 0
else
    echo ""
    echo "❌ La conexión falló: Permission denied (publickey)"
    echo ""
    echo "📋 SOLUCIONES:"
    echo ""
    echo "OPCIÓN 1: Usar Consola Web de GCP (MÁS FÁCIL)"
    echo "----------------------------------------------"
    echo "1. Ve a: https://console.cloud.google.com/compute/instances?project=stvaldivia"
    echo "2. Haz clic en la instancia 'stvaldivia'"
    echo "3. Haz clic en el botón 'SSH' (se abrirá terminal en el navegador)"
    echo "4. En la terminal, ejecuta:"
    echo ""
    echo "   mkdir -p ~/.ssh"
    echo "   chmod 700 ~/.ssh"
    echo "   echo '$(cat ~/.ssh/id_ed25519_gcp.pub)' >> ~/.ssh/authorized_keys"
    echo "   chmod 600 ~/.ssh/authorized_keys"
    echo ""
    echo "OPCIÓN 2: Agregar clave desde GCP Console"
    echo "-----------------------------------------"
    echo "1. Ve a: https://console.cloud.google.com/compute/instances?project=stvaldivia"
    echo "2. Haz clic en la instancia 'stvaldivia'"
    echo "3. Haz clic en 'EDIT' (Editar)"
    echo "4. Baja hasta 'SSH Keys'"
    echo "5. Haz clic en 'ADD ITEM'"
    echo "6. Pega esta línea completa:"
    echo ""
    echo "   sebagatica:$(cat ~/.ssh/id_ed25519_gcp.pub)"
    echo ""
    echo "7. Haz clic en 'SAVE'"
    echo ""
    echo "OPCIÓN 3: Usar gcloud (si está instalado y autenticado)"
    echo "--------------------------------------------------------"
    echo "   gcloud compute instances add-metadata stvaldivia \\"
    echo "     --zone=southamerica-west1-a \\"
    echo "     --project=stvaldivia \\"
    echo "     --metadata-from-file ssh-keys=<(echo \"sebagatica:$(cat ~/.ssh/id_ed25519_gcp.pub)\")"
    echo ""
    exit 1
fi


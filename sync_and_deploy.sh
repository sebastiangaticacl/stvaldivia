#!/bin/bash
# Sincronizar datos (desde panel) y desplegar a VM por SSH
# Uso: ./sync_and_deploy.sh

set -e

echo "🔄 SINCRONIZACIÓN Y DEPLOYMENT A VM"
echo "===================================="
echo ""

echo "📥 PASO 1: Sincronización desde el panel"
echo "   URL: http://127.0.0.1:5001/admin/panel_control"
echo ""
read -p "¿Ya sincronizaste los datos desde el panel? (s/n): " sync_done

if [ "$sync_done" != "s" ] && [ "$sync_done" != "S" ]; then
    echo "⚠️  Sincroniza primero desde el panel, luego ejecuta este script."
    echo "   O continúa y solo se hará deploy del código actual."
    read -p "Presiona Enter para continuar o Ctrl+C para salir..."
fi

echo ""
echo "✅ Continuando con deploy"
echo ""

# Paso 2: Opcional commit/push
if [ -d .git ]; then
    if [ -n "$(git status --porcelain)" ]; then
        echo "📝 Hay cambios sin commitear:"
        git status --short
        echo ""
        read -p "¿Hacer commit y push antes de deploy? (s/n): " do_commit
        if [ "$do_commit" = "s" ] || [ "$do_commit" = "S" ]; then
            read -p "Mensaje de commit: " commit_msg
            [ -z "$commit_msg" ] && commit_msg="Deploy: $(date '+%Y-%m-%d %H:%M:%S')"
            git add .
            git commit -m "$commit_msg"
            git push origin main || git push origin master || true
        fi
    fi
    echo ""
fi

# Paso 3: Deploy a VM por SSH
echo "📦 Ejecutando deploy a VM (SSH)..."
echo ""
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"$SCRIPT_DIR/deploy_completo.sh"

echo ""
echo "✅ Proceso completado"
echo "📍 Verifica el servicio en la URL de tu VM (ej. http://34.176.144.166:5001)"
echo ""

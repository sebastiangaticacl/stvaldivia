#!/bin/bash
# Script para hacer push a GitHub con autenticación

echo "🚀 PUSH A GITHUB"
echo "=================="
echo ""
echo "📦 Commit a subir:"
git log --oneline -1
echo ""
echo "📍 Branch: main"
echo "🌐 Remoto: origin (https://github.com/stvaldivia/stvaldivia.git)"
echo ""
echo "⚠️  Este script requiere autenticación"
echo ""
echo "Si es la primera vez, necesitarás:"
echo "  1. Username: tu_usuario_github"
echo "  2. Password: Personal Access Token"
echo "     (Obtener en: https://github.com/settings/tokens)"
echo ""
read -p "¿Continuar con el push? (y/N): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Push cancelado"
    exit 1
fi

echo ""
echo "🔄 Haciendo push..."
git push origin main

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ PUSH EXITOSO"
    echo ""
    echo "🔗 Verificar en: https://github.com/stvaldivia/stvaldivia"
    echo ""
    echo "📊 Último commit en origin/main:"
    git log origin/main -1 --oneline
else
    echo ""
    echo "❌ PUSH FALLÓ"
    echo ""
    echo "💡 OPCIONES:"
    echo "  1. Usar VS Code (ver GUIA_PUSH_VSCODE.md)"
    echo "  2. Obtener Personal Access Token:"
    echo "     https://github.com/settings/tokens"
    echo "  3. Intentar de nuevo con: ./push_to_github.sh"
fi


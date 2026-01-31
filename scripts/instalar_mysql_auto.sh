#!/bin/bash
# Instalación automática de MySQL (sin confirmación)

set -euo pipefail

if ! command -v brew >/dev/null 2>&1; then
    echo "❌ Homebrew no encontrado"
    echo "Instalar primero: /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
    exit 1
fi

echo "Instalando MySQL..."
brew install mysql

echo "Iniciando MySQL..."
brew services start mysql

echo "Esperando que MySQL inicie..."
sleep 5

echo "✅ MySQL instalado e iniciado"
mysql --version


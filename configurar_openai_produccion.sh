#!/bin/bash
# Script para configurar OpenAI API Key en producción

# API_KEY debe ser configurada manualmente o pasada como parámetro
API_KEY="${1:-}"
if [ -z "$API_KEY" ]; then
    echo "❌ Error: Debes proporcionar la API key como parámetro o editarla en el script"
    echo "   Uso: $0 YOUR_OPENAI_API_KEY"
    exit 1
fi

echo "🔧 Configurando OpenAI API Key en producción..."
echo ""

# Verificar si estamos en el servidor correcto
if [ ! -d "/var/www/stvaldivia" ]; then
    echo "❌ Error: Este script debe ejecutarse en el servidor de producción"
    echo "   Directorio esperado: /var/www/stvaldivia"
    exit 1
fi

# Método 1: Agregar a /etc/environment (persistente para todos los usuarios)
echo "📝 Método 1: Agregando a /etc/environment (requiere sudo)..."
if ! grep -q "OPENAI_API_KEY=" /etc/environment 2>/dev/null; then
    echo "OPENAI_API_KEY=${API_KEY}" | sudo tee -a /etc/environment > /dev/null
    echo "✅ Agregado a /etc/environment"
else
    echo "⚠️  OPENAI_API_KEY ya existe en /etc/environment"
    read -p "¿Deseas actualizarlo? (s/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Ss]$ ]]; then
        sudo sed -i.bak "s|^OPENAI_API_KEY=.*|OPENAI_API_KEY=${API_KEY}|" /etc/environment
        echo "✅ Actualizado en /etc/environment"
    fi
fi

# Método 2: Agregar al servicio systemd (si existe)
SERVICE_FILE="/etc/systemd/system/stvaldivia.service"
if [ -f "$SERVICE_FILE" ]; then
    echo ""
    echo "📝 Método 2: Verificando servicio systemd..."
    if ! grep -q "Environment=\"OPENAI_API_KEY=" "$SERVICE_FILE" 2>/dev/null; then
        echo "⚠️  No se encontró OPENAI_API_KEY en el servicio"
        echo "   Para agregarlo manualmente, edita: $SERVICE_FILE"
        echo "   Agrega esta línea en la sección [Service]:"
        echo "   Environment=\"OPENAI_API_KEY=${API_KEY}\""
    else
        echo "✅ OPENAI_API_KEY ya está en el servicio"
    fi
fi

# Método 3: Exportar en la sesión actual (temporal)
echo ""
echo "📝 Método 3: Exportando en sesión actual (temporal)..."
export OPENAI_API_KEY="${API_KEY}"
echo "✅ Exportado para esta sesión"

# Verificar
echo ""
echo "🔍 Verificando configuración..."
if [ -n "$OPENAI_API_KEY" ]; then
    echo "✅ OPENAI_API_KEY está configurada (${#OPENAI_API_KEY} caracteres)"
else
    echo "❌ OPENAI_API_KEY no está configurada"
fi

echo ""
echo "📋 Próximos pasos:"
echo "1. Si usaste /etc/environment, reinicia el servidor o recarga las variables:"
echo "   source /etc/environment"
echo ""
echo "2. Si modificaste el servicio systemd, recarga y reinicia:"
echo "   sudo systemctl daemon-reload"
echo "   sudo systemctl restart stvaldivia"
echo ""
echo "3. Verifica que funciona:"
echo "   curl -s https://api.openai.com/v1/models -H \"Authorization: Bearer \$OPENAI_API_KEY\" | head -5"
echo ""
echo "4. Prueba el bot en:"
echo "   https://stvaldivia.cl/admin/bot/logs"
echo "   https://stvaldivia.cl/bimba"


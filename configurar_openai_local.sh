#!/bin/bash
# Script para configurar OpenAI API Key en desarrollo local

echo "🤖 Configuración de OpenAI API Key para BIMBA"
echo "=============================================="
echo ""

# Verificar si ya existe una API key configurada
if [ -f .env ]; then
    if grep -q "OPENAI_API_KEY=" .env && ! grep -q "OPENAI_API_KEY=TU_API_KEY_AQUI" .env; then
        echo "⚠️  Ya existe una API key configurada en .env"
        read -p "¿Deseas actualizarla? (s/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Ss]$ ]]; then
            echo "✅ Configuración cancelada"
            exit 0
        fi
    fi
fi

# Solicitar API key
echo "📝 Para obtener tu API key de OpenAI:"
echo "   1. Ve a: https://platform.openai.com/api-keys"
echo "   2. Inicia sesión o crea una cuenta"
echo "   3. Click en 'Create new secret key'"
echo "   4. Copia la clave (empieza con sk-...)"
echo ""
read -p "🔑 Ingresa tu API key de OpenAI: " api_key

if [ -z "$api_key" ]; then
    echo "❌ Error: La API key no puede estar vacía"
    exit 1
fi

# Validar formato básico (debe empezar con sk-)
if [[ ! $api_key =~ ^sk- ]]; then
    echo "⚠️  Advertencia: La API key debería empezar con 'sk-'"
    read -p "¿Continuar de todas formas? (s/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Ss]$ ]]; then
        echo "❌ Configuración cancelada"
        exit 1
    fi
fi

# Actualizar o crear archivo .env
if [ -f .env ]; then
    # Actualizar la línea existente
    if grep -q "OPENAI_API_KEY=" .env; then
        sed -i.bak "s|^OPENAI_API_KEY=.*|OPENAI_API_KEY=${api_key}|" .env
        echo "✅ API key actualizada en .env"
    else
        # Agregar al final del archivo
        echo "" >> .env
        echo "OPENAI_API_KEY=${api_key}" >> .env
        echo "✅ API key agregada a .env"
    fi
else
    # Crear nuevo archivo .env
    cat > .env << EOF
# Configuración de OpenAI para BIMBA - Inteligencia Generativa
OPENAI_API_KEY=${api_key}

# Configuración opcional de OpenAI (no requerida)
# OPENAI_ORGANIZATION_ID=org-xxxxx
# OPENAI_PROJECT_ID=proj-xxxxx

# Modelo a usar (por defecto: gpt-4o-mini - más económico)
# OPENAI_DEFAULT_MODEL=gpt-4o-mini

# Temperatura para la generación (0.0-1.0, por defecto: 0.7)
# OPENAI_DEFAULT_TEMPERATURE=0.7
EOF
    echo "✅ Archivo .env creado con la API key"
fi

# Limpiar backup si existe
[ -f .env.bak ] && rm .env.bak

echo ""
echo "✅ ¡Configuración completada!"
echo ""
echo "📋 Próximos pasos:"
echo "   1. Reinicia tu servidor Flask si está corriendo"
echo "   2. Visita: http://localhost:5000/bimba"
echo "   3. Prueba enviando un mensaje al chatbot"
echo ""
echo "💡 Para verificar que funciona, revisa los logs o visita:"
echo "   http://localhost:5000/admin/bot/config (si eres admin)"
echo ""


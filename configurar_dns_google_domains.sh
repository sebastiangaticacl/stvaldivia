#!/bin/bash

# Script para configurar DNS en Google Domains
# Este script te guiará paso a paso

echo "=========================================="
echo "  CONFIGURACIÓN DNS EN GOOGLE DOMAINS"
echo "=========================================="
echo ""
echo "IP de la VM: 34.176.68.46"
echo "Dominio: stvaldivia.cl"
echo ""
echo "Este script te ayudará a configurar los registros DNS."
echo ""

# Abrir Google Domains en el navegador
echo "1. Abriendo Google Domains en tu navegador..."
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    open "https://domains.google.com/registrar/stvaldivia.cl/dns"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    xdg-open "https://domains.google.com/registrar/stvaldivia.cl/dns" 2>/dev/null || echo "Por favor, abre manualmente: https://domains.google.com/registrar/stvaldivia.cl/dns"
else
    echo "Por favor, abre manualmente: https://domains.google.com/registrar/stvaldivia.cl/dns"
fi

echo ""
echo "2. Una vez en Google Domains, sigue estos pasos:"
echo ""
echo "   a) Ve a la sección 'Registros de recursos personalizados'"
echo "   b) Busca o crea estos 2 registros A:"
echo ""
echo "      Registro 1:"
echo "      - Tipo: A"
echo "      - Nombre: @"
echo "      - IP: 34.176.68.46"
echo "      - TTL: 3600"
echo ""
echo "      Registro 2:"
echo "      - Tipo: A"
echo "      - Nombre: www"
echo "      - IP: 34.176.68.46"
echo "      - TTL: 3600"
echo ""
echo "   c) Guarda los cambios"
echo ""
echo "3. Después de guardar, este script verificará la propagación DNS..."
echo ""
read -p "Presiona ENTER cuando hayas guardado los cambios en Google Domains..."

# Esperar un poco
echo ""
echo "Esperando 10 segundos antes de verificar..."
sleep 10

# Verificar DNS
echo ""
echo "Verificando propagación DNS..."
echo ""

# Verificar stvaldivia.cl
IP_STVALDIVIA=$(dig +short stvaldivia.cl A 2>/dev/null | head -1)
if [ "$IP_STVALDIVIA" = "34.176.68.46" ]; then
    echo "✅ stvaldivia.cl apunta correctamente a 34.176.68.46"
else
    echo "⏳ stvaldivia.cl aún no apunta correctamente (actual: $IP_STVALDIVIA)"
    echo "   Esto es normal, puede tardar 10-30 minutos en propagarse"
fi

# Verificar www.stvaldivia.cl
IP_WWW=$(dig +short www.stvaldivia.cl A 2>/dev/null | head -1)
if [ "$IP_WWW" = "34.176.68.46" ]; then
    echo "✅ www.stvaldivia.cl apunta correctamente a 34.176.68.46"
else
    echo "⏳ www.stvaldivia.cl aún no apunta correctamente (actual: $IP_WWW)"
    echo "   Esto es normal, puede tardar 10-30 minutos en propagarse"
fi

echo ""
echo "=========================================="
echo "  VERIFICACIÓN COMPLETA"
echo "=========================================="
echo ""
echo "Si los DNS aún no están propagados, espera 10-30 minutos y ejecuta:"
echo "  dig stvaldivia.cl +short"
echo "  dig www.stvaldivia.cl +short"
echo ""
echo "Cuando ambos muestren 34.176.68.46, el dominio estará funcionando."
echo ""



#!/bin/bash
# Script para cerrar/abrir el sitio al público
# Uso: ./cerrar_sitio.sh [cerrar|abrir]

ACTION="${1:-cerrar}"

if [ "$ACTION" == "cerrar" ]; then
    echo "🔒 Cerrando sitio al público..."
    # En producción, configurar variable de entorno
    export SITE_CLOSED=true
    echo "✅ Variable SITE_CLOSED=true configurada"
    echo ""
    echo "Para activar en producción, ejecuta en el servidor:"
    echo "  export SITE_CLOSED=true"
    echo "  # O agregar a /etc/environment o archivo de configuración del servicio"
    echo ""
    echo "Luego reinicia el servicio:"
    echo "  sudo systemctl restart gunicorn"
elif [ "$ACTION" == "abrir" ]; then
    echo "🔓 Abriendo sitio al público..."
    export SITE_CLOSED=false
    echo "✅ Variable SITE_CLOSED=false configurada"
    echo ""
    echo "Para desactivar en producción, ejecuta en el servidor:"
    echo "  export SITE_CLOSED=false"
    echo "  # O remover de /etc/environment o archivo de configuración del servicio"
    echo ""
    echo "Luego reinicia el servicio:"
    echo "  sudo systemctl restart gunicorn"
else
    echo "Uso: $0 [cerrar|abrir]"
    exit 1
fi


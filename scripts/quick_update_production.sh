#!/bin/bash
# Script rápido para actualizar producción
# Uso: ./scripts/quick_update_production.sh

set -e

WEBROOT="/var/www/stvaldivia"

echo "=========================================="
echo "🚀 ACTUALIZACIÓN RÁPIDA DE PRODUCCIÓN"
echo "=========================================="
echo ""

# 1) Actualizar código
echo "📥 1) Actualizando código desde Git..."
cd "$WEBROOT"
git fetch origin
git pull origin main
echo "   ✅ Código actualizado"
echo "   Último commit:"
git log -1 --oneline
echo ""

# 2) Verificar que el cambio está aplicado
echo "🔍 2) Verificando cambios aplicados..."
if grep -q "Incluir cajas de prueba siempre" "$WEBROOT/app/services/pos_service.py"; then
    echo "   ✅ Cambio de cajas de prueba aplicado"
else
    echo "   ❌ ERROR: Cambio NO encontrado"
    exit 1
fi
echo ""

# 3) Verificar/crear cajas de prueba
echo "📦 3) Verificando cajas de prueba en BD..."
python3 "$WEBROOT/scripts/verify_and_seed_cajas.py"
echo ""

# 4) Reiniciar servicios
echo "🔄 4) Reiniciando servicios..."
sudo systemctl restart gunicorn
sleep 2
sudo systemctl restart nginx
echo "   ✅ Servicios reiniciados"
echo ""

# 5) Verificar que los servicios están activos
echo "✅ 5) Verificando estado de servicios..."
if systemctl is-active --quiet gunicorn; then
    echo "   ✅ gunicorn está activo"
else
    echo "   ❌ ERROR: gunicorn NO está activo"
    echo "   Revisar logs: sudo journalctl -u gunicorn -n 50"
    exit 1
fi

if systemctl is-active --quiet nginx; then
    echo "   ✅ nginx está activo"
else
    echo "   ❌ ERROR: nginx NO está activo"
    exit 1
fi
echo ""

# 6) Mostrar últimos logs
echo "📋 6) Últimos logs de gunicorn (últimas 20 líneas):"
echo "----------------------------------------"
sudo journalctl -u gunicorn -n 20 --no-pager | tail -20 || echo "   (no disponible)"
echo ""

echo "=========================================="
echo "✅ ACTUALIZACIÓN COMPLETADA"
echo "=========================================="
echo ""
echo "Próximos pasos:"
echo "1. Verificar que las cajas aparecen en /caja/login"
echo "2. Probar una venta de prueba"
echo "3. Si hay problemas, revisar: sudo journalctl -u gunicorn -n 100"
echo ""


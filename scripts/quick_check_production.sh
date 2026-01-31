#!/bin/bash
# Script rápido para verificar estado en producción
# Uso: ./scripts/quick_check_production.sh

set -e

WEBROOT="/var/www/stvaldivia"

echo "=========================================="
echo "🔍 VERIFICACIÓN RÁPIDA DE PRODUCCIÓN"
echo "=========================================="
echo ""

# 1) Verificar que el código está actualizado
echo "📋 1) Verificando código en $WEBROOT..."
if [ -d "$WEBROOT/.git" ]; then
    cd "$WEBROOT"
    echo "   Último commit:"
    git log -1 --oneline
    echo ""
    echo "   Estado del repo:"
    git status --short
    echo ""
    
    # Verificar si hay cambios remotos
    echo "   Verificando cambios remotos..."
    git fetch origin 2>/dev/null || echo "   ⚠️  No se pudo hacer fetch"
    LOCAL=$(git rev-parse HEAD)
    REMOTE=$(git rev-parse origin/main 2>/dev/null || echo "N/A")
    
    if [ "$LOCAL" != "$REMOTE" ] && [ "$REMOTE" != "N/A" ]; then
        echo "   ⚠️  El código local NO está actualizado con remoto"
        echo "   Ejecuta: cd $WEBROOT && git pull origin main"
    else
        echo "   ✅ Código actualizado"
    fi
else
    echo "   ⚠️  No es un repositorio git"
fi

# 2) Verificar que el cambio de pos_service.py está aplicado
echo ""
echo "📋 2) Verificando cambios en pos_service.py..."
if [ -f "$WEBROOT/app/services/pos_service.py" ]; then
    if grep -q "Incluir cajas de prueba siempre" "$WEBROOT/app/services/pos_service.py"; then
        echo "   ✅ Cambio aplicado: cajas de prueba visibles"
    else
        echo "   ❌ Cambio NO aplicado: falta actualizar código"
    fi
    
    if grep -q "NO filtrar cajas de prueba" "$WEBROOT/app/services/pos_service.py"; then
        echo "   ✅ Filtro de cajas de prueba desactivado"
    else
        echo "   ❌ Filtro aún activo"
    fi
else
    echo "   ❌ Archivo no encontrado"
fi

# 3) Verificar servicios
echo ""
echo "📋 3) Verificando servicios..."
if systemctl is-active --quiet gunicorn 2>/dev/null; then
    echo "   ✅ gunicorn está activo"
    echo "   Última reinicio:"
    systemctl show gunicorn -p ActiveEnterTimestamp --value 2>/dev/null || echo "   (no disponible)"
else
    echo "   ⚠️  gunicorn NO está activo"
fi

if systemctl is-active --quiet nginx 2>/dev/null; then
    echo "   ✅ nginx está activo"
else
    echo "   ⚠️  nginx NO está activo"
fi

# 4) Verificar cajas en BD (requiere .env)
echo ""
echo "📋 4) Verificando cajas en base de datos..."
if [ -f "$WEBROOT/.env" ]; then
    cd "$WEBROOT"
    python3 -c "
import sys
sys.path.insert(0, '.')
from app import create_app
app = create_app()
with app.app_context():
    from app.models.pos_models import PosRegister
    regs = PosRegister.query.filter_by(is_active=True).all()
    print(f'   Total de cajas activas: {len(regs)}')
    for r in regs:
        is_test = getattr(r, 'is_test', False)
        test_marker = ' 🧪 TEST' if is_test else ''
        print(f'   - {r.name} (ID: {r.id}, Código: {getattr(r, \"code\", \"N/A\")}){test_marker}')
" 2>/dev/null || echo "   ⚠️  No se pudo verificar BD (revisar .env y conexión)"
else
    echo "   ⚠️  No hay .env, saltando verificación de BD"
fi

echo ""
echo "=========================================="
echo "✅ VERIFICACIÓN COMPLETADA"
echo "=========================================="
echo ""
echo "Si los cambios no se ven:"
echo "1. Actualizar código: cd $WEBROOT && git pull origin main"
echo "2. Reiniciar servicios: sudo systemctl restart gunicorn nginx"
echo "3. Verificar logs: sudo journalctl -u gunicorn -n 50"
echo "4. Ejecutar seed: python3 $WEBROOT/scripts/verify_and_seed_cajas.py"
echo ""


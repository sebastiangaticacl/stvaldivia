#!/bin/bash

echo "🧪 PRUEBA VISUAL DE CSS RESPONSIVE - BIMBA"
echo "=========================================="
echo ""

# Verificar que el servidor esté corriendo
if curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:5001/ | grep -q "200"; then
    echo "✅ Servidor Flask está corriendo en http://127.0.0.1:5001"
else
    echo "⚠️  El servidor no está respondiendo. Iniciando servidor..."
    cd "$(dirname "$0")"
    python3 run_local.py > /tmp/flask_output.log 2>&1 &
    sleep 3
    if curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:5001/ | grep -q "200"; then
        echo "✅ Servidor iniciado correctamente"
    else
        echo "❌ Error al iniciar el servidor"
        exit 1
    fi
fi

echo ""
echo "📱 ABRIENDO NAVEGADOR..."
echo ""

# Abrir navegador en diferentes páginas importantes
echo "🌐 Abriendo página principal..."
open http://127.0.0.1:5001/

echo ""
echo "📋 INSTRUCCIONES PARA PROBAR RESPONSIVE:"
echo "========================================"
echo ""
echo "1. 📱 MOBILE (< 768px):"
echo "   - Abre las herramientas de desarrollador (F12 o Cmd+Option+I)"
echo "   - Activa el modo de dispositivo móvil (Cmd+Shift+M o Cmd+Option+M)"
echo "   - Prueba con: iPhone SE (375px), iPhone 12 Pro (390px), Galaxy S20 (360px)"
echo ""
echo "2. 📱 TABLET (768px - 1023px):"
echo "   - iPad (768px), iPad Pro (1024px en portrait)"
echo ""
echo "3. 💻 DESKTOP (>= 1024px):"
echo "   - Redimensiona manualmente la ventana"
echo ""
echo "4. ✅ VERIFICAR:"
echo "   - NO debe haber scroll horizontal"
echo "   - El menú móvil debe aparecer en < 768px"
echo "   - Las tablas deben convertirse en cards en móvil"
echo "   - Los elementos deben adaptarse correctamente"
echo ""
echo "5. 🔍 PÁGINAS A PROBAR:"
echo "   - Página principal: http://127.0.0.1:5001/"
echo "   - Admin (si estás logueado): http://127.0.0.1:5001/admin"
echo "   - Inventario: http://127.0.0.1:5001/admin/inventory"
echo ""
echo "Presiona Enter para abrir las páginas..."
read

open "http://127.0.0.1:5001/"
sleep 1
open "http://127.0.0.1:5001/admin"

echo ""
echo "✅ Listo! Prueba el responsive en el navegador"
echo ""


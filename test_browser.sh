#!/bin/bash
# Script para probar conexión desde diferentes formas

echo "=== Prueba de Conexión a stvaldivia.cl ==="
echo ""

echo "1. Probando con curl (HTTP):"
curl -I http://www.stvaldivia.cl 2>&1 | head -3
echo ""

echo "2. Probando con curl (HTTPS - debería fallar):"
curl -I https://www.stvaldivia.cl 2>&1 | head -3
echo ""

echo "3. Probando DNS:"
nslookup www.stvaldivia.cl 2>&1 | grep -A 2 "Name:"
echo ""

echo "4. Probando conectividad TCP al puerto 80:"
nc -zv 34.176.144.166 80 2>&1
echo ""

echo "5. Abriendo navegador con HTTP explícito:"
echo "   URL: http://www.stvaldivia.cl"
open http://www.stvaldivia.cl 2>&1
echo ""

echo "=== Si el navegador muestra ERR_CONNECTION_REFUSED ==="
echo "1. Asegúrate de usar http:// (no https://)"
echo "2. Limpia la caché del navegador (Cmd+Shift+Delete)"
echo "3. Prueba en modo incógnito"
echo "4. Verifica que no haya extensiones bloqueando (VPN, ad blockers)"
echo "5. Prueba con la IP directa: http://34.176.144.166"


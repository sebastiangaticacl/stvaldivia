#!/usr/bin/env bash
# Script de prueba con curl para PaymentIntent API

BASE_URL="${1:-http://127.0.0.1:5001}"
# BASE_URL="https://stvaldivia.cl"  # Para producción

echo "============================================================"
echo "PRUEBA: POST /caja/api/payment/intents"
echo "============================================================"
echo ""
echo "URL: $BASE_URL/caja/api/payment/intents"
echo ""

# Payload de prueba
PAYLOAD='{
  "register_id": "1",
  "provider": "GETNET",
  "amount_total": 1500.0
}'

echo "Payload:"
echo "$PAYLOAD" | jq '.' 2>/dev/null || echo "$PAYLOAD"
echo ""

# IMPORTANTE: Esta ruta requiere autenticación POS
# Para probar completamente necesitas una cookie de sesión válida

echo "⚠️  NOTA: Esta ruta requiere autenticación POS (sesión activa)"
echo ""
echo "Opción 1: Probar sin auth (veremos error 401):"
echo "------------------------------------------------------------"

curl -X POST "$BASE_URL/caja/api/payment/intents" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD" \
  -w "\n\nStatus: %{http_code}\n" \
  -s | jq '.' 2>/dev/null || cat

echo ""
echo "------------------------------------------------------------"
echo ""
echo "Opción 2: Probar con cookie de sesión:"
echo "  1. Abre navegador → /caja/login → haz login"
echo "  2. DevTools → Application → Cookies → copia 'session'"
echo "  3. Ejecuta:"
echo ""
echo "curl -X POST \"$BASE_URL/caja/api/payment/intents\" \\"
echo "  -H \"Content-Type: application/json\" \\"
echo "  -H \"Cookie: session=<TU_COOKIE_AQUI>\" \\"
echo "  -d '$PAYLOAD' | jq '.'"
echo ""
echo "============================================================"
echo "Verifica logs del servidor para:"
echo "  [PAYMENT_INTENT] READY→ id=<uuid> register=1 amount=1500.0"
echo "============================================================"















#!/usr/bin/env bash

# ===== CONFIGURACIÓN BÁSICA =====
BASE_URL="https://stvaldivia.cl"

# Si quieres probar con www, descomenta esta línea:
# BASE_URL="https://www.stvaldivia.cl"

# Paths típicos donde podría estar corriendo socket.io
PATHS=(
  "/socket.io/?EIO=4&transport=polling"
  "/tickets/socket.io/?EIO=4&transport=polling"
  "/mercedes/socket.io/?EIO=4&transport=polling"
)

echo "=== Test de Socket.IO en $BASE_URL ==="
echo ""

for p in "${PATHS[@]}"; do
  FULL_URL="${BASE_URL}${p}"
  echo ">>> Probando: $FULL_URL"
  # Socket.IO normalmente no acepta HEAD; usamos GET pero sin bajar el body:
  # -L: seguir redirecciones
  # -sS: silencioso pero muestra errores
  # -D - : dump headers a stdout
  # -o /dev/null: descartar body
  curl -L -sS -D - -o /dev/null "$FULL_URL" 2>/dev/null | \
    egrep 'HTTP/|WWW-Authenticate|Location' || \
    echo "  (sin respuesta HTTP visible)"

  echo ""
done

echo "=== FIN DEL TEST ==="
date



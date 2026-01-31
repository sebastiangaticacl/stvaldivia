#!/usr/bin/env bash
set -euo pipefail

# Uso:
#   ./test_public_socketio.sh <IP_O_DOMINIO>
#   ./test_public_socketio.sh                 # auto-detecta IP pública en GCE via metadata (si está disponible)

TARGET="${1:-}"

if [ -z "$TARGET" ] || [ "$TARGET" = "IP_PUBLICA" ]; then
  # Intentar auto-detectar IP pública desde metadata de Google Compute Engine
  TARGET="$(curl -sS -H "Metadata-Flavor: Google" \
    "http://metadata.google.internal/computeMetadata/v1/instance/network-interfaces/0/access-configs/0/external-ip" \
    2>/dev/null || true)"
fi

if [ -z "$TARGET" ]; then
  echo "❌ ERROR: No se pudo determinar la IP pública."
  echo "Uso: $0 <IP_O_DOMINIO>"
  exit 1
fi

echo "=== TEST HTTP (puerto 80) ==="
curl -sS -D - -o /dev/null "http://$TARGET/socket.io/?EIO=4&transport=polling" | head -60

echo ""
echo "=== TEST HTTPS (puerto 443) ==="
# Si se prueba contra IP, el certificado normalmente NO matchea el hostname.
# Usamos -k para poder inspeccionar headers (ej. 401 / WWW-Authenticate) sin bloquear por SSL.
if [[ "$TARGET" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  curl -k -sS -D - -o /dev/null "https://$TARGET/socket.io/?EIO=4&transport=polling" | head -60
else
  curl -sS -D - -o /dev/null "https://$TARGET/socket.io/?EIO=4&transport=polling" | head -60
fi

echo ""
echo "=== TEST COMPLETADO ==="
date
echo "Target probado: $TARGET"



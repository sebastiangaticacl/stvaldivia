#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="stvaldivia"
ZONE="southamerica-west1-a"
VM="stvaldivia"
USER="stvaldiviazal"

gcloud config set project "$PROJECT_ID" >/dev/null
gcloud config set compute/zone "$ZONE" >/dev/null

gcloud compute ssh "${USER}@${VM}" --command 'sudo bash -c "
set -euo pipefail

echo \"== Antes: UFW status ==\"
ufw status numbered || true

echo \"== Cerrando 5432/tcp (si existe) ==\"
# Eliminar reglas de 5432/tcp
if ufw status numbered | grep -q \"5432/tcp\"; then
  # Intentar eliminar por descripción
  echo \"Eliminando reglas de 5432/tcp...\"
  yes | ufw delete allow 5432/tcp 2>/dev/null || true
  
  # Si aún quedan, eliminar por número de regla
  while ufw status numbered | grep -q \"5432/tcp\"; do
    RULE_NUM=\$(ufw status numbered | grep \"5432/tcp\" | head -1 | sed \"s/^\[//\" | sed \"s/\].*//\" | awk \"{print \\\$1}\")
    if [ -n \"\$RULE_NUM\" ] && [ \"\$RULE_NUM\" -gt 0 ] 2>/dev/null; then
      echo \"Eliminando regla UFW #\$RULE_NUM\"
      yes | ufw delete \"\$RULE_NUM\" 2>/dev/null || break
    else
      break
    fi
  done
fi

echo \"== Después: UFW status ==\"
ufw status verbose || true

echo \"== Confirmar que 5432 solo escucha en localhost ==\"
ss -tulpen | grep \":5432\" || echo \"Puerto 5432 no encontrado\"

echo \"== OK seguridad ==\"
"'

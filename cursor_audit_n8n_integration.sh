#!/usr/bin/env bash
set -euo pipefail

# === Ajusta si cambia ===
PROJECT_ID="stvaldivia"
ZONE="southamerica-west1-a"
VM="stvaldivia"
USER="stvaldiviazal"
APP_DIR="/var/www/stvaldivia"
SERVICE="stvaldivia"

OUT_DIR="./n8n_audit_reports"
TS="$(date +%Y%m%d-%H%M%S)"
OUT_FILE="${OUT_DIR}/n8n_audit_${VM}_${TS}.txt"

mkdir -p "$OUT_DIR"

gcloud config set project "$PROJECT_ID" >/dev/null
gcloud config set compute/zone "$ZONE" >/dev/null

echo "== Ejecutando auditoría n8n en VM ${VM} =="
echo "== Reporte: ${OUT_FILE} =="

gcloud compute ssh "${USER}@${VM}" --command "sudo bash -lc '
set -euo pipefail

APP_DIR=\"$APP_DIR\"
SERVICE=\"$SERVICE\"

redact() {
  sed -E \"s/((API|SECRET|TOKEN|PASS|PASSWORD|KEY)[A-Z0-9_]*=)[^[:space:]]+/\\1<redacted>/g\"
}

section() {
  echo
  echo \"================================================================================\"
  echo \"== \$1\"
  echo \"================================================================================\"
}

section \"0) Estado servicio + env visibles (redactados)\"
systemctl is-active \"$SERVICE\" && echo \"service: active\" || echo \"service: inactive\"
systemctl show \"$SERVICE\" -p Environment --no-pager | redact

section \"1) Buscar archivos relacionados a n8n y rutas admin\"
cd \"$APP_DIR\"
echo \"-- candidatos n8n_* --\"
find . -maxdepth 5 -type f \\( -iname \"*n8n*\" -o -iname \"*systemconfig*\" -o -iname \"routes.py\" \\) | sed -n \"1,220p\"

echo
echo \"-- grep endpoints admin/api/n8n --\"
grep -R \"admin/api/n8n\" -n . 2>/dev/null | sed -n \"1,200p\" || true

section \"2) Mostrar código clave (si existe) — redacción aplicada\"
show_file () {
  local f=\"\$1\"
  if [ -f \"\$f\" ]; then
    echo
    echo \"--- FILE: \$f ---\"
    sed -n \"1,240p\" \"\$f\" | redact
  fi
}

# intenta ubicar archivos típicos
N8N_CLIENT=\$(find . -maxdepth 6 -type f -iname \"*n8n_client*.py\" | head -n 1 || true)
N8N_ROUTES=\$(find . -maxdepth 6 -type f -iname \"*n8n_routes*.py\" | head -n 1 || true)

show_file \"\$N8N_CLIENT\"
show_file \"\$N8N_ROUTES\"

# rutas principales (las que mencionaste)
show_file \"./app/routes.py\"
show_file \"./app/__init__.py\"

section \"3) Validaciones automáticas (contrato y seguridad)\"
echo \"-- Debe existir lectura DB->fallback env (SystemConfig o similar) --\"
grep -R \"SystemConfig\" -n . 2>/dev/null | sed -n \"1,120p\" || echo \"(no se encontró SystemConfig en código)\"


echo
echo \"-- Debe existir validación de token/firma (recomendado) --\"
grep -R \"x-n8n-token|X-N8N|signature|hmac|Authorization\" -n . 2>/dev/null | sed -n \"1,160p\" || echo \"(no se encontró token/firma en código)\"


echo
echo \"-- Evitar filtrar secretos (UI/API no debe devolver valores completos) --\"
grep -R \"OPENAI_API_KEY|API_KEY|WEBHOOK_SECRET|DATABASE_URL\" -n . 2>/dev/null | sed -n \"1,160p\" | redact || true

section \"4) Probar endpoint /admin/api/n8n/test (si existe) desde localhost\"
# intenta descubrir si hay ruta en app: buscamos \"n8n/test\" en código
if grep -R \"n8n/test\" -n . >/dev/null 2>&1; then
  echo \"Encontrado n8n/test en código. Probando request local...\"
  # intenta POST al endpoint local (asume que nginx sirve localhost)
  # Si requiere auth cookie/admin, esto puede devolver 401/302; igual sirve para confirmar que existe.
  set +e
  curl -sS -i -X POST http://127.0.0.1/admin/api/n8n/test -H \"Content-Type: application/json\" -d \"{}\" | sed -n \"1,60p\"
  set -e
else
  echo \"No se detectó endpoint n8n/test en el código.\"
fi

section \"5) Logs recientes buscando n8n\"
journalctl -u \"$SERVICE\" -n 300 --no-pager | egrep -i \"n8n|webhook|SystemConfig|config\" | redact || echo \"(no hay entradas recientes relacionadas a n8n)\"

section \"6) Checklist final (heurístico)\"
echo \"[OK] Servicio activo: \$(systemctl is-active $SERVICE)\"
echo \"[CHECK] Existe n8n_client: \${N8N_CLIENT:-no}\"
echo \"[CHECK] Existe n8n_routes: \${N8N_ROUTES:-no}\"
echo \"[CHECK] Endpoints /admin/api/n8n/* encontrados: \$(grep -R \"admin/api/n8n\" -n . 2>/dev/null | wc -l)\"
echo \"[CHECK] Referencias a SystemConfig: \$(grep -R \"SystemConfig\" -n . 2>/dev/null | wc -l)\"
echo \"[CHECK] Validación token/firma encontrada: \$(grep -R \"x-n8n-token|signature|hmac|Authorization\" -n . 2>/dev/null | wc -l)\"

echo
echo \"== FIN AUDITORIA N8N ==\"
' " | tee "$OUT_FILE"

echo
echo "✅ Reporte guardado en: $OUT_FILE"
echo "👉 Si me pegas ese reporte, te digo exactamente qué está perfecto y qué falta para producción (HMAC, retries, async, etc.)."

#!/usr/bin/env bash
set -euo pipefail

# === Ajusta si cambia ===
PROJECT_ID="stvaldivia"
ZONE="southamerica-west1-a"
VM="stvaldivia"
USER="stvaldiviazal"

# Carpeta app en la VM
APP_DIR="/var/www/stvaldivia"
SERVICE_APP="stvaldivia"
SERVICE_PROXY="cloud-sql-proxy"

# Reporte local
OUT_DIR="./site_review_reports"
TS="$(date +%Y%m%d-%H%M%S)"
OUT_FILE="${OUT_DIR}/site_review_${VM}_${TS}.txt"

mkdir -p "$OUT_DIR"

gcloud config set project "$PROJECT_ID" >/dev/null
gcloud config set compute/zone "$ZONE" >/dev/null

echo "== Ejecutando revisión completa contra VM ${VM} (${ZONE}) =="
echo "== Reporte: ${OUT_FILE} =="

gcloud compute ssh "${USER}@${VM}" --command "sudo bash -lc '
set -eo pipefail

redact() {
  # Redacta valores de secretos comunes: KEY=..., TOKEN=..., PASSWORD=..., etc.
  sed -E \"s/((API|SECRET|TOKEN|PASS|PASSWORD|KEY)[A-Z0-9_]*=)[^[:space:]]+/\\1<redacted>/g\"
}

section() {
  echo
  echo \"================================================================================\"
  echo \"== \$1\"
  echo \"================================================================================\"
}

kv() { printf \"%-28s %s\\n\" \"\$1\" \"\$2\"; }

section \"0) Snapshot del sistema\"
kv \"date\" \"\$(date -Is)\"
kv \"host\" \"\$(hostname)\"
kv \"uptime\" \"\$(uptime -p)\"
kv \"load\" \"\$(cut -d\" \" -f1-3 /proc/loadavg)\"
kv \"os\" \"\$(lsb_release -ds 2>/dev/null || echo unknown)\"
kv \"kernel\" \"\$(uname -r)\"
echo
df -h | sed -n \"1,40p\"
echo
free -h || true

section \"1) Servicios críticos (systemd)\"
for s in nginx ${SERVICE_APP} ${SERVICE_PROXY} mysql postgresql; do
  s=\"\${s:-}\"
  if [ -n \"\$s\" ] && systemctl list-unit-files 2>/dev/null | grep -q \"^\${s}\\.service\"; then
    printf \"%-18s %s\\n\" \"\$s\" \"\$(systemctl is-active \$s 2>/dev/null || echo inactive)\"
  else
    printf \"%-18s %s\\n\" \"\$s\" \"(no unit)\"
  fi
done

section \"2) Puertos escuchando y procesos\"
ss -tulpen | sed -n \"1,220p\"
echo
ps aux | egrep -i \"nginx|gunicorn|cloud-sql-proxy|mysql|postgres\" | grep -v egrep | sed -n \"1,220p\"

section \"3) App service unit (stvaldivia) + overrides (redactado)\"
systemctl cat ${SERVICE_APP} | redact | sed -n \"1,260p\"

section \"4) Variables que ve el servicio (redactado)\"
systemctl show ${SERVICE_APP} -p Environment --no-pager | redact

section \"5) Cloud SQL Proxy: estado y conexiones reales a 5432\"
systemctl status ${SERVICE_PROXY} --no-pager | sed -n \"1,80p\" || true
echo
echo \"-- conexiones a :5432 --\"
ss -tpn | grep \":5432\" || true

section \"6) Confirmación DB desde el proceso (sin secretos)\"
PID=\$(systemctl show -p MainPID --value ${SERVICE_APP})
kv \"MainPID\" \"\$PID\"
if [ \"\$PID\" != \"0\" ] && [ -r \"/proc/\$PID/environ\" ]; then
  echo \"ENV keys relevantes (nombres):\"
  tr \"\\0\" \"\\n\" < \"/proc/\$PID/environ\" | cut -d= -f1 | egrep \"DATABASE|SQLALCHEMY|FLASK|ENV\" || true
fi

section \"7) Nginx: validación + vhost + TLS\"
nginx -t 2>&1 | sed -n \"1,120p\" || true
echo
echo \"-- sites-enabled --\"
ls -la /etc/nginx/sites-enabled 2>/dev/null || true
echo
echo \"-- grep TLS/certs --\"
grep -R \"ssl_certificate\\|ssl_certificate_key\\|listen 443\" -n /etc/nginx 2>/dev/null | sed -n \"1,200p\" || true

section \"8) HTTP/HTTPS checks (local)\"
echo \"-- HTTP localhost --\"
curl -sSI http://127.0.0.1/ | head -n 20 || true
echo
echo \"-- HTTPS localhost (sin verificar CA) --\"
curl -k -sSI https://127.0.0.1/ | head -n 25 || true
echo
echo \"-- App directo (gunicorn) --\"
curl -sSI http://127.0.0.1:5001/ | head -n 20 || true

section \"9) Logs recientes (app + nginx) [redactados]\"
echo \"-- journalctl app (200) --\"
journalctl -u ${SERVICE_APP} -n 200 --no-pager | redact
echo
echo \"-- nginx error.log (120) --\"
tail -n 120 /var/log/nginx/error.log 2>/dev/null | redact || true

section \"10) Firewall local (UFW) + resumen iptables\"
ufw status verbose 2>/dev/null || echo \"ufw no configurado\"
echo
iptables -S 2>/dev/null | sed -n \"1,140p\" || true

section \"11) Revisión del código (rápida, orientada a producción)\"
cd ${APP_DIR} || { echo \"No existe ${APP_DIR}\"; exit 0; }

echo \"-- repo state --\"
git rev-parse --abbrev-ref HEAD 2>/dev/null || true
git rev-parse --short HEAD 2>/dev/null || true
git status --porcelain 2>/dev/null || true

echo
echo \"-- estructura top --\"
ls -la | sed -n \"1,120p\"

echo
echo \"-- entrypoints --\"
[ -f wsgi.py ] && { echo \"[wsgi.py]\"; sed -n \"1,160p\" wsgi.py; } || echo \"wsgi.py: (no)\"

echo
echo \"-- buscar SQLite legacy / bimba.db / URLs DB --\"
grep -R \"bimba\\.db|sqlite:////|sqlite:///|DATABASE_URL|DATABASE_PROD_URL|SQLALCHEMY_DATABASE_URI\" -n . 2>/dev/null | sed -n \"1,220p\" || true

echo
echo \"-- buscar secretos hardcodeados (heurístico) --\"
grep -R \"OPENAI_API_KEY|sk-|Bearer |api_key\\s*=|secret\\s*=|password\\s*=|TOKEN\\s*=|PRIVATE KEY\" -n . 2>/dev/null | sed -n \"1,200p\" | redact || true

echo
echo \"-- buscar imports problemáticos (Product/GuardarropiaTicket) --\"
grep -R \"from .* import .*Product|import Product|GuardarropiaTicket\" -n . 2>/dev/null | sed -n \"1,200p\" || true

echo
echo \"-- requirements (top) --\"
[ -f requirements.txt ] && sed -n \"1,220p\" requirements.txt || true

section \"12) Performance quick look\"
echo \"-- top (snapshot) --\"
top -b -n 1 | sed -n \"1,30p\" || true
echo
echo \"-- systemd resource usage --\"
systemctl status ${SERVICE_APP} --no-pager | sed -n \"1,30p\" || true

echo
echo \"== FIN DE REVISION COMPLETA ==\"
' " | tee "$OUT_FILE"

echo
echo "✅ Reporte generado: $OUT_FILE"
echo "👉 Ábrelo y pégame las secciones que te preocupen (o todo), y te doy un plan de mejoras + comandos."


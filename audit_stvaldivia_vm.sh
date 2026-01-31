#!/usr/bin/env bash
# audit_stvaldivia_vm.sh
# Ejecuta este script DESDE TU LAPTOP en Cursor.
# Hace una auditoría profunda del stack en la VM (systemd/gunicorn/env/nginx/ssl/db/cloudsql proxy/red/firewall/logs)
# y guarda un reporte local en ./audit_reports/

set -euo pipefail

###############################################################################
# CONFIG (AJUSTA SI CAMBIA)
###############################################################################
PROJECT_ID="stvaldivia"
ZONE="southamerica-west1-a"
VM_NAME="stvaldivia"
SSH_USER="stvaldiviazal"   # tu usuario ssh en la VM

OUT_DIR="./audit_reports"
TS="$(date +%Y%m%d-%H%M%S)"
OUT_FILE="${OUT_DIR}/audit_${VM_NAME}_${TS}.txt"

mkdir -p "$OUT_DIR"

echo "== Configurando gcloud =="
gcloud config set project "$PROJECT_ID" >/dev/null
gcloud config set compute/zone "$ZONE" >/dev/null

echo "== Ejecutando auditoría remota en VM ${VM_NAME} (esto puede tardar un poco) =="

# Nota: usamos sudo para leer configs/servicios; no imprimimos secretos (redactamos).
gcloud compute ssh "${SSH_USER}@${VM_NAME}" --zone "$ZONE" --command "sudo bash -lc '
set -euo pipefail

redact() {
  # redacta cualquier posible secreto en líneas con KEY=...
  sed -E \"s/((API|SECRET|TOKEN|PASS|PASSWORD|KEY)[A-Z0-9_]*=)[^[:space:]]+/\\1<redacted>/g\"
}

section() {
  echo
  echo \"###############################################################################\"
  echo \"# \$1\"
  echo \"###############################################################################\"
}

section \"0) FECHA / HOST / USUARIO\"
date -Is
hostname
whoami
uptime
echo \"OS:\"; lsb_release -a 2>/dev/null || true
echo \"KERNEL:\"; uname -a

section \"1) INVENTARIO DE SERVICIOS CLAVE\"
systemctl is-active nginx && echo \"nginx: active\" || echo \"nginx: inactive\"
systemctl is-active apache2 && echo \"apache2: active\" || echo \"apache2: inactive\"
systemctl is-active stvaldivia && echo \"stvaldivia: active\" || echo \"stvaldivia: inactive\"
systemctl is-active cloud-sql-proxy && echo \"cloud-sql-proxy: active\" || echo \"cloud-sql-proxy: inactive\"
systemctl is-active mysql && echo \"mysql: active\" || echo \"mysql: inactive\"
systemctl is-active postgresql && echo \"postgresql: active\" || echo \"postgresql: inactive\"

section \"2) PUERTOS ESCUCHANDO (ss -tulpen)\"
ss -tulpen | sed -n \"1,220p\"

section \"3) PROCESOS (gunicorn/nginx/db/proxy)\"
ps aux | egrep -i \"gunicorn|nginx|cloud-sql-proxy|postgres|mysql\" | grep -v egrep | sed -n \"1,220p\"

section \"4) systemd: stvaldivia (unit + overrides) [SIN SECRETOS]\"
systemctl cat stvaldivia | redact | sed -n \"1,260p\"

section \"5) systemd: variables que ve stvaldivia (redactadas)\"
systemctl show stvaldivia -p Environment --no-pager | redact

section \"6) CONFIRMACION REAL: conexiones gunicorn -> postgres (5432)\"
# muestra conexiones a :5432 y quién las usa
ss -tpn | grep \":5432\" || true

# Mostrar ENV del proceso main PID (sin valores)
PID=\$(systemctl show -p MainPID --value stvaldivia)
echo \"MainPID: \$PID\"
if [ \"\$PID\" != \"0\" ] && [ -r \"/proc/\$PID/environ\" ]; then
  echo \"ENV keys del proceso (solo nombres):\"
  tr \"\\0\" \"\\n\" < \"/proc/\$PID/environ\" | cut -d= -f1 | egrep \"DATABASE|SQLALCHEMY|FLASK|ENV\" || true
fi

section \"7) NGINX: config efectiva + site enabled\"
nginx -t 2>&1 | sed -n \"1,120p\" || true
echo
echo \"-- sites-enabled --\"
ls -la /etc/nginx/sites-enabled || true
echo
echo \"-- stvaldivia site (si existe) --\"
if [ -f /etc/nginx/sites-enabled/stvaldivia ]; then
  sed -n \"1,240p\" /etc/nginx/sites-enabled/stvaldivia
elif [ -f /etc/nginx/sites-available/stvaldivia ]; then
  sed -n \"1,240p\" /etc/nginx/sites-available/stvaldivia
else
  echo \"No hay site stvaldivia en sites-enabled/available\"
fi

section \"8) SSL: certificados referenciados + permisos (si hay)\"
# busca referencias a ssl_certificate en configs (sin imprimir claves)
grep -R \"ssl_certificate\" -n /etc/nginx 2>/dev/null | sed -n \"1,120p\" || true
echo
echo \"Permisos comunes LetsEncrypt (si existe):\"
ls -ld /etc/letsencrypt /etc/letsencrypt/live 2>/dev/null || true
find /etc/letsencrypt/live -maxdepth 3 -type f -name \"fullchain.pem\" -o -name \"privkey.pem\" 2>/dev/null | while read -r f; do
  ls -l \"\$f\"
done || true

section \"9) HEALTHCHECK (interno y vía nginx)\"
echo \"-- gunicorn directo (localhost:5001) --\"
curl -sSI http://127.0.0.1:5001 | head -n 20 || true
echo
echo \"-- nginx (localhost:80) --\"
curl -sSI http://127.0.0.1/ | head -n 20 || true

section \"10) LOGS: stvaldivia (journalctl) últimas 200 líneas\"
journalctl -u stvaldivia -n 200 --no-pager | redact

section \"11) LOGS: nginx últimas 120 líneas\"
echo \"-- /var/log/nginx/error.log --\"
tail -n 120 /var/log/nginx/error.log 2>/dev/null | redact || true
echo
echo \"-- /var/log/nginx/access.log (últimas 40) --\"
tail -n 40 /var/log/nginx/access.log 2>/dev/null || true

section \"12) APP: estructura + entrypoint + DB hints (sin secretos)\"
cd /var/www/stvaldivia || { echo \"No existe /var/www/stvaldivia\"; exit 0; }
echo \"PWD: \$(pwd)\"
ls -la | sed -n \"1,120p\"
echo
echo \"-- wsgi.py (si existe) --\"
[ -f wsgi.py ] && sed -n \"1,120p\" wsgi.py || echo \"wsgi.py no existe\"
echo
echo \"-- app/__init__.py (si existe) --\"
[ -f app/__init__.py ] && sed -n \"1,200p\" app/__init__.py || echo \"app/__init__.py no existe\"
echo
echo \"-- referencias a sqlite/bimba.db/DATABASE_URL --\"
grep -R \"bimba\\.db|sqlite:////|sqlite:///|DATABASE_URL|DATABASE_PROD_URL|SQLALCHEMY_DATABASE_URI\" -n . 2>/dev/null | sed -n \"1,220p\" || true

section \"13) BD local (debería estar apagada si ya migraste) + uso de disco\"
echo \"-- servicios BD --\"
systemctl is-active mysql || true
systemctl is-active postgresql || true
echo
echo \"-- tamaño de sqlite legacy (si existe) --\"
ls -lh /var/www/stvaldivia/instance/bimba.db 2>/dev/null || echo \"No existe bimba.db\"
echo
echo \"-- uso disco --\"
df -h | sed -n \"1,60p\"

section \"14) FIREWALL LOCAL (ufw) y reglas iptables (resumen)\"
ufw status verbose 2>/dev/null || echo \"ufw no configurado\"
echo
iptables -S 2>/dev/null | sed -n \"1,120p\" || true

section \"15) METADATA GCE (red) + IPs\"
hostname -I || true
ip addr | sed -n \"1,200p\" || true

echo
echo \"== FIN AUDITORIA ==\"
' " | tee "$OUT_FILE"

echo
echo "✅ Reporte guardado en: $OUT_FILE"
echo "Siguiente: pégame ese archivo (o su contenido) y te hago el informe + acciones recomendadas."


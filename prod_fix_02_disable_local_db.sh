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

echo \"== Verificar conexiones reales a Postgres via proxy (deberías ver gunicorn->5432 localhost) ==\"
ss -tpn | grep \":5432\" || true

echo
echo \"== Parando BD local MySQL/Postgres (solo si existen) ==\"

if systemctl is-active --quiet mysql; then
  echo \"Stopping mysql\"
  systemctl stop mysql
fi
if systemctl is-enabled --quiet mysql 2>/dev/null; then
  echo \"Disabling mysql\"
  systemctl disable mysql
fi

if systemctl is-active --quiet postgresql; then
  echo \"Stopping postgresql\"
  systemctl stop postgresql
fi
if systemctl is-enabled --quiet postgresql 2>/dev/null; then
  echo \"Disabling postgresql\"
  systemctl disable postgresql
fi

echo
echo \"== Estado final servicios ==\"
systemctl is-active nginx || true
systemctl is-active stvaldivia || true
systemctl is-active cloud-sql-proxy || true
systemctl is-active mysql || true
systemctl is-active postgresql || true

echo
echo \"== Puertos DB locales (ideal: no deben estar escuchando 3306/5432 por mysqld/postgres local) ==\"
ss -tulpen | egrep \":(3306|5432)\\b\" || true
"'


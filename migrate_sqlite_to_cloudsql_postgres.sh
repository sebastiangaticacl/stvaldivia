#!/usr/bin/env bash
# migrate_sqlite_to_cloudsql_postgres.sh
# Ejecutar DESDE TU LAPTOP en Cursor

set -euo pipefail

###############################################################################
# CONFIGURACIÓN FIJA (TU ENTORNO)
###############################################################################
PROJECT_ID="stvaldivia"
ZONE="southamerica-west1-a"
REGION="southamerica-west1"
VM_NAME="stvaldivia"

CLOUDSQL_INSTANCE="stvaldivia-db"
DB_NAME="stvaldivia"
DB_USER="stvaldivia_user"
DB_PASSWORD="fvt37Kf3LZtbZ0YCIRO6JGMA4DVHAO"

APP_DIR="/var/www/stvaldivia"
SQLITE_DB="$APP_DIR/instance/bimba.db"
ENV_FILE="/etc/stvaldivia/stvaldivia.env"
APP_SERVICE="stvaldivia"

PROXY_DIR="/opt/cloud-sql"
PROXY_BIN="$PROXY_DIR/cloud-sql-proxy"
PROXY_SERVICE="cloud-sql-proxy"
PROXY_VERSION="v2.12.0"

###############################################################################
# 1) CONFIG GCP
###############################################################################
echo "== Configurando gcloud =="
gcloud config set project "$PROJECT_ID"
gcloud config set compute/zone "$ZONE"

###############################################################################
# 2) CREAR CLOUD SQL POSTGRES (SI NO EXISTE)
###############################################################################
echo "== Verificando instancia Cloud SQL =="
if ! gcloud sql instances describe "$CLOUDSQL_INSTANCE" >/dev/null 2>&1; then
  echo "Creando instancia Cloud SQL Postgres..."
  gcloud sql instances create "$CLOUDSQL_INSTANCE" \
    --database-version=POSTGRES_15 \
    --region="$REGION" \
    --tier=db-custom-1-3840 \
    --storage-type=SSD \
    --storage-size=20 \
    --availability-type=zonal
else
  echo "Instancia Cloud SQL ya existe."
fi

echo "== Creando base de datos =="
gcloud sql databases create "$DB_NAME" \
  --instance="$CLOUDSQL_INSTANCE" >/dev/null 2>&1 || true

echo "== Creando/actualizando usuario DB =="
if gcloud sql users list --instance="$CLOUDSQL_INSTANCE" --format="value(name)" | grep -qx "$DB_USER"; then
  gcloud sql users set-password "$DB_USER" \
    --instance="$CLOUDSQL_INSTANCE" \
    --password="$DB_PASSWORD"
else
  gcloud sql users create "$DB_USER" \
    --instance="$CLOUDSQL_INSTANCE" \
    --password="$DB_PASSWORD"
fi

CONNECTION_NAME="$(gcloud sql instances describe "$CLOUDSQL_INSTANCE" --format='value(connectionName)')"
echo "connectionName: $CONNECTION_NAME"

###############################################################################
# 3) EJECUTAR TODO EN LA VM
###############################################################################
echo "== Ejecutando migración en la VM =="

gcloud compute ssh "$VM_NAME" --zone "$ZONE" --command "sudo bash -lc '
set -euo pipefail

echo \"[VM] Verificando SQLite\"
test -f \"$SQLITE_DB\" || (echo \"ERROR: no existe $SQLITE_DB\" && exit 1)

echo \"[VM] Instalando dependencias\"
apt-get update -y
apt-get install -y curl ca-certificates pgloader postgresql-client

echo \"[VM] Instalando Cloud SQL Auth Proxy\"
mkdir -p \"$PROXY_DIR\"
cd \"$PROXY_DIR\"

if [ ! -x \"$PROXY_BIN\" ]; then
  curl -L -o cloud-sql-proxy \
    https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/${PROXY_VERSION}/cloud-sql-proxy.linux.amd64
  chmod +x cloud-sql-proxy
fi

echo \"[VM] Configurando systemd del proxy\"
cat > /etc/systemd/system/${PROXY_SERVICE}.service <<EOF
[Unit]
Description=Cloud SQL Auth Proxy
After=network.target

[Service]
Type=simple
User=deploy
ExecStart=${PROXY_BIN} --address 127.0.0.1 --port 5432 ${CONNECTION_NAME}
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now ${PROXY_SERVICE}
systemctl is-active --quiet ${PROXY_SERVICE}

echo \"[VM] Migrando SQLite -> PostgreSQL\"
pgloader \
  sqlite:////var/www/stvaldivia/instance/bimba.db \
  postgresql://${DB_USER}:${DB_PASSWORD}@127.0.0.1:5432/${DB_NAME}

echo \"[VM] Verificando tablas\"
psql \"postgresql://${DB_USER}:${DB_PASSWORD}@127.0.0.1:5432/${DB_NAME}\" -c \"\\dt\"

echo \"[VM] Actualizando DATABASE_URL\"
cp ${ENV_FILE} ${ENV_FILE}.bak.\$(date +%F-%H%M%S)

if grep -q \"^DATABASE_URL=\" ${ENV_FILE}; then
  sed -i \"s|^DATABASE_URL=.*|DATABASE_URL=postgresql://${DB_USER}:${DB_PASSWORD}@127.0.0.1:5432/${DB_NAME}|\" ${ENV_FILE}
else
  echo \"DATABASE_URL=postgresql://${DB_USER}:${DB_PASSWORD}@127.0.0.1:5432/${DB_NAME}\" >> ${ENV_FILE}
fi

chmod 600 ${ENV_FILE}
chown root:root ${ENV_FILE}

echo \"[VM] Reiniciando aplicación\"
systemctl restart ${APP_SERVICE}
systemctl is-active --quiet ${APP_SERVICE}

echo \"[VM] Healthcheck\"
curl -fsSI http://127.0.0.1/ | head -n 10

echo
echo \"✅ MIGRACIÓN COMPLETA\"
echo \"- SQLite -> Cloud SQL PostgreSQL\"
echo \"- DATABASE_URL actualizado\"
echo \"- App corriendo correctamente\"
'"


#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="stvaldivia"
ZONE="southamerica-west1-a"
VM="stvaldivia"
USER="stvaldiviazal"

APP_DIR="/var/www/stvaldivia"
SERVICE="stvaldivia"
VENV="$APP_DIR/venv"

gcloud config set project "$PROJECT_ID" >/dev/null
gcloud config set compute/zone "$ZONE" >/dev/null

echo "== 1) Push a GitHub (desde tu laptop) =="
git status
git push

echo "== 2) Deploy remoto en VM: git pull + deps + restart =="
gcloud compute ssh "${USER}@${VM}" --command "sudo bash -lc '
set -euo pipefail

echo \"[VM] Repo: $APP_DIR\"
cd \"$APP_DIR\"

if [ -d .git ]; then
    echo \"[VM] Branch actual:\"
    git rev-parse --abbrev-ref HEAD
    echo \"[VM] Commit antes:\"
    git rev-parse --short HEAD
    
    echo \"[VM] Pull:\"
    sudo -u deploy git pull --ff-only
    
    echo \"[VM] Commit después:\"
    git rev-parse --short HEAD
else
    echo \"[VM] No es un repo git, clonando desde GitHub...\"
    REPO_URL=\"https://github.com/stvaldivia/stvaldivia.git\"
    TMP_DIR=\"/tmp/stvaldivia_deploy_\$(date +%s)\"
    git clone --depth 1 --branch main \"\$REPO_URL\" \"\$TMP_DIR\" || {
        echo \"❌ Error al clonar repositorio\"
        exit 1
    }
    sudo mkdir -p \"$APP_DIR\"
    sudo chown -R deploy:deploy \"$APP_DIR\"
    sudo -u deploy rsync -av --delete \\
        --exclude='.git' \\
        --exclude='instance' \\
        --exclude='logs' \\
        --exclude='venv' \\
        --exclude='__pycache__' \\
        --exclude='*.pyc' \\
        \"\$TMP_DIR/\" \"$APP_DIR/\"
    rm -rf \"\$TMP_DIR\"
    echo \"[VM] Código actualizado desde GitHub\"
fi

# Asegurar que wsgi.py existe (crítico para Gunicorn)
if [ ! -f \"$APP_DIR/wsgi.py\" ]; then
    echo \"[VM] ⚠️ wsgi.py no encontrado, creándolo...\"
    sudo -u deploy bash -c \"cat > $APP_DIR/wsgi.py << 'EOF'
from app import create_app
application = create_app()
EOF\"
    echo \"[VM] ✅ wsgi.py creado\"
fi

echo \"[VM] Instalar/actualizar deps:\"
sudo -u deploy \"$VENV/bin/pip\" install -r requirements.txt

echo \"[VM] Restart service:\"
systemctl restart \"$SERVICE\"
sleep 2
systemctl is-active --quiet \"$SERVICE\"
echo \"[VM] OK: $SERVICE activo\"

echo \"[VM] Healthcheck nginx:\"
curl -fsSI http://127.0.0.1/ | head -n 12

echo \"[VM] Logs recientes (errores/imports):\"
journalctl -u \"$SERVICE\" -n 120 --no-pager | egrep -i \"ModuleNotFoundError|ImportError|Traceback|ERROR\" || true
'"

echo
echo "✅ Deploy terminado."


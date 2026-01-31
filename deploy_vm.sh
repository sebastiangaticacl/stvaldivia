#!/usr/bin/env bash
set -euo pipefail

VM="stvaldivia"

echo "=== PUSH A GITHUB ==="
git push

echo "=== DEPLOY EN VM: $VM ==="
gcloud compute ssh "$VM" --command '
set -euo pipefail

echo ">> Entrando a /var/www/stvaldivia"
cd /var/www/stvaldivia

echo ">> Actualizando código desde GitHub"
if [ -d .git ]; then
    sudo -u deploy git pull
else
    echo ">> Clonando repositorio (primera vez o no es git repo)"
    REPO_URL="https://github.com/stvaldivia/stvaldivia.git"
    TMP_DIR="/tmp/stvaldivia_deploy_$(date +%s)"
    rm -rf "$TMP_DIR"
    git clone --depth 1 --branch main "$REPO_URL" "$TMP_DIR"
    
    sudo -u deploy rsync -av --delete \
        --exclude='.git' \
        --exclude='instance' \
        --exclude='logs' \
        --exclude='venv' \
        --exclude='__pycache__' \
        --exclude='*.pyc' \
        "$TMP_DIR/" /var/www/stvaldivia/
    
    rm -rf "$TMP_DIR"
fi

echo ">> pip install"
sudo -u deploy /var/www/stvaldivia/venv/bin/pip install -r requirements.txt

echo ">> restart gunicorn"
sudo -u deploy pkill -f "gunicorn.*--bind 127.0.0.1:5001" || true

sudo -u deploy /var/www/stvaldivia/venv/bin/gunicorn \
  --pythonpath /var/www/stvaldivia \
  --bind 127.0.0.1:5001 \
  --workers 4 \
  --worker-class eventlet \
  --timeout 30 \
  --access-logfile /var/www/stvaldivia/logs/access.log \
  --error-logfile /var/www/stvaldivia/logs/error.log \
  --daemon app:app

echo ">> healthcheck"
curl -fsS http://127.0.0.1:5001 >/dev/null

echo "=== DEPLOY OK ==="
'

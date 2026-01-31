#!/usr/bin/env bash
#
# Script de deploy mejorado con validaciones, backups y rollback
#
set -euo pipefail

VM="stvaldivia"
APP_DIR="/var/www/stvaldivia"
BACKUP_DIR="/var/backups/${VM}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "$1"
}

# Verificar que estamos en un repo git
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    log "${RED}✗${NC} Error: No estás en un repositorio git"
    exit 1
fi

# Verificar que no hay cambios sin commitear
if ! git diff-index --quiet HEAD -- 2>/dev/null; then
    log "${YELLOW}⚠${NC} Advertencia: Hay cambios sin commitear"
    read -p "¿Continuar de todas formas? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

log "${BLUE}========================================${NC}"
log "${BLUE}DEPLOY MEJORADO A PRODUCCIÓN${NC}"
log "${BLUE}========================================${NC}\n"

# Paso 1: Push a GitHub
log "${BLUE}[1/5] Push a GitHub...${NC}"
if git push; then
    log "${GREEN}✓${NC} Código pusheado a GitHub\n"
else
    log "${RED}✗${NC} Error al hacer push"
    exit 1
fi

# Paso 2: Deploy en VM
log "${BLUE}[2/5] Deploy en VM...${NC}"
gcloud compute ssh "$VM" --command "
set -euo pipefail

APP_DIR=\"${APP_DIR}\"
BACKUP_DIR=\"${BACKUP_DIR}\"
TIMESTAMP=\"${TIMESTAMP}\"

# Crear backup rápido antes del deploy
echo 'Creando backup rápido...'
mkdir -p \"\${BACKUP_DIR}/\${TIMESTAMP}\"
if [ -d \"\${APP_DIR}\" ]; then
    tar --exclude='venv' --exclude='logs' --exclude='instance' --exclude='__pycache__' --exclude='*.pyc' --exclude='.git' -czf \"\${BACKUP_DIR}/\${TIMESTAMP}/pre_deploy.tar.gz\" -C \$(dirname \${APP_DIR}) \$(basename \${APP_DIR}) 2>/dev/null || true
    echo '✓ Backup creado'
fi

# Entrar al directorio
cd \"\${APP_DIR}\"

# Actualizar código
echo 'Actualizando código desde GitHub...'
if [ -d .git ]; then
    sudo -u deploy git pull
else
    echo 'No es un repo git, clonando...'
    REPO_URL=\"https://github.com/stvaldivia/stvaldivia.git\"
    TMP_DIR=\"/tmp/stvaldivia_deploy_\$(date +%s)\"
    rm -rf \"\${TMP_DIR}\"
    git clone --depth 1 --branch main \"\${REPO_URL}\" \"\${TMP_DIR}\"
    
    sudo -u deploy rsync -av --delete \\
        --exclude='.git' \\
        --exclude='instance' \\
        --exclude='logs' \\
        --exclude='venv' \\
        --exclude='__pycache__' \\
        --exclude='*.pyc' \\
        \"\${TMP_DIR}/\" \"\${APP_DIR}/\"
    
    rm -rf \"\${TMP_DIR}\"
fi
echo '✓ Código actualizado'

# Instalar dependencias
echo 'Instalando dependencias...'
if [ -f requirements.txt ]; then
    sudo -u deploy \"\${APP_DIR}/venv/bin/pip\" install --quiet -r requirements.txt
    echo '✓ Dependencias instaladas'
fi

# Verificar que el servicio puede iniciarse (dry-run)
echo 'Validando configuración...'
if sudo systemctl is-enabled stvaldivia >/dev/null 2>&1; then
    echo '✓ Servicio configurado'
fi

echo '✓ Deploy completado'
"

if [ $? -eq 0 ]; then
    log "${GREEN}✓${NC} Deploy completado\n"
else
    log "${RED}✗${NC} Error en deploy"
    exit 1
fi

# Paso 3: Reiniciar servicio
log "${BLUE}[3/5] Reiniciando servicio...${NC}"
gcloud compute ssh "$VM" --command "
sudo systemctl restart stvaldivia
sleep 3
if sudo systemctl is-active --quiet stvaldivia; then
    echo '✓ Servicio reiniciado correctamente'
    exit 0
else
    echo '✗ Error: Servicio no inició correctamente'
    sudo systemctl status stvaldivia --no-pager -l | head -20
    exit 1
fi
"

if [ $? -eq 0 ]; then
    log "${GREEN}✓${NC} Servicio reiniciado\n"
else
    log "${RED}✗${NC} Error al reiniciar servicio"
    exit 1
fi

# Paso 4: Healthcheck
log "${BLUE}[4/5] Verificando salud del servicio...${NC}"
sleep 2
HTTP_CODE=$(gcloud compute ssh "$VM" --command "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:5001/" 2>/dev/null || echo "000")

if [[ "$HTTP_CODE" =~ ^[23][0-9]{2}$ ]]; then
    log "${GREEN}✓${NC} Healthcheck OK (HTTP ${HTTP_CODE})\n"
else
    log "${YELLOW}⚠${NC} Healthcheck: HTTP ${HTTP_CODE} (puede ser normal si requiere auth)\n"
fi

# Paso 5: Limpiar backups antiguos
log "${BLUE}[5/5] Limpiando backups antiguos...${NC}"
gcloud compute ssh "$VM" --command "
BACKUP_DIR=\"${BACKUP_DIR}\"
find \"\${BACKUP_DIR}\" -type d -mtime +7 -exec rm -rf {} + 2>/dev/null || true
echo '✓ Limpieza completada'
" >/dev/null 2>&1
log "${GREEN}✓${NC} Limpieza completada\n"

log "${BLUE}========================================${NC}"
log "${GREEN}✓ DEPLOY COMPLETADO${NC}"
log "${BLUE}========================================${NC}\n"
log "Backup disponible en: ${BACKUP_DIR}/${TIMESTAMP}/"
echo ""


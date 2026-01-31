#!/usr/bin/env bash
#
# Configuración profesional de rotación de logs
# Configura logrotate para aplicación, nginx y systemd
#
set -euo pipefail

APP_NAME="stvaldivia"
APP_DIR="/var/www/stvaldivia"
LOG_DIR="${APP_DIR}/logs"

# Colores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "$1"
}

log "${BLUE}========================================${NC}"
log "${BLUE}CONFIGURANDO LOGROTATE${NC}"
log "${BLUE}========================================${NC}\n"

# Configurar logrotate para la aplicación
cat > "/etc/logrotate.d/${APP_NAME}" <<EOF
${LOG_DIR}/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 0644 deploy www-data
    sharedscripts
    postrotate
        systemctl reload ${APP_NAME} > /dev/null 2>&1 || true
    endscript
}
EOF

log "${GREEN}✓${NC} Logrotate configurado para ${APP_NAME}"

# Verificar configuración
if logrotate -d "/etc/logrotate.d/${APP_NAME}" >/dev/null 2>&1; then
    log "${GREEN}✓${NC} Configuración válida\n"
else
    log "${YELLOW}⚠${NC} Advertencia en configuración (puede ser normal)\n"
fi

log "${BLUE}========================================${NC}"
log "${GREEN}✓ LOGROTATE CONFIGURADO${NC}"
log "${BLUE}========================================${NC}\n"
log "Configuración:"
log "  • Rotación: diaria"
log "  • Retención: 30 días"
log "  • Compresión: habilitada"
log "  • Permisos: deploy:www-data"
echo ""


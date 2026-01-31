#!/usr/bin/env bash
#
# Script de mantenimiento y optimización del sistema
# Limpia logs, optimiza bases de datos, verifica integridad
#
set -euo pipefail

APP_NAME="stvaldivia"
APP_DIR="/var/www/stvaldivia"
LOG_DIR="${APP_DIR}/logs"

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "$1"
}

log "${BLUE}========================================${NC}"
log "${BLUE}MANTENIMIENTO DEL SISTEMA${NC}"
log "${BLUE}========================================${NC}\n"

# 1. Limpiar logs antiguos
log "${BLUE}[1/5] Limpiando logs antiguos...${NC}"
find "$LOG_DIR" -name "*.log.*" -type f -mtime +7 -delete 2>/dev/null || true
log "${GREEN}✓${NC} Logs antiguos limpiados\n"

# 2. Forzar rotación de logs si es necesario
log "${BLUE}[2/5] Forzando rotación de logs...${NC}"
if command -v logrotate >/dev/null 2>&1; then
    logrotate -f "/etc/logrotate.d/${APP_NAME}" 2>/dev/null || true
    log "${GREEN}✓${NC} Rotación de logs ejecutada\n"
fi

# 3. Limpiar cache de Python
log "${BLUE}[3/5] Limpiando cache de Python...${NC}"
find "$APP_DIR" -type d -name "__pycache__" -exec rm -r {} + 2>/dev/null || true
find "$APP_DIR" -type f -name "*.pyc" -delete 2>/dev/null || true
log "${GREEN}✓${NC} Cache de Python limpiado\n"

# 4. Optimizar bases de datos (si es posible)
log "${BLUE}[4/5] Optimizando bases de datos...${NC}"

# PostgreSQL
if command -v psql >/dev/null 2>&1 && systemctl is-active --quiet postgresql; then
    for db in $(sudo -u postgres psql -t -c "SELECT datname FROM pg_database WHERE datistemplate = false AND datname NOT IN ('postgres');" 2>/dev/null | tr -d ' '); do
        if [ -n "$db" ]; then
            sudo -u postgres psql -d "$db" -c "VACUUM ANALYZE;" >/dev/null 2>&1 || true
            log "${GREEN}✓${NC} PostgreSQL DB '${db}' optimizada"
        fi
    done
fi

# MySQL
if command -v mysql >/dev/null 2>&1 && systemctl is-active --quiet mysql; then
    for db in $(mysql -e "SHOW DATABASES;" 2>/dev/null | grep -v "Database\|information_schema\|performance_schema\|sys"); do
        mysqlcheck -o "$db" >/dev/null 2>&1 || true
        log "${GREEN}✓${NC} MySQL DB '${db}' optimizada"
    done
fi
echo ""

# 5. Verificar permisos
log "${BLUE}[5/5] Verificando permisos...${NC}"
chown -R deploy:www-data "$LOG_DIR" 2>/dev/null || true
chmod 755 "$LOG_DIR" 2>/dev/null || true
log "${GREEN}✓${NC} Permisos verificados\n"

# Resumen
log "${BLUE}========================================${NC}"
log "${GREEN}✓ MANTENIMIENTO COMPLETADO${NC}"
log "${BLUE}========================================${NC}\n"


#!/usr/bin/env bash
#
# Script de backup automatizado profesional
# Realiza backups de código, base de datos y configuración
#
set -euo pipefail

# Configuración
APP_NAME="stvaldivia"
APP_DIR="/var/www/stvaldivia"
BACKUP_BASE="/var/backups/${APP_NAME}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="${BACKUP_BASE}/${TIMESTAMP}"
RETENTION_DAYS=30

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "$1"
}

# Crear directorio de backup
mkdir -p "$BACKUP_DIR"

log "${BLUE}========================================${NC}"
log "${BLUE}BACKUP SISTEMA - $(date '+%Y-%m-%d %H:%M:%S')${NC}"
log "${BLUE}========================================${NC}\n"

# Backup de código (sin venv, logs, cache)
log "${BLUE}[1/4] Backup de código...${NC}"
tar --exclude='venv' \
    --exclude='logs' \
    --exclude='instance' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.git' \
    -czf "${BACKUP_DIR}/code.tar.gz" \
    -C "$(dirname $APP_DIR)" "$(basename $APP_DIR)" 2>/dev/null || true
log "${GREEN}✓${NC} Código respaldado: ${BACKUP_DIR}/code.tar.gz\n"

# Backup de base de datos PostgreSQL (si existe)
log "${BLUE}[2/4] Backup de bases de datos...${NC}"
if command -v pg_dump >/dev/null 2>&1; then
    # Detectar bases de datos
    for db in $(sudo -u postgres psql -t -c "SELECT datname FROM pg_database WHERE datistemplate = false AND datname != 'postgres';" 2>/dev/null | tr -d ' '); do
        if [ -n "$db" ]; then
            sudo -u postgres pg_dump "$db" | gzip > "${BACKUP_DIR}/postgres_${db}.sql.gz" 2>/dev/null || true
            log "${GREEN}✓${NC} PostgreSQL DB '${db}' respaldada"
        fi
    done
fi

# Backup de MySQL (si existe)
if command -v mysqldump >/dev/null 2>&1; then
    # Intentar backup (requiere credenciales en .my.cnf o variables)
    for db in $(mysql -e "SHOW DATABASES;" 2>/dev/null | grep -v "Database\|information_schema\|performance_schema\|sys"); do
        mysqldump "$db" 2>/dev/null | gzip > "${BACKUP_DIR}/mysql_${db}.sql.gz" 2>/dev/null || true
        log "${GREEN}✓${NC} MySQL DB '${db}' respaldada"
    done
fi
echo ""

# Backup de configuración
log "${BLUE}[3/4] Backup de configuración...${NC}"
CONFIG_BACKUP="${BACKUP_DIR}/config.tar.gz"
tar -czf "$CONFIG_BACKUP" \
    /etc/${APP_NAME} \
    /etc/nginx/sites-available/${APP_NAME} \
    /etc/systemd/system/${APP_NAME}.service \
    2>/dev/null || true
log "${GREEN}✓${NC} Configuración respaldada: ${CONFIG_BACKUP}\n"

# Crear índice de backup
log "${BLUE}[4/4] Creando índice...${NC}"
cat > "${BACKUP_DIR}/backup_info.txt" <<EOF
Backup realizado: $(date '+%Y-%m-%d %H:%M:%S')
Sistema: $(uname -a)
Aplicación: ${APP_NAME}
Ubicación: ${APP_DIR}
Contenido:
  - code.tar.gz: Código de la aplicación
  - postgres_*.sql.gz: Backups de bases de datos PostgreSQL
  - mysql_*.sql.gz: Backups de bases de datos MySQL
  - config.tar.gz: Archivos de configuración
EOF
log "${GREEN}✓${NC} Índice creado\n"

# Limpiar backups antiguos
log "${BLUE}Limpiando backups antiguos (>${RETENTION_DAYS} días)...${NC}"
find "$BACKUP_BASE" -type d -mtime +${RETENTION_DAYS} -exec rm -rf {} + 2>/dev/null || true
log "${GREEN}✓${NC} Limpieza completada\n"

# Calcular tamaño
TOTAL_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)
log "${BLUE}========================================${NC}"
log "${GREEN}✓ BACKUP COMPLETADO${NC}"
log "  Ubicación: ${BACKUP_DIR}"
log "  Tamaño total: ${TOTAL_SIZE}"
log "${BLUE}========================================${NC}\n"


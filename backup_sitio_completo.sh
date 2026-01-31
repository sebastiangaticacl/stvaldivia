#!/bin/bash
# ============================================================================
# Script de Backup Completo del Sitio StValdivia
# ============================================================================

set -eo pipefail

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuración
BACKUP_DIR="/backups/stvaldivia"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_NAME="backup_stvaldivia_${TIMESTAMP}"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_NAME}"
SITE_PATH="/var/www/stvaldivia"

# Crear directorio de backup
mkdir -p "${BACKUP_PATH}"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}BACKUP COMPLETO DEL SITIO STVALDIVIA${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Fecha: $(date)"
echo "Directorio de backup: ${BACKUP_PATH}"
echo ""

# ============================================================================
# 1. BACKUP DE BASE DE DATOS
# ============================================================================
echo -e "${YELLOW}[1/5] Backup de base de datos...${NC}"

# Obtener configuración de la base de datos
# Cargar variables de entorno del sistema primero
if [ -f "${SITE_PATH}/.env" ]; then
    set +e  # Desactivar exit on error temporalmente
    source "${SITE_PATH}/.env" 2>/dev/null
    set -e  # Reactivar exit on error
fi

# Obtener DATABASE_URL si existe
DATABASE_URL=${DATABASE_URL:-""}

# Parsear DATABASE_URL si existe (formato: postgresql://user:pass@host:port/dbname)
if [ -n "$DATABASE_URL" ]; then
    # Extraer componentes de DATABASE_URL
    DB_STRING=$(echo "$DATABASE_URL" | sed -e 's|postgresql://||' -e 's|postgres://||')
    DB_USER=$(echo "$DB_STRING" | cut -d: -f1)
    DB_PASS=$(echo "$DB_STRING" | cut -d: -f2 | cut -d@ -f1)
    DB_HOST_PORT=$(echo "$DB_STRING" | cut -d@ -f2 | cut -d/ -f1)
    DB_HOST=$(echo "$DB_HOST_PORT" | cut -d: -f1)
    DB_PORT=$(echo "$DB_HOST_PORT" | cut -d: -f2)
    DB_NAME=$(echo "$DB_STRING" | cut -d/ -f2 | cut -d? -f1)
    
    DB_PORT=${DB_PORT:-5432}
else
    # Fallback a variables individuales
    DB_NAME=${DATABASE_NAME:-"stvaldivia"}
    DB_USER=${DATABASE_USER:-"stvaldivia"}
    DB_HOST=${DATABASE_HOST:-"localhost"}
    DB_PORT=${DATABASE_PORT:-5432}
    DB_PASS=${DATABASE_PASSWORD:-""}
fi

# Backup PostgreSQL
if command -v pg_dump &> /dev/null; then
    echo "Backup PostgreSQL..."
    if [ -n "$DB_PASS" ]; then
        export PGPASSWORD="$DB_PASS"
    fi
    # Intentar backup con usuario postgres primero (si tiene acceso)
    if [ -n "$DB_PASS" ]; then
        export PGPASSWORD="$DB_PASS"
    fi
    
    # Intentar con el usuario configurado primero
    pg_dump -h "${DB_HOST}" -p "${DB_PORT:-5432}" -U "${DB_USER}" -d "${DB_NAME}" -F c -f "${BACKUP_PATH}/database.dump" --no-owner --no-acl 2>&1 | grep -v "permission denied" | grep -v "LOCK TABLE" || true
    
    # Si falló, intentar con usuario postgres (requiere sudo)
    if [ ! -f "${BACKUP_PATH}/database.dump" ] || [ ! -s "${BACKUP_PATH}/database.dump" ]; then
        echo "Intentando backup con usuario postgres..."
        sudo -u postgres pg_dump -d "${DB_NAME}" -F c -f "${BACKUP_PATH}/database.dump" --no-owner --no-acl 2>&1 || echo "⚠️  Backup con postgres también falló"
    fi
    
    if [ -f "${BACKUP_PATH}/database.dump" ] && [ -s "${BACKUP_PATH}/database.dump" ]; then
        echo "✅ Backup PostgreSQL completado ($(du -h "${BACKUP_PATH}/database.dump" | cut -f1))"
    else
        echo "⚠️  Backup PostgreSQL falló - el archivo está vacío o no existe"
        echo "   Esto puede deberse a permisos insuficientes"
        echo "   Intenta ejecutar manualmente: sudo -u postgres pg_dump -d ${DB_NAME} > ${BACKUP_PATH}/database.sql"
    fi
# Backup MySQL/MariaDB
elif command -v mysqldump &> /dev/null; then
    echo "Backup MySQL/MariaDB..."
    mysqldump -h "${DB_HOST}" -u "${DB_USER}" -p"${DATABASE_PASSWORD:-}" "${DB_NAME}" > "${BACKUP_PATH}/database.sql"
    echo "✅ Backup MySQL completado"
else
    echo -e "${RED}⚠️  No se encontró pg_dump ni mysqldump${NC}"
fi

# ============================================================================
# 2. BACKUP DE ARCHIVOS DEL SITIO (sin venv y sin .git)
# ============================================================================
echo -e "${YELLOW}[2/5] Backup de archivos del sitio...${NC}"

cd "${SITE_PATH}"

# Crear tar.gz excluyendo venv, .git, node_modules, logs grandes, etc.
tar -czf "${BACKUP_PATH}/sitio.tar.gz" \
    --exclude='venv' \
    --exclude='.git' \
    --exclude='node_modules' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.env' \
    --exclude='logs/*.log' \
    --exclude='*.log' \
    --exclude='.DS_Store' \
    --exclude='*.swp' \
    --exclude='*.swo' \
    .

echo "✅ Backup de archivos completado"

# ============================================================================
# 3. BACKUP DE CONFIGURACIÓN DEL SERVIDOR
# ============================================================================
echo -e "${YELLOW}[3/5] Backup de configuración del servidor...${NC}"

# Backup de configuración de Nginx
if [ -f "/etc/nginx/sites-available/stvaldivia" ]; then
    cp /etc/nginx/sites-available/stvaldivia "${BACKUP_PATH}/nginx_stvaldivia.conf"
fi

# Backup de configuración de Systemd
if [ -f "/etc/systemd/system/stvaldivia.service" ]; then
    cp /etc/systemd/system/stvaldivia.service "${BACKUP_PATH}/stvaldivia.service"
fi

# Backup de configuración de Systemd override
if [ -d "/etc/systemd/system/stvaldivia.service.d" ]; then
    cp -r /etc/systemd/system/stvaldivia.service.d "${BACKUP_PATH}/"
fi

echo "✅ Backup de configuración completado"

# ============================================================================
# 4. BACKUP DE VARIABLES DE ENTORNO (sin contraseñas)
# ============================================================================
echo -e "${YELLOW}[4/5] Backup de variables de entorno (seguro)...${NC}"

if [ -f "${SITE_PATH}/.env" ]; then
    # Copiar .env pero ocultar valores sensibles
    sed 's/=.*/=***HIDDEN***/g' "${SITE_PATH}/.env" > "${BACKUP_PATH}/.env.example"
    echo "✅ Backup de .env (valores ocultos) completado"
fi

# ============================================================================
# 5. INFORMACIÓN DEL SISTEMA
# ============================================================================
echo -e "${YELLOW}[5/5] Generando información del sistema...${NC}"

cat > "${BACKUP_PATH}/system_info.txt" << EOF
BACKUP INFORMATION
==================
Fecha: $(date)
Hostname: $(hostname)
Sistema Operativo: $(lsb_release -d 2>/dev/null | cut -f2 || uname -a)
Versión Python: $(python3 --version 2>/dev/null || echo "N/A")
Versión Git: $(git --version 2>/dev/null || echo "N/A")
Ruta del sitio: ${SITE_PATH}
Directorio de backup: ${BACKUP_PATH}

SERVICIOS
=========
$(systemctl list-units --type=service --state=running | grep -E "(nginx|stvaldivia|postgres|mysql|mariadb)" || echo "No se encontraron servicios relevantes")

DISCO
=====
$(df -h /)

MEMORIA
=======
$(free -h)

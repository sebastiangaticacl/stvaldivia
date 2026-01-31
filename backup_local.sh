#!/bin/bash
# ============================================================================
# Script de Backup Local del Proyecto StValdivia
# ============================================================================

set -eo pipefail

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Obtener directorio del script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${SCRIPT_DIR}"
BACKUP_DIR="${PROJECT_DIR}/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_NAME="backup_local_${TIMESTAMP}"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_NAME}"

# Crear directorio de backup
mkdir -p "${BACKUP_PATH}"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}BACKUP LOCAL DEL PROYECTO STVALDIVIA${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Fecha: $(date)"
echo "Directorio del proyecto: ${PROJECT_DIR}"
echo "Directorio de backup: ${BACKUP_PATH}"
echo ""

# ============================================================================
# 1. BACKUP DE BASE DE DATOS
# ============================================================================
echo -e "${YELLOW}[1/4] Backup de base de datos...${NC}"

# Buscar base de datos SQLite local
DB_LOCAL_PATH="${PROJECT_DIR}/instance/bimba.db"
if [ -f "${DB_LOCAL_PATH}" ]; then
    echo "Encontrada base de datos SQLite local: ${DB_LOCAL_PATH}"
    cp "${DB_LOCAL_PATH}" "${BACKUP_PATH}/bimba.db"
    echo "✅ Backup SQLite completado ($(du -h "${BACKUP_PATH}/bimba.db" | cut -f1))"
else
    echo -e "${BLUE}ℹ️  No se encontró base de datos SQLite local${NC}"
    echo "   Buscando en otras ubicaciones..."
    
    # Buscar en otras ubicaciones comunes
    for db_path in "${PROJECT_DIR}/bimba.db" "/tmp/bimba.db"; do
        if [ -f "${db_path}" ]; then
            echo "Encontrada: ${db_path}"
            cp "${db_path}" "${BACKUP_PATH}/bimba.db"
            echo "✅ Backup SQLite completado"
            break
        fi
    done
fi

# Intentar backup de PostgreSQL si hay DATABASE_URL
if [ -f "${PROJECT_DIR}/.env" ]; then
    set +e
    source "${PROJECT_DIR}/.env" 2>/dev/null
    set -e
    
    if [ -n "$DATABASE_URL" ] && command -v pg_dump &> /dev/null; then
        echo "Intentando backup de PostgreSQL..."
        
        # Parsear DATABASE_URL
        DB_STRING=$(echo "$DATABASE_URL" | sed -e 's|postgresql://||' -e 's|postgres://||')
        DB_USER=$(echo "$DB_STRING" | cut -d: -f1)
        DB_PASS=$(echo "$DB_STRING" | cut -d: -f2 | cut -d@ -f1)
        DB_HOST_PORT=$(echo "$DB_STRING" | cut -d@ -f2 | cut -d/ -f1)
        DB_HOST=$(echo "$DB_HOST_PORT" | cut -d: -f1)
        DB_PORT=$(echo "$DB_HOST_PORT" | cut -d: -f2)
        DB_NAME=$(echo "$DB_STRING" | cut -d/ -f2 | cut -d? -f1)
        DB_PORT=${DB_PORT:-5432}
        
        if [ -n "$DB_PASS" ]; then
            export PGPASSWORD="$DB_PASS"
        fi
        
        pg_dump -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" \
            -F c -f "${BACKUP_PATH}/database_postgres.dump" \
            --no-owner --no-acl 2>&1 | grep -v "permission denied" || true
        
        if [ -f "${BACKUP_PATH}/database_postgres.dump" ] && [ -s "${BACKUP_PATH}/database_postgres.dump" ]; then
            echo "✅ Backup PostgreSQL completado ($(du -h "${BACKUP_PATH}/database_postgres.dump" | cut -f1))"
        else
            echo -e "${BLUE}ℹ️  Backup PostgreSQL no disponible o falló${NC}"
            rm -f "${BACKUP_PATH}/database_postgres.dump"
        fi
        
        unset PGPASSWORD
    fi
fi

# ============================================================================
# 2. BACKUP DE ARCHIVOS DEL PROYECTO
# ============================================================================
echo -e "${YELLOW}[2/4] Backup de archivos del proyecto...${NC}"

cd "${PROJECT_DIR}"

# Crear tar.gz excluyendo archivos innecesarios
tar -czf "${BACKUP_PATH}/proyecto.tar.gz" \
    --exclude='venv' \
    --exclude='.git' \
    --exclude='node_modules' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.env' \
    --exclude='instance' \
    --exclude='backups' \
    --exclude='*.log' \
    --exclude='.DS_Store' \
    --exclude='*.swp' \
    --exclude='*.swo' \
    --exclude='.pytest_cache' \
    --exclude='*.db' \
    --exclude='*.sqlite' \
    --exclude='*.sqlite3' \
    .

echo "✅ Backup de archivos completado ($(du -h "${BACKUP_PATH}/proyecto.tar.gz" | cut -f1))"

# ============================================================================
# 3. BACKUP DE CONFIGURACIÓN (sin contraseñas)
# ============================================================================
echo -e "${YELLOW}[3/4] Backup de configuración (seguro)...${NC}"

# Backup de .env (valores ocultos)
if [ -f "${PROJECT_DIR}/.env" ]; then
    sed 's/=.*/=***HIDDEN***/g' "${PROJECT_DIR}/.env" > "${BACKUP_PATH}/.env.example"
    echo "✅ Backup de .env (valores ocultos) completado"
fi

# Backup de requirements.txt
if [ -f "${PROJECT_DIR}/requirements.txt" ]; then
    cp "${PROJECT_DIR}/requirements.txt" "${BACKUP_PATH}/requirements.txt"
    echo "✅ Backup de requirements.txt completado"
fi

# ============================================================================
# 4. INFORMACIÓN DEL SISTEMA Y PROYECTO
# ============================================================================
echo -e "${YELLOW}[4/4] Generando información del sistema...${NC}"

cat > "${BACKUP_PATH}/backup_info.txt" << EOF
BACKUP LOCAL - INFORMACIÓN
==========================
Fecha: $(date)
Hostname: $(hostname)
Sistema Operativo: $(uname -a)
Versión Python: $(python3 --version 2>/dev/null || echo "N/A")
Versión Git: $(git --version 2>/dev/null || echo "N/A")
Ruta del proyecto: ${PROJECT_DIR}
Directorio de backup: ${BACKUP_PATH}

CONTENIDO DEL BACKUP
=====================
- proyecto.tar.gz: Archivos del proyecto (sin venv, .git, logs)
- bimba.db: Base de datos SQLite local (si existe)
- database_postgres.dump: Backup PostgreSQL (si está configurado)
- .env.example: Variables de entorno (valores ocultos)
- requirements.txt: Dependencias Python
- backup_info.txt: Este archivo

ESTADO DEL PROYECTO
===================
$(if [ -d "${PROJECT_DIR}/.git" ]; then
    echo "Git branch: $(git -C "${PROJECT_DIR}" branch --show-current 2>/dev/null || echo "N/A")"
    echo "Git commit: $(git -C "${PROJECT_DIR}" rev-parse --short HEAD 2>/dev/null || echo "N/A")"
    echo "Git status:"
    git -C "${PROJECT_DIR}" status --short 2>/dev/null || echo "N/A"
else
    echo "No es un repositorio Git"
fi)

DISCO
=====
$(df -h . 2>/dev/null || echo "N/A")

MEMORIA
=======
$(free -h 2>/dev/null || echo "N/A (sistema no compatible)")
EOF

echo "✅ Información del sistema generada"

# ============================================================================
# RESUMEN
# ============================================================================
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}BACKUP COMPLETADO${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Ubicación: ${BACKUP_PATH}"
echo ""
echo "Contenido:"
ls -lh "${BACKUP_PATH}" | tail -n +2 | awk '{print "  " $9 " (" $5 ")"}'
echo ""
echo -e "${BLUE}Para restaurar:${NC}"
echo "  1. Descomprimir: tar -xzf ${BACKUP_PATH}/proyecto.tar.gz"
echo "  2. Restaurar BD: cp ${BACKUP_PATH}/bimba.db instance/bimba.db"
echo ""

# Crear enlace simbólico al último backup
ln -sfn "${BACKUP_NAME}" "${BACKUP_DIR}/latest"
echo -e "${GREEN}✅ Enlace 'latest' creado: ${BACKUP_DIR}/latest${NC}"
echo ""



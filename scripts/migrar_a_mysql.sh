#!/bin/bash
# ============================================================================
# Script Maestro de Migración: PostgreSQL → MySQL
# ============================================================================

set -euo pipefail

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MIGRATIONS_DIR="${PROJECT_ROOT}/migrations"
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')

# Cargar .env si existe
if [ -f "${PROJECT_ROOT}/.env" ]; then
    set -a
    source "${PROJECT_ROOT}/.env"
    set +a
fi

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}MIGRACIÓN A MYSQL${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Fecha: $(date)"
echo "Directorio: ${PROJECT_ROOT}"
echo ""

# ============================================================================
# VERIFICACIONES PREVIAS
# ============================================================================

echo -e "${YELLOW}[1/6] Verificando requisitos previos...${NC}"

# Verificar que estamos en el directorio correcto
if [ ! -f "${PROJECT_ROOT}/app/__init__.py" ]; then
    echo -e "${RED}❌ Error: No se encontró app/__init__.py${NC}"
    echo "   Ejecutar desde el directorio raíz del proyecto"
    exit 1
fi

# Verificar que MySQL está disponible
if ! command -v mysql >/dev/null 2>&1; then
    echo -e "${RED}❌ Error: mysql client no encontrado${NC}"
    echo "   Instalar: sudo apt-get install mysql-client"
    exit 1
fi

# Verificar DATABASE_URL
if [ -z "${DATABASE_URL:-}" ]; then
    echo -e "${YELLOW}⚠️  DATABASE_URL no configurado${NC}"
    echo "   Configurar: export DATABASE_URL='mysql://user:pass@host:port/dbname'"
    read -p "¿Continuar de todas formas? (s/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Ss]$ ]]; then
        exit 1
    fi
else
    if [[ ! "$DATABASE_URL" =~ ^mysql ]]; then
        echo -e "${RED}❌ Error: DATABASE_URL no es MySQL${NC}"
        echo "   Actual: ${DATABASE_URL:0:50}..."
        exit 1
    fi
    echo -e "${GREEN}✅ DATABASE_URL configurado (MySQL)${NC}"
fi

# Verificar migraciones MySQL
MYSQL_MIGRATIONS=$(find "${MIGRATIONS_DIR}" -name "*_mysql.sql" | wc -l)
if [ "$MYSQL_MIGRATIONS" -eq 0 ]; then
    echo -e "${RED}❌ Error: No se encontraron migraciones MySQL${NC}"
    exit 1
fi
echo -e "${GREEN}✅ ${MYSQL_MIGRATIONS} migraciones MySQL encontradas${NC}"

echo ""

# ============================================================================
# BACKUP
# ============================================================================

echo -e "${YELLOW}[2/6] Creando backup...${NC}"

BACKUP_DIR="${PROJECT_ROOT}/backups"
mkdir -p "${BACKUP_DIR}"

# Intentar backup de MySQL si DATABASE_URL está configurado
if [ -n "${DATABASE_URL:-}" ]; then
    # Parsear DATABASE_URL (soporta mysql:// y mysql+mysqlconnector://)
    DB_INFO=$(python3 << 'PYEOF'
import re
import os
import sys

db_url = os.environ.get('DATABASE_URL', '')
# Remover prefijo mysql+mysqlconnector:// o mysql://
db_url_clean = re.sub(r'^mysql(\+[^:]+)?://', 'mysql://', db_url)
match = re.match(r'mysql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', db_url_clean)

if match:
    user, password, host, port, dbname = match.groups()
    print(f"{user}|{password}|{host}|{port}|{dbname}")
else:
    sys.exit(1)
PYEOF
)
    
    if [ $? -eq 0 ]; then
        IFS='|' read -r DB_USER DB_PASS DB_HOST DB_PORT DB_NAME <<< "$DB_INFO"
        BACKUP_FILE="${BACKUP_DIR}/backup_mysql_${TIMESTAMP}.sql"
        
        echo "   Creando backup de MySQL..."
        MYSQL_PWD="${DB_PASS}" mysqldump -h "${DB_HOST}" -P "${DB_PORT}" -u "${DB_USER}" "${DB_NAME}" > "${BACKUP_FILE}" 2>&1
        
        if [ $? -eq 0 ]; then
            BACKUP_SIZE=$(du -h "${BACKUP_FILE}" | cut -f1)
            echo -e "${GREEN}✅ Backup creado: ${BACKUP_FILE} (${BACKUP_SIZE})${NC}"
        else
            echo -e "${YELLOW}⚠️  No se pudo crear backup automático${NC}"
            echo "   Continuar manualmente: mysqldump -u user -p database > backup.sql"
        fi
    fi
else
    echo -e "${YELLOW}⚠️  DATABASE_URL no configurado, saltando backup automático${NC}"
    echo "   Crear backup manualmente antes de continuar"
fi

echo ""

# ============================================================================
# CONFIRMACIÓN
# ============================================================================

echo -e "${YELLOW}[3/6] Confirmación${NC}"
echo ""
echo "⚠️  ADVERTENCIA: Este script aplicará migraciones MySQL a la base de datos."
echo ""
echo "Migraciones a aplicar:"
find "${MIGRATIONS_DIR}" -name "*_mysql.sql" | sort | sed 's/^/   - /'
echo ""
# Permitir ejecución no interactiva con variable de entorno
if [ "${MIGRATE_AUTO:-}" = "yes" ]; then
    echo "Ejecutando automáticamente (MIGRATE_AUTO=yes)"
else
    read -p "¿Continuar con la migración? (s/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Ss]$ ]]; then
        echo "Migración cancelada"
        exit 0
    fi
fi

echo ""

# ============================================================================
# APLICAR MIGRACIONES
# ============================================================================

echo -e "${YELLOW}[4/6] Aplicando migraciones MySQL...${NC}"

if [ -z "${DATABASE_URL:-}" ]; then
    echo -e "${RED}❌ Error: DATABASE_URL no configurado${NC}"
    exit 1
fi

# Parsear DATABASE_URL
DB_INFO=$(python3 << 'PYEOF'
import re
import os
import sys

db_url = os.environ.get('DATABASE_URL', '')
match = re.match(r'mysql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', db_url)

if match:
    user, password, host, port, dbname = match.groups()
    print(f"{user}|{password}|{host}|{port}|{dbname}")
else:
    sys.exit(1)
PYEOF
)

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Error al parsear DATABASE_URL${NC}"
    exit 1
fi

IFS='|' read -r DB_USER DB_PASS DB_HOST DB_PORT DB_NAME <<< "$DB_INFO"

# Aplicar migraciones en orden
MIGRATION_COUNT=0
MIGRATION_ERRORS=0

for migration in $(find "${MIGRATIONS_DIR}" -name "*_mysql.sql" | sort); do
    MIGRATION_NAME=$(basename "$migration")
    echo -n "   Aplicando ${MIGRATION_NAME}... "
    
    if MYSQL_PWD="${DB_PASS}" mysql -h "${DB_HOST}" -P "${DB_PORT}" -u "${DB_USER}" "${DB_NAME}" < "$migration" 2>&1; then
        echo -e "${GREEN}✅${NC}"
        ((MIGRATION_COUNT++))
    else
        echo -e "${RED}❌${NC}"
        ((MIGRATION_ERRORS++))
        echo -e "${RED}   Error al aplicar ${MIGRATION_NAME}${NC}"
    fi
done

echo ""

if [ $MIGRATION_ERRORS -gt 0 ]; then
    echo -e "${RED}❌ ${MIGRATION_ERRORS} migraciones fallaron${NC}"
    echo -e "${YELLOW}⚠️  Revisar errores y considerar rollback${NC}"
    exit 1
fi

echo -e "${GREEN}✅ ${MIGRATION_COUNT} migraciones aplicadas exitosamente${NC}"
echo ""

# ============================================================================
# VERIFICACIÓN
# ============================================================================

echo -e "${YELLOW}[5/6] Verificando migraciones...${NC}"

# Verificar tablas creadas
REQUIRED_TABLES=("payment_intents" "payment_agents")
MISSING_TABLES=()

for table in "${REQUIRED_TABLES[@]}"; do
    TABLE_EXISTS=$(MYSQL_PWD="${DB_PASS}" mysql -h "${DB_HOST}" -P "${DB_PORT}" -u "${DB_USER}" "${DB_NAME}" -sN -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='${DB_NAME}' AND table_name='${table}';" 2>/dev/null || echo "0")
    
    if [ "$TABLE_EXISTS" -eq 1 ]; then
        echo -e "${GREEN}✅ Tabla ${table} existe${NC}"
    else
        echo -e "${RED}❌ Tabla ${table} NO existe${NC}"
        MISSING_TABLES+=("$table")
    fi
done

if [ ${#MISSING_TABLES[@]} -gt 0 ]; then
    echo -e "${RED}❌ Faltan tablas: ${MISSING_TABLES[*]}${NC}"
    exit 1
fi

echo ""

# ============================================================================
# RESUMEN
# ============================================================================

echo -e "${YELLOW}[6/6] Resumen${NC}"
echo ""
echo -e "${GREEN}✅ Migración completada${NC}"
echo ""
echo "Detalles:"
echo "  - Migraciones aplicadas: ${MIGRATION_COUNT}"
echo "  - Base de datos: ${DB_NAME}"
echo "  - Host: ${DB_HOST}:${DB_PORT}"
echo "  - Backup: ${BACKUP_FILE:-No disponible}"
echo ""
echo -e "${BLUE}Próximos pasos:${NC}"
echo "  1. Probar aplicación: python3 run_local.py"
echo "  2. Verificar endpoints críticos"
echo "  3. Validar queries complejas"
echo ""


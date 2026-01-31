#!/bin/bash
# ============================================================================
# Script de Verificación de Preparación para Migración MySQL
# ============================================================================

set -euo pipefail

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}VERIFICACIÓN DE PREPARACIÓN MYSQL${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

ERRORS=0
WARNINGS=0

# ============================================================================
# 1. VERIFICAR MYSQL CLIENT
# ============================================================================

echo -e "${YELLOW}[1/6] Verificando MySQL client...${NC}"

if command -v mysql >/dev/null 2>&1; then
    MYSQL_VERSION=$(mysql --version 2>&1 | head -1)
    echo -e "${GREEN}✅ MySQL client encontrado: ${MYSQL_VERSION}${NC}"
else
    echo -e "${RED}❌ MySQL client no encontrado${NC}"
    echo "   Instalar:"
    echo "     Ubuntu/Debian: sudo apt-get install mysql-client"
    echo "     macOS: brew install mysql-client"
    ((ERRORS++))
fi

echo ""

# ============================================================================
# 2. VERIFICAR DATABASE_URL
# ============================================================================

echo -e "${YELLOW}[2/6] Verificando DATABASE_URL...${NC}"

# Cargar .env si existe
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

if [ -z "${DATABASE_URL:-}" ]; then
    echo -e "${RED}❌ DATABASE_URL no configurado${NC}"
    echo ""
    echo "   Configurar en .env o export:"
    echo "   export DATABASE_URL='mysql://usuario:password@localhost:3306/bimba_db'"
    ((ERRORS++))
else
    if [[ "$DATABASE_URL" =~ ^mysql:// ]]; then
        DB_SANITIZED=$(echo "$DATABASE_URL" | sed -E 's#(mysql://[^:]+):[^@]+@#\1:***@#')
        echo -e "${GREEN}✅ DATABASE_URL configurado: ${DB_SANITIZED}${NC}"
        
        # Intentar parsear
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
        
        if [ $? -eq 0 ]; then
            IFS='|' read -r DB_USER DB_PASS DB_HOST DB_PORT DB_NAME <<< "$DB_INFO"
            echo "   Usuario: ${DB_USER}"
            echo "   Host: ${DB_HOST}:${DB_PORT}"
            echo "   Base de datos: ${DB_NAME}"
        fi
    else
        echo -e "${RED}❌ DATABASE_URL no es MySQL${NC}"
        echo "   Actual: ${DATABASE_URL:0:50}..."
        echo "   Debe comenzar con: mysql://"
        ((ERRORS++))
    fi
fi

echo ""

# ============================================================================
# 3. VERIFICAR CONECTIVIDAD MYSQL
# ============================================================================

echo -e "${YELLOW}[3/6] Verificando conectividad MySQL...${NC}"

if [ -n "${DATABASE_URL:-}" ] && [[ "$DATABASE_URL" =~ ^mysql:// ]]; then
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
    
    if [ $? -eq 0 ]; then
        IFS='|' read -r DB_USER DB_PASS DB_HOST DB_PORT DB_NAME <<< "$DB_INFO"
        
        if MYSQL_PWD="${DB_PASS}" mysql -h "${DB_HOST}" -P "${DB_PORT}" -u "${DB_USER}" -e "SELECT 1;" >/dev/null 2>&1; then
            echo -e "${GREEN}✅ Conexión a MySQL exitosa${NC}"
            
            # Verificar que la base de datos existe
            DB_EXISTS=$(MYSQL_PWD="${DB_PASS}" mysql -h "${DB_HOST}" -P "${DB_PORT}" -u "${DB_USER}" -sN -e "SELECT COUNT(*) FROM information_schema.schemata WHERE schema_name='${DB_NAME}';" 2>/dev/null || echo "0")
            
            if [ "$DB_EXISTS" -eq 1 ]; then
                echo -e "${GREEN}✅ Base de datos '${DB_NAME}' existe${NC}"
            else
                echo -e "${YELLOW}⚠️  Base de datos '${DB_NAME}' NO existe${NC}"
                echo "   Crear con: CREATE DATABASE ${DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
                ((WARNINGS++))
            fi
        else
            echo -e "${RED}❌ No se puede conectar a MySQL${NC}"
            echo "   Verificar:"
            echo "     - Servicio MySQL corriendo"
            echo "     - Credenciales correctas"
            echo "     - Acceso de red"
            ((ERRORS++))
        fi
    fi
else
    echo -e "${YELLOW}⚠️  No se puede verificar (DATABASE_URL no configurado o no es MySQL)${NC}"
    ((WARNINGS++))
fi

echo ""

# ============================================================================
# 4. VERIFICAR DEPENDENCIAS PYTHON
# ============================================================================

echo -e "${YELLOW}[4/6] Verificando dependencias Python...${NC}"

if python3 -c "import mysql.connector" 2>/dev/null; then
    echo -e "${GREEN}✅ mysql-connector-python instalado${NC}"
else
    echo -e "${RED}❌ mysql-connector-python NO instalado${NC}"
    echo "   Instalar: pip install mysql-connector-python"
    ((ERRORS++))
fi

if python3 -c "import sqlalchemy" 2>/dev/null; then
    SQLALCHEMY_VERSION=$(python3 -c "import sqlalchemy; print(sqlalchemy.__version__)" 2>/dev/null)
    echo -e "${GREEN}✅ SQLAlchemy instalado: ${SQLALCHEMY_VERSION}${NC}"
else
    echo -e "${RED}❌ SQLAlchemy NO instalado${NC}"
    ((ERRORS++))
fi

echo ""

# ============================================================================
# 5. VERIFICAR MIGRACIONES
# ============================================================================

echo -e "${YELLOW}[5/6] Verificando migraciones MySQL...${NC}"

MIGRATIONS_DIR="migrations"
MYSQL_MIGRATIONS=$(find "${MIGRATIONS_DIR}" -name "*_mysql.sql" 2>/dev/null | wc -l | tr -d ' ')

if [ "$MYSQL_MIGRATIONS" -gt 0 ]; then
    echo -e "${GREEN}✅ ${MYSQL_MIGRATIONS} migraciones MySQL encontradas${NC}"
    echo "   Migraciones:"
    find "${MIGRATIONS_DIR}" -name "*_mysql.sql" 2>/dev/null | sort | sed 's/^/     - /'
else
    echo -e "${RED}❌ No se encontraron migraciones MySQL${NC}"
    ((ERRORS++))
fi

echo ""

# ============================================================================
# 6. VERIFICAR SCRIPTS
# ============================================================================

echo -e "${YELLOW}[6/6] Verificando scripts de migración...${NC}"

if [ -f "scripts/migrar_a_mysql.sh" ]; then
    if [ -x "scripts/migrar_a_mysql.sh" ]; then
        echo -e "${GREEN}✅ scripts/migrar_a_mysql.sh existe y es ejecutable${NC}"
    else
        echo -e "${YELLOW}⚠️  scripts/migrar_a_mysql.sh existe pero no es ejecutable${NC}"
        echo "   Ejecutar: chmod +x scripts/migrar_a_mysql.sh"
        ((WARNINGS++))
    fi
else
    echo -e "${RED}❌ scripts/migrar_a_mysql.sh NO existe${NC}"
    ((ERRORS++))
fi

if [ -f "scripts/validar_migracion_mysql.sh" ]; then
    if [ -x "scripts/validar_migracion_mysql.sh" ]; then
        echo -e "${GREEN}✅ scripts/validar_migracion_mysql.sh existe y es ejecutable${NC}"
    else
        echo -e "${YELLOW}⚠️  scripts/validar_migracion_mysql.sh existe pero no es ejecutable${NC}"
        echo "   Ejecutar: chmod +x scripts/validar_migracion_mysql.sh"
        ((WARNINGS++))
    fi
else
    echo -e "${RED}❌ scripts/validar_migracion_mysql.sh NO existe${NC}"
    ((ERRORS++))
fi

echo ""

# ============================================================================
# RESUMEN
# ============================================================================

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}RESUMEN${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}✅ Todo está listo para migrar${NC}"
    echo ""
    echo "Próximo paso:"
    echo "  ./scripts/migrar_a_mysql.sh"
    exit 0
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}⚠️  Listo con advertencias (${WARNINGS})${NC}"
    echo ""
    echo "Puedes proceder, pero revisa las advertencias arriba."
    echo ""
    echo "Próximo paso:"
    echo "  ./scripts/migrar_a_mysql.sh"
    exit 0
else
    echo -e "${RED}❌ Hay ${ERRORS} error(es) que deben corregirse${NC}"
    if [ $WARNINGS -gt 0 ]; then
        echo -e "${YELLOW}   y ${WARNINGS} advertencia(s)${NC}"
    fi
    echo ""
    echo "Revisa los errores arriba antes de continuar."
    exit 1
fi


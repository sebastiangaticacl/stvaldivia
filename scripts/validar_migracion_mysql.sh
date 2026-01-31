#!/bin/bash
# ============================================================================
# Script de Validación Post-Migración MySQL
# ============================================================================

set -euo pipefail

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}VALIDACIÓN POST-MIGRACIÓN MYSQL${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Verificar DATABASE_URL
if [ -z "${DATABASE_URL:-}" ]; then
    echo -e "${RED}❌ Error: DATABASE_URL no configurado${NC}"
    exit 1
fi

if [[ ! "$DATABASE_URL" =~ ^mysql ]]; then
    echo -e "${RED}❌ Error: DATABASE_URL no es MySQL${NC}"
    exit 1
fi

# Parsear DATABASE_URL
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

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Error al parsear DATABASE_URL${NC}"
    exit 1
fi

IFS='|' read -r DB_USER DB_PASS DB_HOST DB_PORT DB_NAME <<< "$DB_INFO"

echo "Base de datos: ${DB_NAME}"
echo "Host: ${DB_HOST}:${DB_PORT}"
echo ""

# ============================================================================
# VERIFICAR TABLAS
# ============================================================================

echo -e "${YELLOW}[1/4] Verificando tablas...${NC}"

REQUIRED_TABLES=("payment_intents" "payment_agents" "pos_registers" "pos_sales" "register_sessions" "products")
MISSING_TABLES=()
EXISTING_TABLES=()

for table in "${REQUIRED_TABLES[@]}"; do
    TABLE_EXISTS=$(MYSQL_PWD="${DB_PASS}" mysql -h "${DB_HOST}" -P "${DB_PORT}" -u "${DB_USER}" "${DB_NAME}" -sN -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='${DB_NAME}' AND table_name='${table}';" 2>/dev/null || echo "0")
    
    if [ "$TABLE_EXISTS" -eq 1 ]; then
        echo -e "${GREEN}✅ ${table}${NC}"
        EXISTING_TABLES+=("$table")
    else
        echo -e "${RED}❌ ${table} NO existe${NC}"
        MISSING_TABLES+=("$table")
    fi
done

echo ""

if [ ${#MISSING_TABLES[@]} -gt 0 ]; then
    echo -e "${RED}❌ Faltan ${#MISSING_TABLES[@]} tablas${NC}"
else
    echo -e "${GREEN}✅ Todas las tablas existen${NC}"
fi

echo ""

# ============================================================================
# VERIFICAR COLUMNAS CRÍTICAS
# ============================================================================

echo -e "${YELLOW}[2/4] Verificando columnas críticas...${NC}"

# payment_intents.id debe ser CHAR(36)
PAYMENT_INTENTS_ID_TYPE=$(MYSQL_PWD="${DB_PASS}" mysql -h "${DB_HOST}" -P "${DB_PORT}" -u "${DB_USER}" "${DB_NAME}" -sN -e "SELECT data_type FROM information_schema.columns WHERE table_schema='${DB_NAME}' AND table_name='payment_intents' AND column_name='id';" 2>/dev/null || echo "")

if [ "$PAYMENT_INTENTS_ID_TYPE" = "char" ] || [ "$PAYMENT_INTENTS_ID_TYPE" = "varchar" ]; then
    echo -e "${GREEN}✅ payment_intents.id es CHAR/VARCHAR (correcto para MySQL)${NC}"
else
    echo -e "${RED}❌ payment_intents.id es ${PAYMENT_INTENTS_ID_TYPE} (debería ser CHAR/VARCHAR)${NC}"
fi

# payment_agents.id debe ser CHAR(36)
PAYMENT_AGENTS_ID_TYPE=$(MYSQL_PWD="${DB_PASS}" mysql -h "${DB_HOST}" -P "${DB_PORT}" -u "${DB_USER}" "${DB_NAME}" -sN -e "SELECT data_type FROM information_schema.columns WHERE table_schema='${DB_NAME}' AND table_name='payment_agents' AND column_name='id';" 2>/dev/null || echo "")

if [ "$PAYMENT_AGENTS_ID_TYPE" = "char" ] || [ "$PAYMENT_AGENTS_ID_TYPE" = "varchar" ]; then
    echo -e "${GREEN}✅ payment_agents.id es CHAR/VARCHAR (correcto para MySQL)${NC}"
else
    echo -e "${RED}❌ payment_agents.id es ${PAYMENT_AGENTS_ID_TYPE} (debería ser CHAR/VARCHAR)${NC}"
fi

# pos_registers.is_test debe existir
IS_TEST_EXISTS=$(MYSQL_PWD="${DB_PASS}" mysql -h "${DB_HOST}" -P "${DB_PORT}" -u "${DB_USER}" "${DB_NAME}" -sN -e "SELECT COUNT(*) FROM information_schema.columns WHERE table_schema='${DB_NAME}' AND table_name='pos_registers' AND column_name='is_test';" 2>/dev/null || echo "0")

if [ "$IS_TEST_EXISTS" -eq 1 ]; then
    echo -e "${GREEN}✅ pos_registers.is_test existe${NC}"
else
    echo -e "${RED}❌ pos_registers.is_test NO existe${NC}"
fi

# products.is_test debe existir
PRODUCTS_IS_TEST_EXISTS=$(MYSQL_PWD="${DB_PASS}" mysql -h "${DB_HOST}" -P "${DB_PORT}" -u "${DB_USER}" "${DB_NAME}" -sN -e "SELECT COUNT(*) FROM information_schema.columns WHERE table_schema='${DB_NAME}' AND table_name='products' AND column_name='is_test';" 2>/dev/null || echo "0")

if [ "$PRODUCTS_IS_TEST_EXISTS" -eq 1 ]; then
    echo -e "${GREEN}✅ products.is_test existe${NC}"
else
    echo -e "${RED}❌ products.is_test NO existe${NC}"
fi

echo ""

# ============================================================================
# VERIFICAR ÍNDICES
# ============================================================================

echo -e "${YELLOW}[3/4] Verificando índices críticos...${NC}"

REQUIRED_INDEXES=(
    "payment_intents.idx_payment_intents_status"
    "payment_intents.idx_payment_intents_register"
    "payment_agents.idx_payment_agents_register_id"
    "pos_registers.idx_pos_registers_is_test"
)

MISSING_INDEXES=()

for index in "${REQUIRED_INDEXES[@]}"; do
    TABLE_NAME=$(echo "$index" | cut -d'.' -f1)
    INDEX_NAME=$(echo "$index" | cut -d'.' -f2)
    
    INDEX_EXISTS=$(MYSQL_PWD="${DB_PASS}" mysql -h "${DB_HOST}" -P "${DB_PORT}" -u "${DB_USER}" "${DB_NAME}" -sN -e "SELECT COUNT(*) FROM information_schema.statistics WHERE table_schema='${DB_NAME}' AND table_name='${TABLE_NAME}' AND index_name='${INDEX_NAME}';" 2>/dev/null || echo "0")
    
    if [ "$INDEX_EXISTS" -eq 1 ]; then
        echo -e "${GREEN}✅ ${index}${NC}"
    else
        echo -e "${RED}❌ ${index} NO existe${NC}"
        MISSING_INDEXES+=("$index")
    fi
done

echo ""

# ============================================================================
# VERIFICAR CONECTIVIDAD PYTHON
# ============================================================================

echo -e "${YELLOW}[4/4] Verificando conectividad desde Python...${NC}"

python3 << PYEOF
import os
import sys

try:
    from app import create_app
    app = create_app()
    
    with app.app_context():
        from app.models import db
        
        # Intentar conectar
        db.engine.connect()
        print("✅ Conexión a MySQL exitosa desde Python")
        
        # Verificar tipo de BD
        db_url = app.config.get('SQLALCHEMY_DATABASE_URI', '')
        if 'mysql' in db_url:
            print("✅ DATABASE_URL configurado para MySQL")
        else:
            print(f"⚠️  DATABASE_URL no es MySQL: {db_url[:50]}...")
            
except Exception as e:
    print(f"❌ Error de conexión: {e}")
    sys.exit(1)
PYEOF

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Validación Python completada${NC}"
else
    echo -e "${RED}❌ Error en validación Python${NC}"
fi

echo ""

# ============================================================================
# RESUMEN
# ============================================================================

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}RESUMEN DE VALIDACIÓN${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

if [ ${#MISSING_TABLES[@]} -eq 0 ] && [ ${#MISSING_INDEXES[@]} -eq 0 ]; then
    echo -e "${GREEN}✅ Validación exitosa${NC}"
    echo ""
    echo "La migración a MySQL parece estar completa y correcta."
    echo ""
    echo "Próximos pasos:"
    echo "  1. Probar aplicación: python3 run_local.py"
    echo "  2. Verificar endpoints críticos"
    echo "  3. Ejecutar tests si existen"
    exit 0
else
    echo -e "${RED}❌ Validación falló${NC}"
    echo ""
    if [ ${#MISSING_TABLES[@]} -gt 0 ]; then
        echo "Faltan tablas: ${MISSING_TABLES[*]}"
    fi
    if [ ${#MISSING_INDEXES[@]} -gt 0 ]; then
        echo "Faltan índices: ${MISSING_INDEXES[*]}"
    fi
    echo ""
    echo "Revisar migraciones y aplicar las faltantes."
    exit 1
fi


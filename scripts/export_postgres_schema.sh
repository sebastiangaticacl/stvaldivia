#!/bin/bash
# ============================================================================
# Script para exportar esquema real de PostgreSQL
# Genera: dump schema-only, reportes de tablas, FKs e índices
# ============================================================================

set -euo pipefail

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuración
ENV_FILE="/var/www/stvaldivia/.env"
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DOCS_DIR="${PROJECT_ROOT}/docs"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}EXPORTACIÓN DE ESQUEMA POSTGRESQL${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# ============================================================================
# 1. DETECTAR CONFIGURACIÓN DE BD
# ============================================================================
echo -e "${YELLOW}[1/5] Detectando configuración de base de datos...${NC}"

if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}❌ Error: Archivo .env no encontrado en ${ENV_FILE}${NC}"
    echo ""
    echo "Ubicaciones alternativas a verificar:"
    echo "  - ~/.env"
    echo "  - ${PROJECT_ROOT}/.env"
    echo "  - Variables de entorno: DATABASE_URL"
    exit 1
fi

# Extraer DATABASE_URL
DATABASE_URL=$(grep "^DATABASE_URL=" "$ENV_FILE" | cut -d'=' -f2- | tr -d '"' | tr -d "'" | xargs)

if [ -z "$DATABASE_URL" ]; then
    echo -e "${RED}❌ Error: DATABASE_URL no encontrado en ${ENV_FILE}${NC}"
    exit 1
fi

echo -e "${GREEN}✅ DATABASE_URL encontrado${NC}"

# Parsear DATABASE_URL: postgresql://user:pass@host:port/dbname
# Usar Python para parsing seguro
DB_INFO=$(python3 << PYEOF
import re
import sys

db_url = "${DATABASE_URL}"
match = re.match(r'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', db_url)

if not match:
    # Intentar sin password
    match = re.match(r'postgresql://([^@]+)@([^:]+):(\d+)/(.+)', db_url)
    if match:
        user = match.group(1)
        password = ""
        host = match.group(2)
        port = match.group(3)
        dbname = match.group(4)
    else:
        print("ERROR: Formato no reconocido", file=sys.stderr)
        sys.exit(1)
else:
    user, password, host, port, dbname = match.groups()

print(f"{user}|{password}|{host}|{port}|{dbname}")
PYEOF
)

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Error al parsear DATABASE_URL${NC}"
    exit 1
fi

IFS='|' read -r DB_USER DB_PASS DB_HOST DB_PORT DB_NAME <<< "$DB_INFO"

echo "  Usuario: ${DB_USER}"
echo "  Host: ${DB_HOST}"
echo "  Puerto: ${DB_PORT}"
echo "  Base de datos: ${DB_NAME}"
echo ""

# ============================================================================
# 2. VERIFICAR CONECTIVIDAD
# ============================================================================
echo -e "${YELLOW}[2/5] Verificando conectividad a PostgreSQL...${NC}"

export PGPASSWORD="${DB_PASS}"
if psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT version();" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Conexión exitosa${NC}"
else
    echo -e "${RED}❌ Error: No se puede conectar a PostgreSQL${NC}"
    echo "Verificar:"
    echo "  - Servicio PostgreSQL corriendo"
    echo "  - Credenciales correctas"
    echo "  - Acceso de red"
    exit 1
fi
echo ""

# ============================================================================
# 3. GENERAR DUMP SCHEMA-ONLY
# ============================================================================
echo -e "${YELLOW}[3/5] Generando dump schema-only...${NC}"

SCHEMA_FILE="${DOCS_DIR}/SCHEMA_REAL.sql"
pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
    --schema-only \
    --no-owner \
    --no-privileges \
    --no-tablespaces \
    --no-security-labels \
    --no-comments \
    > "$SCHEMA_FILE" 2>&1

if [ $? -eq 0 ]; then
    SCHEMA_SIZE=$(du -h "$SCHEMA_FILE" | cut -f1)
    echo -e "${GREEN}✅ Dump generado: ${SCHEMA_FILE} (${SCHEMA_SIZE})${NC}"
else
    echo -e "${RED}❌ Error al generar dump${NC}"
    exit 1
fi
echo ""

# ============================================================================
# 4. GENERAR REPORTE DE TABLAS Y ROW COUNT
# ============================================================================
echo -e "${YELLOW}[4/5] Generando reporte de tablas y conteo de filas...${NC}"

TABLES_REPORT="${DOCS_DIR}/TABLES_ROWCOUNT.md"

psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -A -F'|' << 'SQL' > "${TABLES_REPORT}.tmp"
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
    (SELECT COUNT(*) FROM information_schema.tables t2 
     WHERE t2.table_schema = t.schemaname 
     AND t2.table_name = t.tablename) as exists_flag
FROM pg_tables t
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
SQL

# Agregar conteo de filas
echo "# Reporte de Tablas y Conteo de Filas" > "$TABLES_REPORT"
echo "" >> "$TABLES_REPORT"
echo "**Fecha:** $(date '+%Y-%m-%d %H:%M:%S')" >> "$TABLES_REPORT"
echo "**Base de datos:** ${DB_NAME}" >> "$TABLES_REPORT"
echo "**Host:** ${DB_HOST}:${DB_PORT}" >> "$TABLES_REPORT"
echo "" >> "$TABLES_REPORT"
echo "| Tabla | Tamaño | Filas |" >> "$TABLES_REPORT"
echo "|-------|--------|-------|" >> "$TABLES_REPORT"

while IFS='|' read -r schema table size exists; do
    if [ -n "$table" ]; then
        ROW_COUNT=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -A -c "SELECT COUNT(*) FROM \"$table\";" 2>/dev/null || echo "N/A")
        echo "| \`$table\` | $size | $ROW_COUNT |" >> "$TABLES_REPORT"
    fi
done < "${TABLES_REPORT}.tmp"

rm -f "${TABLES_REPORT}.tmp"
echo -e "${GREEN}✅ Reporte generado: ${TABLES_REPORT}${NC}"
echo ""

# ============================================================================
# 5. GENERAR REPORTE DE FOREIGN KEYS
# ============================================================================
echo -e "${YELLOW}[5/5] Generando reporte de Foreign Keys...${NC}"

FKS_REPORT="${DOCS_DIR}/FKS_REAL.md"

psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" << 'SQL' > "$FKS_REPORT"
\echo '# Foreign Keys Reales en Base de Datos'
\echo ''
\echo '**Fecha:** ' || CURRENT_TIMESTAMP
\echo ''
\echo '## Foreign Keys por Tabla'
\echo ''
\echo '| Tabla Origen | Columna | Tabla Destino | Columna Destino | Nombre Constraint | ON DELETE | ON UPDATE |'
\echo '|--------------|--------|---------------|----------------|-------------------|-----------|-----------|'

SELECT 
    tc.table_name as tabla_origen,
    kcu.column_name as columna,
    ccu.table_name AS tabla_destino,
    ccu.column_name AS columna_destino,
    tc.constraint_name as constraint_name,
    rc.delete_rule as on_delete,
    rc.update_rule as on_update
FROM information_schema.table_constraints AS tc 
JOIN information_schema.key_column_usage AS kcu
  ON tc.constraint_name = kcu.constraint_name
  AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage AS ccu
  ON ccu.constraint_name = tc.constraint_name
  AND ccu.table_schema = tc.table_schema
JOIN information_schema.referential_constraints AS rc
  ON rc.constraint_name = tc.constraint_name
  AND rc.constraint_schema = tc.table_schema
WHERE tc.constraint_type = 'FOREIGN KEY' 
  AND tc.table_schema = 'public'
ORDER BY tc.table_name, kcu.column_name;
SQL

echo -e "${GREEN}✅ Reporte generado: ${FKS_REPORT}${NC}"
echo ""

# ============================================================================
# 6. GENERAR REPORTE DE ÍNDICES
# ============================================================================
echo -e "${YELLOW}[6/5] Generando reporte de Índices...${NC}"

INDEXES_REPORT="${DOCS_DIR}/INDEXES_REAL.md"

psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" << 'SQL' > "$INDEXES_REPORT"
\echo '# Índices Reales en Base de Datos'
\echo ''
\echo '**Fecha:** ' || CURRENT_TIMESTAMP
\echo ''
\echo '## Índices por Tabla'
\echo ''

SELECT 
    tablename,
    indexname,
    indexdef,
    CASE 
        WHEN indexdef LIKE '%UNIQUE%' THEN 'Sí'
        ELSE 'No'
    END as es_unico
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename, indexname;
SQL

# Formatear mejor el reporte
python3 << PYEOF
import re

with open('${INDEXES_REPORT}', 'r') as f:
    content = f.read()

# Agregar formato markdown
lines = content.split('\n')
output = []
current_table = None

for line in lines:
    if 'tablename' in line.lower() and 'indexname' in line.lower():
        # Header de tabla
        output.append('| Tabla | Índice | Definición | Único |')
        output.append('|-------|--------|------------|-------|')
    elif '|' in line and len(line.split('|')) >= 4:
        # Datos
        parts = [p.strip() for p in line.split('|')]
        if len(parts) >= 4:
            table = parts[0] if parts[0] else current_table
            if table:
                current_table = table
            idx_name = parts[1] if len(parts) > 1 else ''
            idx_def = parts[2] if len(parts) > 2 else ''
            is_unique = parts[3] if len(parts) > 3 else 'No'
            
            # Escapar pipes en definición
            idx_def = idx_def.replace('|', '\\|')
            
            output.append(f"| \`{table}\` | \`{idx_name}\` | \`{idx_def}\` | {is_unique} |")
    else:
        output.append(line)

with open('${INDEXES_REPORT}', 'w') as f:
    f.write('\n'.join(output))
PYEOF

echo -e "${GREEN}✅ Reporte generado: ${INDEXES_REPORT}${NC}"
echo ""

# ============================================================================
# RESUMEN
# ============================================================================
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}EXPORTACIÓN COMPLETADA${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Archivos generados:"
echo "  📄 ${SCHEMA_FILE}"
echo "  📊 ${TABLES_REPORT}"
echo "  🔗 ${FKS_REPORT}"
echo "  📇 ${INDEXES_REPORT}"
echo ""
echo -e "${BLUE}Nota: Todos los comandos fueron de SOLO LECTURA${NC}"
echo ""


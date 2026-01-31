#!/bin/bash
# ============================================================================
# Script de Diagnóstico de Base de Datos - Servidor Linux
# Ejecutar en: /var/www/stvaldivia
# ============================================================================

set -euo pipefail

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Generar nombre de reporte con timestamp
TIMESTAMP=$(date '+%Y-%m-%d_%H%M%S')
REPORT_FILE="docs/ESTADO_DB_REAL_${TIMESTAMP}.md"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}DIAGNÓSTICO DE BASE DE DATOS${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Fecha: $(date)"
echo "Directorio: $(pwd)"
echo "Usuario: $(whoami)"
echo ""

# Crear directorio docs si no existe
mkdir -p docs

# Iniciar reporte
cat > "$REPORT_FILE" << EOF
# Estado Real de Base de Datos - Diagnóstico

**Fecha:** $(date '+%Y-%m-%d %H:%M:%S')  
**Servidor:** $(hostname)  
**Directorio:** $(pwd)  
**Usuario:** $(whoami)

---

EOF

echo "## 1. VERIFICACIÓN DE ARCHIVO .env" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

ENV_FILE="/var/www/stvaldivia/.env"
if [ -f "$ENV_FILE" ]; then
    echo -e "${GREEN}✅ Archivo .env existe${NC}"
    echo "✅ Archivo .env existe" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"
    
    echo "**Comando:** \`ls -la $ENV_FILE\`" >> "$REPORT_FILE"
    echo "\`\`\`" >> "$REPORT_FILE"
    ls -la "$ENV_FILE" >> "$REPORT_FILE"
    echo "\`\`\`" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"
    
    echo "**Cargando variables desde .env:**" >> "$REPORT_FILE"
    echo "\`\`\`bash" >> "$REPORT_FILE"
    echo "set -a; source $ENV_FILE; set +a" >> "$REPORT_FILE"
    echo "\`\`\`" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"
    
    # Cargar .env sin modificar valores
    set -a
    source "$ENV_FILE" || true
    set +a
    
    # Obtener DATABASE_URL desde variable de entorno cargada
    DATABASE_URL="${DATABASE_URL:-}"
    
    if [ -n "$DATABASE_URL" ]; then
        # Mostrar DATABASE_URL sanitizado (sin modificar el valor real)
        DATABASE_URL_SANITIZED=$(echo "$DATABASE_URL" | sed -E 's#(postgresql://[^:]+):[^@]+@#\1:***@#')
        echo "**DATABASE_URL (password oculto):**" >> "$REPORT_FILE"
        echo "\`\`\`" >> "$REPORT_FILE"
        echo "$DATABASE_URL_SANITIZED" >> "$REPORT_FILE"
        echo "\`\`\`" >> "$REPORT_FILE"
    else
        echo "⚠️ DATABASE_URL no encontrado en .env" >> "$REPORT_FILE"
    fi
    echo "" >> "$REPORT_FILE"
else
    echo -e "${RED}❌ Archivo .env NO existe en $ENV_FILE${NC}"
    echo "❌ Archivo .env NO existe en $ENV_FILE" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"
    DATABASE_URL=""
fi

echo "" >> "$REPORT_FILE"
echo "## 2. VERIFICACIÓN DE POSTGRESQL INSTALADO" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

if command -v psql >/dev/null 2>&1; then
    echo -e "${GREEN}✅ psql encontrado${NC}"
    echo "✅ psql encontrado" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"
    echo "**Comando:** \`psql --version\`" >> "$REPORT_FILE"
    echo "\`\`\`" >> "$REPORT_FILE"
    psql --version >> "$REPORT_FILE" 2>&1
    echo "\`\`\`" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"
    echo "**Ubicación:** \`which psql\`" >> "$REPORT_FILE"
    echo "\`\`\`" >> "$REPORT_FILE"
    which psql >> "$REPORT_FILE" 2>&1
    echo "\`\`\`" >> "$REPORT_FILE"
else
    echo -e "${RED}❌ psql NO encontrado en PATH${NC}"
    echo "❌ psql NO encontrado en PATH" >> "$REPORT_FILE"
fi

echo "" >> "$REPORT_FILE"
echo "## 3. VERIFICACIÓN DE SERVICIO POSTGRESQL" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

echo "**Comando:** \`systemctl status postgresql\`" >> "$REPORT_FILE"
echo "\`\`\`" >> "$REPORT_FILE"
if systemctl status postgresql --no-pager -l 2>&1 | head -15 >> "$REPORT_FILE"; then
    echo -e "${GREEN}✅ Servicio postgresql encontrado${NC}"
else
    echo "" >> "$REPORT_FILE"
    echo "Servicios postgres detectados:" >> "$REPORT_FILE"
    systemctl list-units --type=service 2>/dev/null | grep -i postgres >> "$REPORT_FILE" 2>&1 || echo "No se encontraron servicios postgres" >> "$REPORT_FILE"
fi
echo "\`\`\`" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

echo "## 4. VERIFICACIÓN DE PUERTO 5432" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

if command -v ss >/dev/null 2>&1; then
    echo "**Comando:** \`ss -lntp | grep 5432\`" >> "$REPORT_FILE"
    echo "\`\`\`" >> "$REPORT_FILE"
    if ss -lntp 2>/dev/null | grep 5432 >> "$REPORT_FILE" 2>&1; then
        echo -e "${GREEN}✅ Puerto 5432 escuchando${NC}"
    else
        echo "Puerto 5432 no escuchando" >> "$REPORT_FILE"
        echo -e "${YELLOW}⚠️ Puerto 5432 no escuchando${NC}"
    fi
    echo "\`\`\`" >> "$REPORT_FILE"
elif command -v netstat >/dev/null 2>&1; then
    echo "**Comando:** \`netstat -lntp | grep 5432\`" >> "$REPORT_FILE"
    echo "\`\`\`" >> "$REPORT_FILE"
    if netstat -lntp 2>/dev/null | grep 5432 >> "$REPORT_FILE" 2>&1; then
        echo -e "${GREEN}✅ Puerto 5432 escuchando${NC}"
    else
        echo "Puerto 5432 no escuchando" >> "$REPORT_FILE"
    fi
    echo "\`\`\`" >> "$REPORT_FILE"
else
    echo "⚠️ ss y netstat no disponibles" >> "$REPORT_FILE"
fi
echo "" >> "$REPORT_FILE"

echo "## 5. EXTRACCIÓN Y PARSING DE DATABASE_URL" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

if [ -n "$DATABASE_URL" ]; then
    # Mostrar DATABASE_URL sanitizado (sin modificar el valor real)
    DATABASE_URL_SANITIZED=$(echo "$DATABASE_URL" | sed -E 's#(postgresql://[^:]+):[^@]+@#\1:***@#')
    echo "**DATABASE_URL (password oculto):**" >> "$REPORT_FILE"
    echo "\`\`\`" >> "$REPORT_FILE"
    echo "$DATABASE_URL_SANITIZED" >> "$REPORT_FILE"
    echo "\`\`\`" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"
    
    echo "**Componentes extraídos:**" >> "$REPORT_FILE"
    echo "\`\`\`" >> "$REPORT_FILE"
    python3 << PYEOF >> "$REPORT_FILE"
import re
import sys
import os

db_url = os.environ.get('DATABASE_URL', '')
if not db_url:
    try:
        with open('$ENV_FILE', 'r') as f:
            for line in f:
                if line.startswith('DATABASE_URL='):
                    db_url = line.split('=', 1)[1].strip().strip('"').strip("'")
                    break
    except:
        pass

if db_url:
    match = re.match(r'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', db_url)
    if match:
        user, password, host, port, dbname = match.groups()
        print(f"Usuario: {user}")
        print(f"Host: {host}")
        print(f"Puerto: {port}")
        print(f"Base de datos: {dbname}")
    else:
        match = re.match(r'postgresql://([^@]+)@([^:]+):(\d+)/(.+)', db_url)
        if match:
            user, host, port, dbname = match.groups()
            print(f"Usuario: {user}")
            print(f"Host: {host}")
            print(f"Puerto: {port}")
            print(f"Base de datos: {dbname}")
            print("⚠️ Sin password en URL")
        else:
            print(f"❌ Formato no reconocido: {db_url[:50]}...")
else:
    print("❌ DATABASE_URL no encontrado")
PYEOF
    echo "\`\`\`" >> "$REPORT_FILE"
else
    echo "❌ DATABASE_URL no disponible" >> "$REPORT_FILE"
fi
echo "" >> "$REPORT_FILE"

echo "## 6. PRUEBA DE CONEXIÓN CON DATABASE_URL" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

if [ -n "$DATABASE_URL" ]; then
    echo "**Comando:** \`psql \"\$DATABASE_URL\" -c \"SELECT 1 as test, current_database(), current_user;\"\`" >> "$REPORT_FILE"
    echo "\`\`\`" >> "$REPORT_FILE"
    if psql "$DATABASE_URL" -c "SELECT 1 as test, current_database(), current_user;" >> "$REPORT_FILE" 2>&1; then
        echo -e "${GREEN}✅ Conexión exitosa${NC}"
        echo "" >> "$REPORT_FILE"
        echo "✅ **Conexión exitosa**" >> "$REPORT_FILE"
    else
        echo -e "${RED}❌ Conexión falló${NC}"
        echo "" >> "$REPORT_FILE"
        echo "❌ **Conexión falló**" >> "$REPORT_FILE"
        echo "" >> "$REPORT_FILE"
        echo "**Detalles del error arriba**" >> "$REPORT_FILE"
    fi
    echo "\`\`\`" >> "$REPORT_FILE"
else
    echo "⚠️ No se puede probar conexión: DATABASE_URL no disponible" >> "$REPORT_FILE"
fi
echo "" >> "$REPORT_FILE"

echo "## 7. PRUEBA DE CONEXIÓN COMO POSTGRES LOCAL" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

if [ -n "$DATABASE_URL" ]; then
    DB_NAME=$(python3 << PYEOF
import re
import sys
import os

db_url = os.environ.get('DATABASE_URL', '')
if not db_url:
    try:
        with open('$ENV_FILE', 'r') as f:
            for line in f:
                if line.startswith('DATABASE_URL='):
                    db_url = line.split('=', 1)[1].strip().strip('"').strip("'")
                    break
    except:
        pass

if db_url:
    match = re.match(r'postgresql://[^@]+@[^:]+:\d+/(.+)', db_url)
    if not match:
        match = re.match(r'postgresql://[^:]+:[^@]+@[^:]+:\d+/(.+)', db_url)
    if match:
        print(match.group(1))
PYEOF
)
    
    if [ -n "$DB_NAME" ]; then
        echo "**Intentando conectar como usuario postgres a BD: \`$DB_NAME\`**" >> "$REPORT_FILE"
        echo "" >> "$REPORT_FILE"
        echo "**Comando:** \`sudo -u postgres psql -d \"$DB_NAME\" -c \"SELECT current_user, current_database();\"\`" >> "$REPORT_FILE"
        echo "\`\`\`" >> "$REPORT_FILE"
        if sudo -u postgres psql -d "$DB_NAME" -c "SELECT current_user, current_database();" >> "$REPORT_FILE" 2>&1; then
            echo -e "${GREEN}✅ Conexión como postgres exitosa${NC}"
            echo "" >> "$REPORT_FILE"
            echo "✅ **Conexión como postgres exitosa**" >> "$REPORT_FILE"
        else
            echo -e "${YELLOW}⚠️ Conexión como postgres falló${NC}"
            echo "" >> "$REPORT_FILE"
            echo "⚠️ **Conexión como postgres falló**" >> "$REPORT_FILE"
            echo "" >> "$REPORT_FILE"
            echo "**Listando bases de datos disponibles:**" >> "$REPORT_FILE"
            echo "\`\`\`" >> "$REPORT_FILE"
            sudo -u postgres psql -l >> "$REPORT_FILE" 2>&1 || echo "Error al listar bases de datos" >> "$REPORT_FILE"
            echo "\`\`\`" >> "$REPORT_FILE"
        fi
        echo "\`\`\`" >> "$REPORT_FILE"
    else
        echo "⚠️ No se pudo extraer nombre de BD desde DATABASE_URL" >> "$REPORT_FILE"
    fi
else
    echo "⚠️ No se puede probar: DATABASE_URL no disponible" >> "$REPORT_FILE"
fi
echo "" >> "$REPORT_FILE"

echo "## 8. VERIFICACIÓN DE pg_dump" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

if command -v pg_dump >/dev/null 2>&1; then
    echo -e "${GREEN}✅ pg_dump encontrado${NC}"
    echo "✅ pg_dump encontrado" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"
    echo "**Comando:** \`which pg_dump\`" >> "$REPORT_FILE"
    echo "\`\`\`" >> "$REPORT_FILE"
    which pg_dump >> "$REPORT_FILE" 2>&1
    echo "\`\`\`" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"
    echo "**Comando:** \`pg_dump --version\`" >> "$REPORT_FILE"
    echo "\`\`\`" >> "$REPORT_FILE"
    pg_dump --version >> "$REPORT_FILE" 2>&1
    echo "\`\`\`" >> "$REPORT_FILE"
else
    echo -e "${RED}❌ pg_dump NO encontrado${NC}"
    echo "❌ pg_dump NO encontrado" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"
    echo "**Comando para instalar (NO ejecutado):**" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"
    if command -v apt-get >/dev/null 2>&1; then
        echo "\`\`\`bash" >> "$REPORT_FILE"
        echo "sudo apt-get update && sudo apt-get install -y postgresql-client" >> "$REPORT_FILE"
        echo "\`\`\`" >> "$REPORT_FILE"
    elif command -v yum >/dev/null 2>&1; then
        echo "\`\`\`bash" >> "$REPORT_FILE"
        echo "sudo yum install -y postgresql" >> "$REPORT_FILE"
        echo "\`\`\`" >> "$REPORT_FILE"
    elif command -v dnf >/dev/null 2>&1; then
        echo "\`\`\`bash" >> "$REPORT_FILE"
        echo "sudo dnf install -y postgresql" >> "$REPORT_FILE"
        echo "\`\`\`" >> "$REPORT_FILE"
    else
        echo "Verificar gestor de paquetes del sistema" >> "$REPORT_FILE"
    fi
fi
echo "" >> "$REPORT_FILE"

echo "## 9. INFORMACIÓN ADICIONAL DEL SISTEMA" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

echo "**Sistema operativo:**" >> "$REPORT_FILE"
echo "\`\`\`" >> "$REPORT_FILE"
uname -a >> "$REPORT_FILE" 2>&1
echo "\`\`\`" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

echo "**Versión de Python:**" >> "$REPORT_FILE"
echo "\`\`\`" >> "$REPORT_FILE"
python3 --version >> "$REPORT_FILE" 2>&1 || echo "Python3 no disponible" >> "$REPORT_FILE"
echo "\`\`\`" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

echo "**Directorio actual:**" >> "$REPORT_FILE"
echo "\`\`\`" >> "$REPORT_FILE"
pwd >> "$REPORT_FILE"
echo "\`\`\`" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

echo "---" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"
echo "**Reporte generado:** $(date '+%Y-%m-%d %H:%M:%S')" >> "$REPORT_FILE"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}DIAGNÓSTICO COMPLETADO${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "📄 Reporte generado: ${BLUE}${REPORT_FILE}${NC}"
echo ""
echo -e "${BLUE}⚠️  NOTA: Este script es de SOLO LECTURA. No se realizaron cambios.${NC}"
echo ""
echo -e "${YELLOW}Comando exacto ejecutado:${NC}"
echo "  cd /var/www/stvaldivia && ./scripts/diagnostico_db_servidor.sh"
echo ""


#!/bin/bash
# ============================================================================
# Script para Configurar MySQL en Entorno Local (macOS)
# ============================================================================

set -euo pipefail

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}CONFIGURACIÓN MYSQL LOCAL${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# ============================================================================
# 1. INSTALAR MYSQL
# ============================================================================

echo -e "${YELLOW}[1/4] Verificando MySQL...${NC}"

if command -v mysql >/dev/null 2>&1; then
    MYSQL_VERSION=$(mysql --version 2>&1 | head -1)
    echo -e "${GREEN}✅ MySQL encontrado: ${MYSQL_VERSION}${NC}"
else
    echo -e "${YELLOW}⚠️  MySQL no encontrado${NC}"
    echo ""
    read -p "¿Instalar MySQL via Homebrew? (s/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Ss]$ ]]; then
        if ! command -v brew >/dev/null 2>&1; then
            echo -e "${RED}❌ Homebrew no encontrado${NC}"
            echo "   Instalar Homebrew primero"
            exit 1
        fi
        
        echo "   Instalando MySQL..."
        brew install mysql
        
        echo "   Iniciando servicio MySQL..."
        brew services start mysql
        
        echo -e "${GREEN}✅ MySQL instalado e iniciado${NC}"
        echo ""
        echo -e "${YELLOW}⚠️  IMPORTANTE: Configura la contraseña de root${NC}"
        echo "   Ejecutar: mysql_secure_installation"
    else
        echo "   Instalación cancelada"
        exit 1
    fi
fi

echo ""

# ============================================================================
# 2. VERIFICAR SERVICIO
# ============================================================================

echo -e "${YELLOW}[2/4] Verificando servicio MySQL...${NC}"

if brew services list 2>/dev/null | grep -q "mysql.*started"; then
    echo -e "${GREEN}✅ Servicio MySQL corriendo${NC}"
elif ps aux | grep -i "[m]ysqld" >/dev/null; then
    echo -e "${GREEN}✅ MySQL corriendo (detectado proceso)${NC}"
else
    echo -e "${YELLOW}⚠️  MySQL no está corriendo${NC}"
    read -p "¿Iniciar MySQL? (s/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Ss]$ ]]; then
        if command -v brew >/dev/null 2>&1; then
            brew services start mysql
        else
            mysql.server start 2>/dev/null || echo "   Intentar manualmente: mysql.server start"
        fi
        sleep 2
        echo -e "${GREEN}✅ MySQL iniciado${NC}"
    else
        echo "   No se puede continuar sin MySQL corriendo"
        exit 1
    fi
fi

echo ""

# ============================================================================
# 3. CREAR BASE DE DATOS
# ============================================================================

echo -e "${YELLOW}[3/4] Configurando base de datos...${NC}"

DB_NAME="bimba_db"
DB_USER="bimba_user"
DB_PASS="bimba_local_2025"

# Intentar conectar como root
echo "   Intentando conectar a MySQL..."

ROOT_PASS=""
if mysql -u root -e "SELECT 1;" >/dev/null 2>&1; then
    echo -e "${GREEN}✅ Conexión como root exitosa (sin contraseña)${NC}"
    MYSQL_CMD="mysql -u root"
elif [ -n "${MYSQL_ROOT_PASSWORD:-}" ]; then
    if mysql -u root -p"${MYSQL_ROOT_PASSWORD}" -e "SELECT 1;" >/dev/null 2>&1; then
        ROOT_PASS="${MYSQL_ROOT_PASSWORD}"
        MYSQL_CMD="mysql -u root -p${ROOT_PASS}"
        echo -e "${GREEN}✅ Conexión como root exitosa (con contraseña de variable)${NC}"
    fi
fi

if [ -z "$MYSQL_CMD" ]; then
    echo -e "${YELLOW}⚠️  No se puede conectar como root sin contraseña${NC}"
    read -sp "Ingresa contraseña de root MySQL (o Enter si no tiene): " ROOT_PASS
    echo ""
    
    if [ -n "$ROOT_PASS" ]; then
        if ! mysql -u root -p"$ROOT_PASS" -e "SELECT 1;" >/dev/null 2>&1; then
            echo -e "${RED}❌ Contraseña incorrecta${NC}"
            exit 1
        fi
        MYSQL_CMD="mysql -u root -p${ROOT_PASS}"
    else
        if ! mysql -u root -e "SELECT 1;" >/dev/null 2>&1; then
            echo -e "${RED}❌ No se puede conectar a MySQL${NC}"
            exit 1
        fi
        MYSQL_CMD="mysql -u root"
    fi
fi

# Crear base de datos
echo "   Creando base de datos ${DB_NAME}..."
$MYSQL_CMD << SQL
CREATE DATABASE IF NOT EXISTS ${DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
SQL

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Base de datos ${DB_NAME} creada${NC}"
else
    echo -e "${RED}❌ Error al crear base de datos${NC}"
    exit 1
fi

# Crear usuario
echo "   Creando usuario ${DB_USER}..."
$MYSQL_CMD << SQL
CREATE USER IF NOT EXISTS '${DB_USER}'@'localhost' IDENTIFIED BY '${DB_PASS}';
GRANT ALL PRIVILEGES ON ${DB_NAME}.* TO '${DB_USER}'@'localhost';
FLUSH PRIVILEGES;
SQL

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Usuario ${DB_USER} creado${NC}"
else
    echo -e "${YELLOW}⚠️  Usuario ya existe o error (puedes usar root)${NC}"
fi

echo ""

# ============================================================================
# 4. CONFIGURAR DATABASE_URL
# ============================================================================

echo -e "${YELLOW}[4/4] Configurando DATABASE_URL...${NC}"

ENV_FILE=".env"
DATABASE_URL="mysql://${DB_USER}:${DB_PASS}@localhost:3306/${DB_NAME}"

# Verificar si el usuario funciona
if ! mysql -u "${DB_USER}" -p"${DB_PASS}" -e "SELECT 1;" >/dev/null 2>&1; then
    echo "   Usando root en lugar de ${DB_USER}..."
    if [ -n "$ROOT_PASS" ]; then
        DATABASE_URL="mysql://root:${ROOT_PASS}@localhost:3306/${DB_NAME}"
    else
        DATABASE_URL="mysql://root@localhost:3306/${DB_NAME}"
    fi
fi

if [ -f "$ENV_FILE" ]; then
    # Backup del .env existente
    cp "$ENV_FILE" "${ENV_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
    echo "   Backup de .env creado"
    
    # Actualizar o agregar DATABASE_URL
    if grep -q "^DATABASE_URL=" "$ENV_FILE"; then
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' "s|^DATABASE_URL=.*|DATABASE_URL=${DATABASE_URL}|" "$ENV_FILE"
        else
            sed -i "s|^DATABASE_URL=.*|DATABASE_URL=${DATABASE_URL}|" "$ENV_FILE"
        fi
        echo -e "${GREEN}✅ DATABASE_URL actualizado en .env${NC}"
    else
        echo "DATABASE_URL=${DATABASE_URL}" >> "$ENV_FILE"
        echo -e "${GREEN}✅ DATABASE_URL agregado a .env${NC}"
    fi
else
    # Crear .env nuevo
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null || echo "change-me-in-production")
    cat > "$ENV_FILE" << EOF
# Configuración de Base de Datos
DATABASE_URL=${DATABASE_URL}

# Flask
FLASK_ENV=development
SECRET_KEY=${SECRET_KEY}
EOF
    echo -e "${GREEN}✅ Archivo .env creado${NC}"
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}CONFIGURACIÓN COMPLETADA${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Base de datos: ${DB_NAME}"
echo "Usuario: ${DB_USER}"
echo "DATABASE_URL configurado en .env"
echo ""
echo -e "${BLUE}Próximos pasos:${NC}"
echo "  1. Verificar: ./scripts/verificar_preparacion_mysql.sh"
echo "  2. Migrar: ./scripts/migrar_a_mysql.sh"
echo "  3. Validar: ./scripts/validar_migracion_mysql.sh"
echo ""


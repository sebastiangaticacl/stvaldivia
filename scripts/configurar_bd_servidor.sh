#!/bin/bash
# Script para configurar bases de datos en el servidor VM de Google
# Ejecutar en el servidor VM

set -e

echo "=" * 80
echo "🔧 CONFIGURACIÓN DE BASES DE DATOS EN SERVIDOR VM"
echo "=" * 80
echo ""

# Obtener directorio del proyecto
PROJECT_DIR="${1:-$(pwd)}"
if [ ! -d "$PROJECT_DIR" ]; then
    echo "❌ Error: Directorio del proyecto no encontrado: $PROJECT_DIR"
    exit 1
fi

ENV_FILE="$PROJECT_DIR/.env"

# Obtener IP del servidor
SERVER_IP=$(hostname -I | awk '{print $1}' || echo "localhost")
echo "📍 IP del servidor: $SERVER_IP"
echo ""

# Solicitar credenciales
echo "📝 Configuración de MySQL:"
read -p "Usuario MySQL (default: bimba_user): " MYSQL_USER
MYSQL_USER=${MYSQL_USER:-bimba_user}

read -sp "Password MySQL: " MYSQL_PASS
echo ""

read -p "Host MySQL (default: localhost): " MYSQL_HOST
MYSQL_HOST=${MYSQL_HOST:-localhost}

read -p "Puerto MySQL (default: 3306): " MYSQL_PORT
MYSQL_PORT=${MYSQL_PORT:-3306}

# Construir URLs
PROD_URL="mysql://${MYSQL_USER}:${MYSQL_PASS}@${MYSQL_HOST}:${MYSQL_PORT}/bimba_prod"
DEV_URL="mysql://${MYSQL_USER}:${MYSQL_PASS}@${MYSQL_HOST}:${MYSQL_PORT}/bimba_dev"

echo ""
echo "📋 URLs generadas:"
echo "   PROD: mysql://${MYSQL_USER}:***@${MYSQL_HOST}:${MYSQL_PORT}/bimba_prod"
echo "   DEV:  mysql://${MYSQL_USER}:***@${MYSQL_HOST}:${MYSQL_PORT}/bimba_dev"
echo ""

# Verificar si las bases de datos existen
echo "🔍 Verificando bases de datos..."
if command -v mysql &> /dev/null; then
    DB_EXISTS_PROD=$(mysql -h "$MYSQL_HOST" -P "$MYSQL_PORT" -u "$MYSQL_USER" -p"$MYSQL_PASS" -e "SHOW DATABASES LIKE 'bimba_prod';" 2>/dev/null | grep -c "bimba_prod" || echo "0")
    DB_EXISTS_DEV=$(mysql -h "$MYSQL_HOST" -P "$MYSQL_PORT" -u "$MYSQL_USER" -p"$MYSQL_PASS" -e "SHOW DATABASES LIKE 'bimba_dev';" 2>/dev/null | grep -c "bimba_dev" || echo "0")
    
    if [ "$DB_EXISTS_PROD" -eq "0" ]; then
        echo "⚠️  Base de datos 'bimba_prod' no existe"
        read -p "¿Crear base de datos de producción? (s/n): " CREATE_PROD
        if [ "$CREATE_PROD" = "s" ] || [ "$CREATE_PROD" = "S" ]; then
            mysql -h "$MYSQL_HOST" -P "$MYSQL_PORT" -u "$MYSQL_USER" -p"$MYSQL_PASS" -e "CREATE DATABASE IF NOT EXISTS bimba_prod CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
            echo "✅ Base de datos 'bimba_prod' creada"
        fi
    else
        echo "✅ Base de datos 'bimba_prod' existe"
    fi
    
    if [ "$DB_EXISTS_DEV" -eq "0" ]; then
        echo "⚠️  Base de datos 'bimba_dev' no existe"
        read -p "¿Crear base de datos de desarrollo? (s/n): " CREATE_DEV
        if [ "$CREATE_DEV" = "s" ] || [ "$CREATE_DEV" = "S" ]; then
            mysql -h "$MYSQL_HOST" -P "$MYSQL_PORT" -u "$MYSQL_USER" -p"$MYSQL_PASS" -e "CREATE DATABASE IF NOT EXISTS bimba_dev CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
            echo "✅ Base de datos 'bimba_dev' creada"
        fi
    else
        echo "✅ Base de datos 'bimba_dev' existe"
    fi
else
    echo "⚠️  MySQL client no encontrado, saltando verificación"
fi

echo ""
echo "📝 Configurando archivo .env..."

# Crear backup si existe
if [ -f "$ENV_FILE" ]; then
    cp "$ENV_FILE" "$ENV_FILE.backup.$(date +%Y%m%d_%H%M%S)"
    echo "✅ Backup de .env guardado"
fi

# Agregar o actualizar variables
if grep -q "^DATABASE_PROD_URL=" "$ENV_FILE" 2>/dev/null; then
    sed -i.bak "s|^DATABASE_PROD_URL=.*|DATABASE_PROD_URL=$PROD_URL|" "$ENV_FILE"
else
    echo "DATABASE_PROD_URL=$PROD_URL" >> "$ENV_FILE"
fi

if grep -q "^DATABASE_DEV_URL=" "$ENV_FILE" 2>/dev/null; then
    sed -i.bak "s|^DATABASE_DEV_URL=.*|DATABASE_DEV_URL=$DEV_URL|" "$ENV_FILE"
else
    echo "DATABASE_DEV_URL=$DEV_URL" >> "$ENV_FILE"
fi

if grep -q "^DATABASE_MODE=" "$ENV_FILE" 2>/dev/null; then
    # No cambiar el modo si ya existe
    echo "ℹ️  DATABASE_MODE ya configurado, manteniendo valor actual"
else
    echo "DATABASE_MODE=prod" >> "$ENV_FILE"
fi

echo "✅ Variables de entorno configuradas en: $ENV_FILE"
echo ""

# Ejecutar migración si es posible
if [ -f "$PROJECT_DIR/migrate_system_config.py" ]; then
    echo "🔄 Ejecutando migración..."
    cd "$PROJECT_DIR"
    python3 migrate_system_config.py 2>/dev/null || echo "⚠️  No se pudo ejecutar migración automáticamente"
fi

echo ""
echo "=" * 80
echo "✅ CONFIGURACIÓN COMPLETADA"
echo "=" * 80
echo ""
echo "📋 RESUMEN:"
echo "   - Bases de datos configuradas en servidor VM"
echo "   - Variables de entorno guardadas en: $ENV_FILE"
echo ""
echo "💡 Para desarrolladores, usar en su .env local:"
echo "   DATABASE_PROD_URL=mysql://${MYSQL_USER}:***@${SERVER_IP}:${MYSQL_PORT}/bimba_prod"
echo "   DATABASE_DEV_URL=mysql://${MYSQL_USER}:***@${SERVER_IP}:${MYSQL_PORT}/bimba_dev"
echo "   DATABASE_MODE=dev"
echo ""
echo "⚠️  IMPORTANTE:"
echo "   - No compartir el archivo .env con credenciales"
echo "   - Usar VPN o SSH tunnel para acceso remoto"
echo "   - Reiniciar la aplicación después de cambios"
echo ""




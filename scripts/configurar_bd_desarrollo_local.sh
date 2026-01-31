#!/bin/bash
# Script para configurar conexión a bases de datos del servidor VM desde computadora de desarrollo
# Ejecutar en la computadora de desarrollo local

set -e

echo "=" * 80
echo "💻 CONFIGURACIÓN DE BASE DE DATOS PARA DESARROLLO LOCAL"
echo "=" * 80
echo ""
echo "Este script configura tu entorno local para conectarte a las bases de datos"
echo "que están guardadas en el servidor VM de Google."
echo ""

# Obtener directorio del proyecto
PROJECT_DIR="${1:-$(pwd)}"
if [ ! -d "$PROJECT_DIR" ]; then
    echo "❌ Error: Directorio del proyecto no encontrado: $PROJECT_DIR"
    exit 1
fi

ENV_FILE="$PROJECT_DIR/.env"

# Solicitar información del servidor
echo "📝 Información del servidor VM:"
read -p "IP o hostname del servidor VM: " SERVER_IP
if [ -z "$SERVER_IP" ]; then
    echo "❌ Error: IP del servidor es requerida"
    exit 1
fi

read -p "Puerto MySQL en servidor (default: 3306): " SERVER_PORT
SERVER_PORT=${SERVER_PORT:-3306}

echo ""
echo "📝 Credenciales MySQL:"
read -p "Usuario MySQL: " MYSQL_USER
if [ -z "$MYSQL_USER" ]; then
    echo "❌ Error: Usuario MySQL es requerido"
    exit 1
fi

read -sp "Password MySQL: " MYSQL_PASS
echo ""

# Construir URLs apuntando al servidor
PROD_URL="mysql://${MYSQL_USER}:${MYSQL_PASS}@${SERVER_IP}:${SERVER_PORT}/bimba_prod"
DEV_URL="mysql://${MYSQL_USER}:${MYSQL_PASS}@${SERVER_IP}:${SERVER_PORT}/bimba_dev"

echo ""
echo "📋 URLs generadas (apuntando al servidor VM):"
echo "   PROD: mysql://${MYSQL_USER}:***@${SERVER_IP}:${SERVER_PORT}/bimba_prod"
echo "   DEV:  mysql://${MYSQL_USER}:***@${SERVER_IP}:${SERVER_PORT}/bimba_dev"
echo ""

# Preguntar modo inicial
echo "📝 Modo inicial:"
read -p "¿Qué modo usar inicialmente? (dev/prod, default: dev): " INITIAL_MODE
INITIAL_MODE=${INITIAL_MODE:-dev}

# Probar conexión
echo ""
echo "🔍 Probando conexión al servidor..."
if command -v mysql &> /dev/null; then
    if mysql -h "$SERVER_IP" -P "$SERVER_PORT" -u "$MYSQL_USER" -p"$MYSQL_PASS" -e "SHOW DATABASES LIKE 'bimba%';" 2>/dev/null | grep -q "bimba"; then
        echo "✅ Conexión exitosa al servidor VM"
        
        # Verificar que las bases de datos existen
        DB_PROD_EXISTS=$(mysql -h "$SERVER_IP" -P "$SERVER_PORT" -u "$MYSQL_USER" -p"$MYSQL_PASS" -e "SHOW DATABASES LIKE 'bimba_prod';" 2>/dev/null | grep -c "bimba_prod" || echo "0")
        DB_DEV_EXISTS=$(mysql -h "$SERVER_IP" -P "$SERVER_PORT" -u "$MYSQL_USER" -p"$MYSQL_PASS" -e "SHOW DATABASES LIKE 'bimba_dev';" 2>/dev/null | grep -c "bimba_dev" || echo "0")
        
        if [ "$DB_PROD_EXISTS" -eq "0" ]; then
            echo "⚠️  Advertencia: Base de datos 'bimba_prod' no encontrada en el servidor"
        else
            echo "✅ Base de datos 'bimba_prod' encontrada"
        fi
        
        if [ "$DB_DEV_EXISTS" -eq "0" ]; then
            echo "⚠️  Advertencia: Base de datos 'bimba_dev' no encontrada en el servidor"
        else
            echo "✅ Base de datos 'bimba_dev' encontrada"
        fi
    else
        echo "⚠️  No se pudo conectar al servidor. Verifica:"
        echo "   - IP/hostname correcto"
        echo "   - Puerto accesible"
        echo "   - Credenciales correctas"
        echo "   - Firewall/VPN configurado"
        read -p "¿Continuar de todas formas? (s/n): " CONTINUE
        if [ "$CONTINUE" != "s" ] && [ "$CONTINUE" != "S" ]; then
            exit 1
        fi
    fi
else
    echo "⚠️  MySQL client no encontrado, saltando prueba de conexión"
fi

# Crear backup si existe
if [ -f "$ENV_FILE" ]; then
    cp "$ENV_FILE" "$ENV_FILE.backup.$(date +%Y%m%d_%H%M%S)"
    echo "✅ Backup de .env guardado"
fi

# Configurar .env
echo ""
echo "📝 Configurando archivo .env..."

# Agregar o actualizar variables
if grep -q "^DATABASE_PROD_URL=" "$ENV_FILE" 2>/dev/null; then
    sed -i.bak "s|^DATABASE_PROD_URL=.*|DATABASE_PROD_URL=$PROD_URL|" "$ENV_FILE"
else
    echo "" >> "$ENV_FILE"
    echo "# Bases de datos en servidor VM" >> "$ENV_FILE"
    echo "DATABASE_PROD_URL=$PROD_URL" >> "$ENV_FILE"
fi

if grep -q "^DATABASE_DEV_URL=" "$ENV_FILE" 2>/dev/null; then
    sed -i.bak "s|^DATABASE_DEV_URL=.*|DATABASE_DEV_URL=$DEV_URL|" "$ENV_FILE"
else
    echo "DATABASE_DEV_URL=$DEV_URL" >> "$ENV_FILE"
fi

if grep -q "^DATABASE_MODE=" "$ENV_FILE" 2>/dev/null; then
    sed -i.bak "s|^DATABASE_MODE=.*|DATABASE_MODE=$INITIAL_MODE|" "$ENV_FILE"
else
    echo "DATABASE_MODE=$INITIAL_MODE" >> "$ENV_FILE"
fi

echo "✅ Variables de entorno configuradas en: $ENV_FILE"
echo ""

# Opción de SSH Tunnel
echo "🔒 Seguridad:"
read -p "¿Quieres usar SSH Tunnel para mayor seguridad? (s/n): " USE_SSH
if [ "$USE_SSH" = "s" ] || [ "$USE_SSH" = "S" ]; then
    read -p "Usuario SSH en servidor VM: " SSH_USER
    read -p "Puerto SSH (default: 22): " SSH_PORT
    SSH_PORT=${SSH_PORT:-22}
    
    LOCAL_PORT=3307
    
    echo ""
    echo "📋 Para usar SSH Tunnel, ejecuta este comando en otra terminal:"
    echo "   ssh -L ${LOCAL_PORT}:localhost:3306 ${SSH_USER}@${SERVER_IP} -p ${SSH_PORT}"
    echo ""
    echo "   Luego actualiza tu .env con:"
    echo "   DATABASE_PROD_URL=mysql://${MYSQL_USER}:***@127.0.0.1:${LOCAL_PORT}/bimba_prod"
    echo "   DATABASE_DEV_URL=mysql://${MYSQL_USER}:***@127.0.0.1:${LOCAL_PORT}/bimba_dev"
fi

echo ""
echo "=" * 80
echo "✅ CONFIGURACIÓN COMPLETADA"
echo "=" * 80
echo ""
echo "📋 RESUMEN:"
echo "   - Configurado para conectarse al servidor VM: $SERVER_IP"
echo "   - Modo inicial: $INITIAL_MODE"
echo "   - Archivo: $ENV_FILE"
echo ""
echo "💡 Próximos pasos:"
echo "   1. Ejecutar migración: python3 migrate_system_config.py"
echo "   2. Iniciar aplicación: python3 run_local.py"
echo "   3. Acceder a /admin/panel_control para cambiar modo si es necesario"
echo ""
echo "⚠️  IMPORTANTE:"
echo "   - Las bases de datos están en el servidor VM, no localmente"
echo "   - Todos los desarrolladores comparten las mismas bases de datos"
echo "   - Usa el toggle en el panel de control para cambiar entre dev/prod"
echo ""




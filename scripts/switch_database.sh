#!/bin/bash
# Script para cambiar entre bases de datos de desarrollo y producción
# Uso: source scripts/switch_database.sh [dev|prod|local]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$PROJECT_ROOT/.env"

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

case "$1" in
  prod)
    echo -e "${RED}⚠️  ADVERTENCIAS:${NC}"
    echo -e "${RED}   - Estás conectando a PRODUCCIÓN${NC}"
    echo -e "${RED}   - Cualquier cambio afectará datos reales${NC}"
    echo -e "${RED}   - Asegúrate de tener un backup${NC}"
    echo ""
    read -p "¿Estás seguro? (escribe 'SI' para continuar): " confirm
    if [ "$confirm" != "SI" ]; then
        echo "❌ Operación cancelada"
        exit 1
    fi
    
    # Solicitar DATABASE_URL de producción
    echo ""
    echo "Ingresa el DATABASE_URL de producción:"
    echo "Formato: mysql://usuario:password@host:puerto/database"
    read -p "DATABASE_URL: " PROD_DB_URL
    
    if [ -z "$PROD_DB_URL" ]; then
        echo "❌ DATABASE_URL no puede estar vacío"
        exit 1
    fi
    
    # Crear backup del .env actual
    if [ -f "$ENV_FILE" ]; then
        cp "$ENV_FILE" "$ENV_FILE.backup.$(date +%Y%m%d_%H%M%S)"
        echo "✅ Backup de .env guardado"
    fi
    
    # Actualizar .env
    if [ -f "$ENV_FILE" ]; then
        # Si existe DATABASE_URL, reemplazarlo
        if grep -q "^DATABASE_URL=" "$ENV_FILE"; then
            sed -i.bak "s|^DATABASE_URL=.*|DATABASE_URL=$PROD_DB_URL|" "$ENV_FILE"
        else
            echo "DATABASE_URL=$PROD_DB_URL" >> "$ENV_FILE"
        fi
    else
        echo "DATABASE_URL=$PROD_DB_URL" > "$ENV_FILE"
    fi
    
    echo -e "${GREEN}✅ Base de datos cambiada a PRODUCCIÓN${NC}"
    echo -e "${YELLOW}⚠️  Recuerda cambiar de vuelta a desarrollo cuando termines${NC}"
    ;;
    
  dev)
    # Solicitar DATABASE_URL de desarrollo
    echo "Ingresa el DATABASE_URL de desarrollo:"
    echo "Formato: mysql://usuario:password@localhost:3306/bimba_dev"
    read -p "DATABASE_URL (Enter para default): " DEV_DB_URL
    
    if [ -z "$DEV_DB_URL" ]; then
        DEV_DB_URL="mysql://bimba_user:password@localhost:3306/bimba_dev"
        echo "Usando default: $DEV_DB_URL"
    fi
    
    # Actualizar .env
    if [ -f "$ENV_FILE" ]; then
        if grep -q "^DATABASE_URL=" "$ENV_FILE"; then
            sed -i.bak "s|^DATABASE_URL=.*|DATABASE_URL=$DEV_DB_URL|" "$ENV_FILE"
        else
            echo "DATABASE_URL=$DEV_DB_URL" >> "$ENV_FILE"
        fi
    else
        echo "DATABASE_URL=$DEV_DB_URL" > "$ENV_FILE"
    fi
    
    echo -e "${GREEN}✅ Base de datos cambiada a DESARROLLO${NC}"
    ;;
    
  local)
    # Remover DATABASE_URL para usar SQLite
    if [ -f "$ENV_FILE" ]; then
        if grep -q "^DATABASE_URL=" "$ENV_FILE"; then
            sed -i.bak "/^DATABASE_URL=/d" "$ENV_FILE"
        fi
    fi
    
    echo -e "${GREEN}✅ Base de datos cambiada a SQLite (local)${NC}"
    ;;
    
  *)
    echo "Uso: source scripts/switch_database.sh {dev|prod|local}"
    echo ""
    echo "Opciones:"
    echo "  dev   - Base de datos de desarrollo (MySQL local)"
    echo "  prod  - Base de datos de producción (⚠️  PELIGRO)"
    echo "  local - SQLite local (desarrollo rápido)"
    exit 1
    ;;
esac

# Mostrar configuración actual
echo ""
echo "📋 Configuración actual:"
if [ -f "$ENV_FILE" ] && grep -q "^DATABASE_URL=" "$ENV_FILE"; then
    DB_URL=$(grep "^DATABASE_URL=" "$ENV_FILE" | cut -d'=' -f2-)
    # Ocultar password en el output
    DB_URL_SAFE=$(echo "$DB_URL" | sed 's/:[^@]*@/:***@/')
    echo "   DATABASE_URL=$DB_URL_SAFE"
else
    echo "   DATABASE_URL=(no configurado - usará SQLite)"
fi




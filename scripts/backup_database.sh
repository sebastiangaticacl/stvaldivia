#!/bin/bash
# Script para hacer backup de la base de datos actual
# Detecta automáticamente el tipo de base de datos desde .env

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$PROJECT_ROOT/.env"
BACKUP_DIR="$PROJECT_ROOT/backups"

# Crear directorio de backups
mkdir -p "$BACKUP_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Cargar .env si existe
if [ -f "$ENV_FILE" ]; then
    source "$ENV_FILE"
fi

# Obtener DATABASE_URL
DATABASE_URL=${DATABASE_URL:-""}

if [ -z "$DATABASE_URL" ]; then
    echo "⚠️  DATABASE_URL no configurado"
    echo "   Usando SQLite local..."
    
    # Buscar archivo SQLite
    SQLITE_DB="$PROJECT_ROOT/instance/bimba.db"
    if [ -f "$SQLITE_DB" ]; then
        BACKUP_FILE="$BACKUP_DIR/sqlite_backup_${TIMESTAMP}.db"
        cp "$SQLITE_DB" "$BACKUP_FILE"
        echo "✅ Backup SQLite guardado en: $BACKUP_FILE"
    else
        echo "❌ No se encontró base de datos SQLite en: $SQLITE_DB"
        exit 1
    fi
    exit 0
fi

# Detectar tipo de base de datos
if [[ $DATABASE_URL == mysql* ]]; then
    echo "📦 Haciendo backup de MySQL..."
    
    # Extraer componentes de DATABASE_URL
    # Formato: mysql://usuario:password@host:port/database
    DB_URL=${DATABASE_URL#mysql://}
    DB_CREDS=${DB_URL%@*}
    DB_USER=${DB_CREDS%:*}
    DB_PASS=${DB_CREDS#*:}
    DB_HOST_PORT=${DB_URL#*@}
    DB_HOST=${DB_HOST_PORT%%:*}
    DB_PORT_DB=${DB_HOST_PORT#*:}
    DB_PORT=${DB_PORT_DB%%/*}
    DB_NAME=${DB_PORT_DB#*/}
    
    BACKUP_FILE="$BACKUP_DIR/mysql_backup_${DB_NAME}_${TIMESTAMP}.sql"
    
    # Hacer backup
    mysqldump -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -p"$DB_PASS" "$DB_NAME" > "$BACKUP_FILE" 2>/dev/null
    
    if [ $? -eq 0 ]; then
        # Comprimir backup
        gzip "$BACKUP_FILE"
        echo "✅ Backup MySQL guardado en: ${BACKUP_FILE}.gz"
        echo "   Tamaño: $(du -h "${BACKUP_FILE}.gz" | cut -f1)"
    else
        echo "❌ Error al hacer backup de MySQL"
        echo "   Verifica las credenciales en .env"
        exit 1
    fi
    
elif [[ $DATABASE_URL == postgresql* ]] || [[ $DATABASE_URL == postgres* ]]; then
    echo "📦 Haciendo backup de PostgreSQL..."
    
    # Extraer componentes de DATABASE_URL
    # Formato: postgresql://usuario:password@host:port/database
    DB_URL=${DATABASE_URL#postgresql://}
    DB_URL=${DB_URL#postgres://}
    DB_CREDS=${DB_URL%@*}
    DB_USER=${DB_CREDS%:*}
    DB_PASS=${DB_CREDS#*:}
    DB_HOST_PORT=${DB_URL#*@}
    DB_HOST=${DB_HOST_PORT%%:*}
    DB_PORT_DB=${DB_HOST_PORT#*:}
    DB_PORT=${DB_PORT_DB%%/*}
    DB_NAME=${DB_PORT_DB#*/}
    
    BACKUP_FILE="$BACKUP_DIR/postgres_backup_${DB_NAME}_${TIMESTAMP}.sql"
    
    # Configurar PGPASSWORD
    export PGPASSWORD="$DB_PASS"
    
    # Hacer backup
    pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" > "$BACKUP_FILE" 2>/dev/null
    
    if [ $? -eq 0 ]; then
        # Comprimir backup
        gzip "$BACKUP_FILE"
        echo "✅ Backup PostgreSQL guardado en: ${BACKUP_FILE}.gz"
        echo "   Tamaño: $(du -h "${BACKUP_FILE}.gz" | cut -f1)"
    else
        echo "❌ Error al hacer backup de PostgreSQL"
        echo "   Verifica las credenciales en .env"
        exit 1
    fi
    
else
    echo "⚠️  Tipo de base de datos no soportado para backup automático"
    echo "   DATABASE_URL: ${DATABASE_URL:0:30}..."
    exit 1
fi

# Limpiar backups antiguos (mantener solo los últimos 10)
echo ""
echo "🧹 Limpiando backups antiguos (manteniendo últimos 10)..."
cd "$BACKUP_DIR"
ls -t *.gz 2>/dev/null | tail -n +11 | xargs rm -f 2>/dev/null
echo "✅ Limpieza completada"




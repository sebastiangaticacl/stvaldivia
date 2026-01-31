#!/bin/bash
# Script para desplegar versión local completa al servidor
# Elimina todo en el servidor y sube la versión local desde git

set -e

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuración
SSH_HOST="stvaldivia"
REMOTE_DIR="/var/www/stvaldivia"
REPO_URL="https://github.com/stvaldivia/stvaldivia.git"
BACKUP_DIR="/tmp/stvaldivia_backup_$(date +%Y%m%d_%H%M%S)"

echo "=========================================="
echo "🚀 DEPLOY COMPLETO: LOCAL → SERVIDOR"
echo "=========================================="
echo ""
echo "⚠️  ADVERTENCIA: Esto eliminará TODO en $REMOTE_DIR"
echo "   Se creará un backup en: $BACKUP_DIR"
echo ""
read -p "¿Continuar? (escribe 'si' para confirmar): " confirm
if [ "$confirm" != "si" ]; then
    echo "❌ Deploy cancelado"
    exit 1
fi

echo ""
echo "📋 PASO 1: Verificando conexión SSH..."
if ! ssh "$SSH_HOST" "echo '✅ Conexión OK'" > /dev/null 2>&1; then
    echo -e "${RED}❌ No se puede conectar al servidor${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Conexión SSH OK${NC}"

echo ""
echo "📋 PASO 2: Creando backup del contenido actual..."
ssh "$SSH_HOST" << 'ENDSSH'
    set -e
    REMOTE_DIR="/var/www/stvaldivia"
    BACKUP_DIR="/tmp/stvaldivia_backup_$(date +%Y%m%d_%H%M%S)"
    
    if [ -d "$REMOTE_DIR" ] && [ "$(ls -A $REMOTE_DIR 2>/dev/null)" ]; then
        echo "💾 Creando backup en $BACKUP_DIR..."
        sudo mkdir -p "$(dirname $BACKUP_DIR)"
        sudo cp -r "$REMOTE_DIR" "$BACKUP_DIR"
        echo "✅ Backup creado: $BACKUP_DIR"
        
        # Backup de BD también
        if [ -f "$REMOTE_DIR/.env" ]; then
            echo "💾 Creando backup de BD..."
            source "$REMOTE_DIR/.env" 2>/dev/null || true
            if [ -n "$DATABASE_URL" ]; then
                DB_BACKUP="/tmp/stvaldivia_db_backup_$(date +%Y%m%d_%H%M%S).sql"
                # Intentar hacer backup (puede fallar si no hay acceso)
                pg_dump "$DATABASE_URL" > "$DB_BACKUP" 2>/dev/null && \
                    echo "✅ Backup BD creado: $DB_BACKUP" || \
                    echo "⚠️  No se pudo hacer backup de BD (continuando...)"
            fi
        fi
    else
        echo "⚠️  No hay contenido para hacer backup"
    fi
ENDSSH

echo ""
echo "📋 PASO 3: Eliminando contenido actual..."
ssh "$SSH_HOST" "sudo rm -rf $REMOTE_DIR/* $REMOTE_DIR/.* 2>/dev/null || true"
echo -e "${GREEN}✅ Contenido eliminado${NC}"

echo ""
echo "📋 PASO 4: Clonando repositorio..."
ssh "$SSH_HOST" << ENDSSH
    set -e
    REMOTE_DIR="$REMOTE_DIR"
    REPO_URL="$REPO_URL"
    
    sudo mkdir -p "$REMOTE_DIR"
    sudo chown -R stvaldiviazal:stvaldiviazal "$REMOTE_DIR"
    
    cd "$(dirname $REMOTE_DIR)"
    git clone "$REPO_URL" "$(basename $REMOTE_DIR)" || {
        echo "⚠️  Clon falló, intentando pull si ya existe..."
        cd "$REMOTE_DIR"
        git pull origin main
    }
    
    cd "$REMOTE_DIR"
    git checkout main
    git pull origin main
ENDSSH
echo -e "${GREEN}✅ Código clonado${NC}"

echo ""
echo "📋 PASO 5: Restaurando .env desde backup..."
ssh "$SSH_HOST" << 'ENDSSH'
    set -e
    REMOTE_DIR="/var/www/stvaldivia"
    BACKUP_BASE="/tmp/stvaldivia_backup_"
    
    # Buscar el backup más reciente
    LATEST_BACKUP=$(ls -td ${BACKUP_BASE}* 2>/dev/null | head -1)
    
    if [ -n "$LATEST_BACKUP" ] && [ -f "$LATEST_BACKUP/.env" ]; then
        echo "📋 Restaurando .env desde backup..."
        cp "$LATEST_BACKUP/.env" "$REMOTE_DIR/.env"
        echo "✅ .env restaurado"
    else
        echo "⚠️  No se encontró .env en backup, necesitarás configurarlo manualmente"
    fi
ENDSSH

echo ""
echo "📋 PASO 6: Creando entorno virtual..."
ssh "$SSH_HOST" << 'ENDSSH'
    set -e
    REMOTE_DIR="/var/www/stvaldivia"
    
    cd "$REMOTE_DIR"
    
    if [ ! -d "venv" ]; then
        echo "🐍 Creando venv..."
        python3 -m venv venv
    fi
    
    echo "📦 Instalando dependencias..."
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
ENDSSH
echo -e "${GREEN}✅ Entorno virtual configurado${NC}"

echo ""
echo "📋 PASO 7: Ejecutando migraciones de BD..."
ssh "$SSH_HOST" << 'ENDSSH'
    set -e
    REMOTE_DIR="/var/www/stvaldivia"
    
    cd "$REMOTE_DIR"
    source venv/bin/activate
    
    # Ejecutar migraciones Flask-Migrate
    if [ -d "migrations" ]; then
        echo "🔄 Ejecutando migraciones Flask-Migrate..."
        export FLASK_APP=app
        flask db upgrade || echo "⚠️  Flask-Migrate no disponible o sin migraciones"
    fi
    
    # Ejecutar migraciones SQL directas
    if [ -d "migrations" ]; then
        echo "🔄 Ejecutando migraciones SQL..."
        for migration in migrations/*.sql; do
            if [ -f "$migration" ]; then
                echo "   Ejecutando: $(basename $migration)"
                # Intentar ejecutar con psql (puede fallar si no hay DATABASE_URL configurado)
                if [ -f ".env" ]; then
                    source .env 2>/dev/null || true
                    if [ -n "$DATABASE_URL" ]; then
                        psql "$DATABASE_URL" -f "$migration" 2>/dev/null && \
                            echo "   ✅ $(basename $migration)" || \
                            echo "   ⚠️  Error en $(basename $migration) (continuando...)"
                    fi
                fi
            fi
        done
    fi
ENDSSH

echo ""
echo "📋 PASO 8: Verificando y creando datos de prueba..."
ssh "$SSH_HOST" << 'ENDSSH'
    set -e
    REMOTE_DIR="/var/www/stvaldivia"
    
    cd "$REMOTE_DIR"
    source venv/bin/activate
    
    if [ -f "scripts/verify_and_seed_cajas.py" ]; then
        echo "📦 Verificando cajas de prueba..."
        python3 scripts/verify_and_seed_cajas.py || echo "⚠️  Error al verificar cajas (continuando...)"
    fi
ENDSSH

echo ""
echo "📋 PASO 9: Configurando permisos..."
ssh "$SSH_HOST" << 'ENDSSH'
    set -e
    REMOTE_DIR="/var/www/stvaldivia"
    
    # Crear directorio de logs si no existe
    sudo mkdir -p "$REMOTE_DIR/logs"
    sudo chown -R deploy:deploy "$REMOTE_DIR"
    sudo chmod -R 755 "$REMOTE_DIR"
    sudo chmod 600 "$REMOTE_DIR/.env" 2>/dev/null || true
ENDSSH
echo -e "${GREEN}✅ Permisos configurados${NC}"

echo ""
echo "📋 PASO 10: Reiniciando servicios..."
ssh "$SSH_HOST" << 'ENDSSH'
    set -e
    
    # Reiniciar gunicorn (si hay systemd service)
    if systemctl list-units --type=service --all | grep -q gunicorn; then
        echo "🔄 Reiniciando gunicorn..."
        sudo systemctl restart gunicorn || echo "⚠️  No se pudo reiniciar gunicorn (puede que no esté configurado)"
    else
        echo "⚠️  Servicio gunicorn no encontrado en systemd"
        echo "   Puede estar corriendo manualmente o con otro método"
    fi
    
    # Reiniciar nginx
    if systemctl list-units --type=service --all | grep -q nginx; then
        echo "🔄 Reiniciando nginx..."
        sudo systemctl restart nginx || echo "⚠️  Error al reiniciar nginx"
    fi
ENDSSH

echo ""
echo "📋 PASO 11: Verificando estado..."
ssh "$SSH_HOST" << 'ENDSSH'
    set -e
    REMOTE_DIR="/var/www/stvaldivia"
    
    echo "📊 Estado del proyecto:"
    cd "$REMOTE_DIR"
    echo "   Directorio: $(pwd)"
    echo "   Último commit: $(git log -1 --oneline 2>/dev/null || echo 'N/A')"
    echo "   Python: $(venv/bin/python3 --version 2>/dev/null || echo 'N/A')"
    
    echo ""
    echo "📊 Procesos gunicorn:"
    ps aux | grep gunicorn | grep -v grep | wc -l | xargs echo "   Procesos activos:"
    
    echo ""
    echo "📊 Servicios:"
    systemctl is-active nginx >/dev/null 2>&1 && echo "   ✅ nginx: activo" || echo "   ❌ nginx: inactivo"
    systemctl is-active gunicorn >/dev/null 2>&1 && echo "   ✅ gunicorn: activo" || echo "   ⚠️  gunicorn: no en systemd (puede estar corriendo manualmente)"
ENDSSH

echo ""
echo "=========================================="
echo -e "${GREEN}✅ DEPLOY COMPLETADO${NC}"
echo "=========================================="
echo ""
echo "📍 Proyecto desplegado en: $REMOTE_DIR"
echo "💾 Backup guardado en: $BACKUP_DIR"
echo ""
echo "🔍 Verificar:"
echo "   ssh $SSH_HOST 'cd $REMOTE_DIR && git log -1'"
echo "   ssh $SSH_HOST 'ps aux | grep gunicorn | grep -v grep'"
echo ""


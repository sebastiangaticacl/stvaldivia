#!/bin/bash
# Script completo de deploy a producción con actualización de código y migración

set -e

INSTANCE_NAME="stvaldivia"
ZONE="southamerica-west1-a"
PROJECT_ID="stvaldivia"
SSH_USER="stvaldiviazal"
REPO_URL="https://github.com/stvaldivia/stvaldivia.git"
PROJECT_DIR="/var/www/stvaldivia"

# Agregar gcloud al PATH si no está
export PATH="$HOME/google-cloud-sdk/bin:$PATH"

echo "🚀 DEPLOYMENT COMPLETO A PRODUCCIÓN"
echo "===================================="
echo "📍 Instancia: $INSTANCE_NAME"
echo "📍 Zona: $ZONE"
echo "👤 Usuario: $SSH_USER"
echo "📦 Repositorio: $REPO_URL"
echo ""

# Usar gcloud compute ssh que maneja las claves automáticamente
gcloud compute ssh "$SSH_USER@$INSTANCE_NAME" \
    --zone="$ZONE" \
    --project="$PROJECT_ID" \
    --command="bash -s" << 'ENDSSH'
set -e

REPO_URL="https://github.com/stvaldivia/stvaldivia.git"
PROJECT_DIR="/var/www/stvaldivia"

echo "📥 Clonando código desde GitHub..."
TMP_DIR="/tmp/stvaldivia_deploy_$(date +%s)"
rm -rf "$TMP_DIR"
git clone --depth 1 --branch main "$REPO_URL" "$TMP_DIR" || {
    echo "❌ Error al clonar repositorio"
    exit 1
}

echo "📋 Copiando archivos actualizados..."
sudo mkdir -p "$PROJECT_DIR"
sudo mkdir -p "$PROJECT_DIR/logs"
sudo chown -R deploy:deploy "$PROJECT_DIR"
sudo chmod -R 755 "$PROJECT_DIR"
sudo chmod -R 775 "$PROJECT_DIR/logs"

# Copiar archivos (preservando estructura)
sudo -u deploy rsync -av --delete \
    --exclude='.git' \
    --exclude='instance' \
    --exclude='logs' \
    --exclude='venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    "$TMP_DIR/" "$PROJECT_DIR/"

echo "✅ Código actualizado"

# Asegurar permisos de logs antes de cualquier operación
sudo chown -R deploy:deploy "$PROJECT_DIR/logs" 2>/dev/null || sudo mkdir -p "$PROJECT_DIR/logs" && sudo chown -R deploy:deploy "$PROJECT_DIR/logs"
sudo chmod -R 775 "$PROJECT_DIR/logs" 2>/dev/null || true

# Activar entorno virtual
cd "$PROJECT_DIR"
if [ -d venv ]; then
    # Asegurar permisos del venv
    sudo chown -R deploy:deploy venv/
    sudo chmod -R 755 venv/
    
    echo "✅ Entorno virtual encontrado"
    
    # Instalar dependencias como usuario deploy
    if [ -f requirements.txt ]; then
        echo "📦 Instalando/actualizando dependencias..."
        sudo -u deploy bash -c "cd '$PROJECT_DIR' && source venv/bin/activate && pip install -q -r requirements.txt" || echo "⚠️  Algunas dependencias no se pudieron instalar"
    fi
else
    echo "⚠️  Entorno virtual no encontrado"
fi

# Ejecutar migración de system_config
echo "🔄 Ejecutando migración de system_config..."
if [ -f migrate_system_config.py ]; then
    # Asegurar permisos de logs antes de ejecutar migración
    sudo chown -R deploy:deploy logs/ 2>/dev/null || true
    sudo chmod -R 775 logs/ 2>/dev/null || true
    
    python3 migrate_system_config.py || {
        echo "⚠️  Error en migración (continuando...)"
    }
else
    echo "⚠️  Script de migración no encontrado"
fi

# Ejecutar migración de email tracking
echo "🔄 Ejecutando migración de email tracking..."
if [ -f migrate_add_email_tracking.py ]; then
    python3 migrate_add_email_tracking.py || {
        echo "⚠️  Error en migración de email tracking (continuando...)"
    }
else
    echo "⚠️  Script de migración de email tracking no encontrado"
fi

# Reiniciar servicio
echo "🔄 Reiniciando servicio..."
if sudo systemctl is-active --quiet gunicorn.service; then
    sudo systemctl restart gunicorn.service && echo "✅ Gunicorn reiniciado (systemd)" || {
        echo "⚠️  No se pudo reiniciar con systemd, intentando método alternativo..."
        sudo pkill -f 'gunicorn.*app:create_app' || true
        sleep 2
        cd "$PROJECT_DIR"
        sudo -u deploy bash -c "cd '$PROJECT_DIR' && source venv/bin/activate && nohup gunicorn --pythonpath '$PROJECT_DIR' --bind 127.0.0.1:5001 --workers 4 --worker-class eventlet --timeout 30 --access-logfile '$PROJECT_DIR/logs/access.log' --error-logfile '$PROJECT_DIR/logs/error.log' --daemon app:create_app > /dev/null 2>&1 &"
        sleep 2
        if pgrep -f 'gunicorn.*app:create_app' > /dev/null; then
            echo "✅ Gunicorn iniciado manualmente"
        else
            echo "❌ Error al iniciar gunicorn"
            exit 1
        fi
    }
elif pgrep -f "gunicorn.*app:create_app" > /dev/null; then
    GUNICORN_PID=$(pgrep -f "gunicorn.*app:create_app" | head -1)
    if [ -n "$GUNICORN_PID" ]; then
        sudo kill -HUP "$GUNICORN_PID" 2>/dev/null && echo "✅ Gunicorn reiniciado (HUP signal)" || {
            echo "⚠️  No se pudo hacer HUP, reiniciando completamente..."
            sudo pkill -f 'gunicorn.*app:create_app' || true
            sleep 2
            cd "$PROJECT_DIR"
            sudo -u deploy bash -c "cd '$PROJECT_DIR' && source venv/bin/activate && nohup gunicorn --pythonpath '$PROJECT_DIR' --bind 127.0.0.1:5001 --workers 4 --worker-class eventlet --timeout 30 --access-logfile '$PROJECT_DIR/logs/access.log' --error-logfile '$PROJECT_DIR/logs/error.log' --daemon app:create_app > /dev/null 2>&1 &"
            sleep 2
            if pgrep -f 'gunicorn.*app:create_app' > /dev/null; then
                echo "✅ Gunicorn reiniciado"
            else
                echo "❌ Error al reiniciar gunicorn"
                exit 1
            fi
        }
    fi
else
    echo "⚠️  Gunicorn no está corriendo, iniciando..."
    cd "$PROJECT_DIR"
    sudo -u deploy bash -c "cd '$PROJECT_DIR' && source venv/bin/activate && nohup gunicorn --pythonpath '$PROJECT_DIR' --bind 127.0.0.1:5001 --workers 4 --worker-class eventlet --timeout 30 --access-logfile '$PROJECT_DIR/logs/access.log' --error-logfile '$PROJECT_DIR/logs/error.log' --daemon app:create_app > /dev/null 2>&1 &"
    sleep 2
    if pgrep -f 'gunicorn.*app:create_app' > /dev/null; then
        echo "✅ Gunicorn iniciado"
    else
        echo "❌ Error al iniciar gunicorn"
        exit 1
    fi
fi

# Limpiar directorio temporal
rm -rf "$TMP_DIR"

echo ""
echo "✅ DEPLOYMENT COMPLETADO"
ENDSSH
TMP_DIR="/tmp/stvaldivia_deploy_\$(date +%s)"
rm -rf "\$TMP_DIR"
git clone --depth 1 --branch main "$REPO_URL" "\$TMP_DIR" || {
    echo "❌ Error al clonar repositorio"
    exit 1
}

echo "📋 Copiando archivos actualizados..."
PROJECT_DIR="$PROJECT_DIR"
sudo mkdir -p "\$PROJECT_DIR"
sudo mkdir -p "\$PROJECT_DIR/logs"
sudo chown -R deploy:deploy "\$PROJECT_DIR"
sudo chmod -R 755 "\$PROJECT_DIR"
sudo chmod -R 775 "\$PROJECT_DIR/logs"

# Copiar archivos (preservando estructura)
sudo -u deploy rsync -av --delete \
    --exclude='.git' \
    --exclude='instance' \
    --exclude='logs' \
    --exclude='venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    "\$TMP_DIR/" "\$PROJECT_DIR/"

echo "✅ Código actualizado"

# Activar entorno virtual
cd "\$PROJECT_DIR"
if [ -d venv ]; then
    # Asegurar permisos del venv
    sudo chown -R deploy:deploy venv/
    sudo chmod -R 755 venv/
    
    source venv/bin/activate
    echo "✅ Entorno virtual activado"
    
    # Instalar dependencias si es necesario
    if [ -f requirements.txt ]; then
        echo "📦 Instalando/actualizando dependencias..."
        pip install -q -r requirements.txt || echo "⚠️  Algunas dependencias no se pudieron instalar"
    fi
else
    echo "⚠️  Entorno virtual no encontrado"
fi

# Ejecutar migración de system_config
echo "🔄 Ejecutando migración de system_config..."
if [ -f migrate_system_config.py ]; then
    # Asegurar permisos de logs antes de ejecutar migración
    sudo chown -R deploy:deploy logs/ 2>/dev/null || true
    sudo chmod -R 775 logs/ 2>/dev/null || true
    
    python3 migrate_system_config.py || {
        echo "⚠️  Error en migración (continuando...)"
    }
else
    echo "⚠️  Script de migración no encontrado"
fi

# Ejecutar migración de email tracking
echo "🔄 Ejecutando migración de email tracking..."
if [ -f migrate_add_email_tracking.py ]; then
    python3 migrate_add_email_tracking.py || {
        echo "⚠️  Error en migración de email tracking (continuando...)"
    }
else
    echo "⚠️  Script de migración de email tracking no encontrado"
fi

# Reiniciar servicio
echo "🔄 Reiniciando servicio..."
if sudo systemctl is-active --quiet gunicorn.service; then
    sudo systemctl restart gunicorn.service && echo "✅ Gunicorn reiniciado (systemd)" || {
        echo "⚠️  No se pudo reiniciar con systemd, intentando método alternativo..."
        sudo pkill -f 'gunicorn.*app:create_app' || true
        sleep 2
        cd "\$PROJECT_DIR"
        source venv/bin/activate
        nohup gunicorn --pythonpath "\$PROJECT_DIR" \
            --bind 127.0.0.1:5001 \
            --workers 4 \
            --worker-class eventlet \
            --timeout 30 \
            --access-logfile "\$PROJECT_DIR/logs/access.log" \
            --error-logfile "\$PROJECT_DIR/logs/error.log" \
            --daemon \
            app:create_app > /dev/null 2>&1 &
        sleep 2
        if pgrep -f 'gunicorn.*app:create_app' > /dev/null; then
            echo "✅ Gunicorn iniciado manualmente"
        else
            echo "❌ Error al iniciar gunicorn"
            exit 1
        fi
    }
elif pgrep -f "gunicorn.*app:create_app" > /dev/null; then
    GUNICORN_PID=\$(pgrep -f "gunicorn.*app:create_app" | head -1)
    if [ -n "\$GUNICORN_PID" ]; then
        sudo kill -HUP "\$GUNICORN_PID" 2>/dev/null && echo "✅ Gunicorn reiniciado (HUP signal)" || {
            echo "⚠️  No se pudo hacer HUP, reiniciando completamente..."
            sudo pkill -f 'gunicorn.*app:create_app' || true
            sleep 2
            cd "\$PROJECT_DIR"
            source venv/bin/activate
            nohup gunicorn --pythonpath "\$PROJECT_DIR" \
                --bind 127.0.0.1:5001 \
                --workers 4 \
                --worker-class eventlet \
                --timeout 30 \
                --access-logfile "\$PROJECT_DIR/logs/access.log" \
                --error-logfile "\$PROJECT_DIR/logs/error.log" \
                --daemon \
                app:create_app > /dev/null 2>&1 &
            sleep 2
            if pgrep -f 'gunicorn.*app:create_app' > /dev/null; then
                echo "✅ Gunicorn reiniciado"
            else
                echo "❌ Error al reiniciar gunicorn"
                exit 1
            fi
        }
    fi
else
    echo "⚠️  Gunicorn no está corriendo, iniciando..."
    cd "\$PROJECT_DIR"
    source venv/bin/activate
    nohup gunicorn --pythonpath "\$PROJECT_DIR" \
        --bind 127.0.0.1:5001 \
        --workers 4 \
        --worker-class eventlet \
        --timeout 30 \
        --access-logfile "\$PROJECT_DIR/logs/access.log" \
        --error-logfile "\$PROJECT_DIR/logs/error.log" \
        --daemon \
        app:create_app > /dev/null 2>&1 &
    sleep 2
    if pgrep -f 'gunicorn.*app:create_app' > /dev/null; then
        echo "✅ Gunicorn iniciado"
    else
        echo "❌ Error al iniciar gunicorn"
        exit 1
    fi
fi

# Limpiar directorio temporal
rm -rf "\$TMP_DIR"

echo ""
echo "✅ DEPLOYMENT COMPLETADO"
ENDSSH

VM_IP="34.176.144.166"

echo ""
echo "✅ DEPLOYMENT COMPLETADO"
echo "📍 URL: http://$VM_IP"
echo ""
echo "💡 Próximos pasos:"
echo "   1. Verificar que el sitio funciona: http://$VM_IP"
echo "   2. Acceder al panel de control: http://$VM_IP/admin/panel_control"
echo "   3. Verificar que el toggle de base de datos aparece (solo superadmin)"



#!/bin/bash
set -e

echo "🚀 DEPLOYMENT COMPLETO - Borrando VM y subiendo versión local"
echo "============================================================"

VM_USER="stvaldiviazal"
VM_IP="34.176.144.166"
VM_DIR="/var/www/stvaldivia"
SSH_KEY="$HOME/.ssh/id_ed25519_gcp"

# Verificar que existe la clave SSH
if [ ! -f "$SSH_KEY" ]; then
    echo "❌ Error: No se encuentra la clave SSH: $SSH_KEY"
    exit 1
fi

echo ""
echo "📦 Paso 1: Haciendo backup de la VM actual..."
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$VM_USER@$VM_IP" "
    cd $VM_DIR 2>/dev/null || exit 0
    if [ -d . ]; then
        BACKUP_DIR=\"/tmp/stvaldivia_backup_\$(date +%Y%m%d_%H%M%S)\"
        echo '💾 Creando backup en: '\$BACKUP_DIR
        sudo -u deploy mkdir -p \$BACKUP_DIR
        sudo -u deploy cp -r . \$BACKUP_DIR/ 2>/dev/null || true
        echo '✅ Backup creado'
    fi
" || echo "⚠️  No se pudo hacer backup (continuando...)"

echo ""
echo "🗑️  Paso 2: Eliminando código actual en la VM..."
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$VM_USER@$VM_IP" "
    # Detener servicios
    echo '🛑 Deteniendo servicios...'
    sudo pkill -f 'gunicorn.*app:create_app' 2>/dev/null || true
    sleep 2
    
    # Eliminar directorio (excepto backups y logs importantes)
    if [ -d $VM_DIR ]; then
        echo '🗑️  Eliminando directorio...'
        sudo rm -rf $VM_DIR/*
        sudo rm -rf $VM_DIR/.* 2>/dev/null || true
        echo '✅ Directorio limpiado'
    else
        echo '📁 Creando directorio...'
        sudo mkdir -p $VM_DIR
        sudo chown -R deploy:deploy $VM_DIR
    fi
"

echo ""
echo "📤 Paso 3: Subiendo código local completo..."
# Excluir archivos innecesarios
rsync -avz --progress \
    -e "ssh -i $SSH_KEY -o StrictHostKeyChecking=no" \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.env' \
    --exclude='instance/*.db' \
    --exclude='instance/*.db-journal' \
    --exclude='.pytest_cache' \
    --exclude='node_modules' \
    --exclude='.DS_Store' \
    ./ "$VM_USER@$VM_IP:$VM_DIR/"

echo ""
echo "⚙️  Paso 4: Configurando entorno en la VM..."
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$VM_USER@$VM_IP" "
    cd $VM_DIR
    
    # Crear venv si no existe
    if [ ! -d venv ]; then
        echo '📦 Creando entorno virtual...'
        python3 -m venv venv
    fi
    
    # Activar venv e instalar dependencias
    echo '📦 Instalando dependencias...'
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    
    # Crear directorio instance si no existe
    sudo -u deploy mkdir -p instance
    sudo -u deploy chmod 700 instance
    
    # Copiar .env si existe en la VM (mantener configuración de producción)
    if [ ! -f .env ]; then
        echo '⚠️  No se encontró .env en la VM'
    fi
    
    echo '✅ Entorno configurado'
"

echo ""
echo "🔧 Paso 5: Configurando servicios..."
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$VM_USER@$VM_IP" "
    cd $VM_DIR
    
    # Asegurar permisos correctos
    sudo chown -R deploy:deploy .
    sudo -u deploy chmod -R u+rwX,go-w .
    
    echo '✅ Permisos configurados'
"

echo ""
echo "🚀 Paso 6: Iniciando servicios..."
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$VM_USER@$VM_IP" "
    cd $VM_DIR
    source venv/bin/activate
    
    # Iniciar gunicorn en background
    echo '🚀 Iniciando gunicorn...'
    nohup gunicorn --bind 127.0.0.1:5001 --workers 2 --timeout 120 --access-logfile /var/www/stvaldivia/logs/access.log --error-logfile /var/www/stvaldivia/logs/error.log app:create_app > /var/www/stvaldivia/logs/gunicorn.log 2>&1 &
    
    sleep 3
    
    # Verificar que está corriendo
    if pgrep -f 'gunicorn.*app:create_app' > /dev/null; then
        echo '✅ Gunicorn iniciado correctamente'
    else
        echo '❌ Error: Gunicorn no se inició'
        exit 1
    fi
"

echo ""
echo "✅ DEPLOYMENT COMPLETO FINALIZADO"
echo "=================================="
echo "Verifica que todo funcione en: https://stvaldivia.cl"





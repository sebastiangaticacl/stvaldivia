#!/bin/bash
set -e

echo "🚀 CONFIGURANDO PRODUCCIÓN INDEPENDIENTE"
echo "=========================================="

VM_USER="stvaldiviazal"
VM_IP="34.176.144.166"
SSH_KEY="$HOME/.ssh/id_ed25519_gcp"

echo ""
echo "📋 Paso 1: Verificando PostgreSQL..."
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$VM_USER@$VM_IP" "
    if ! command -v psql &> /dev/null; then
        echo '📦 Instalando PostgreSQL...'
        sudo apt-get update -qq
        sudo apt-get install -y postgresql postgresql-contrib
        sudo systemctl start postgresql
        sudo systemctl enable postgresql
        echo '✅ PostgreSQL instalado'
    else
        echo '✅ PostgreSQL ya está instalado'
        sudo systemctl start postgresql || true
    fi
"

echo ""
echo "📋 Paso 2: Configurando base de datos..."
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$VM_USER@$VM_IP" "
    sudo -u postgres psql << 'SQL'
-- Crear base de datos si no existe
SELECT 'CREATE DATABASE bimba'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'bimba')\\gexec

-- Crear usuario si no existe
DO \\$\\$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_user WHERE usename = 'bimba_user') THEN
        CREATE USER bimba_user WITH PASSWORD '<PASSWORD>';
    END IF;
END
\\$\\$;

-- Dar permisos
GRANT ALL PRIVILEGES ON DATABASE bimba TO bimba_user;
ALTER DATABASE bimba OWNER TO bimba_user;
SQL
    echo '✅ Base de datos configurada'
"

echo ""
echo "📋 Paso 3: Actualizando .env..."
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$VM_USER@$VM_IP" "
    cd /var/www/stvaldivia
    # Backup del .env actual
    cp .env .env.backup.\$(date +%Y%m%d_%H%M%S)
    
    # Actualizar DATABASE_URL
    if grep -q 'DATABASE_URL' .env; then
        sed -i 's|DATABASE_URL=.*|DATABASE_URL=postgresql://bimba_user:<PASSWORD>@localhost:5432/bimba|' .env
    else
        echo 'DATABASE_URL=postgresql://bimba_user:<PASSWORD>@localhost:5432/bimba' >> .env
    fi
    
    echo '✅ .env actualizado'
    grep DATABASE_URL .env
"

echo ""
echo "📋 Paso 4: Iniciando gunicorn..."
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$VM_USER@$VM_IP" "
    cd /var/www/stvaldivia
    sudo pkill -f gunicorn 2>/dev/null || true
    sleep 2
    
    sudo -u deploy bash -c '
        cd /var/www/stvaldivia
        source venv/bin/activate
        nohup gunicorn \\
            --pythonpath /var/www/stvaldivia \\
            --bind 127.0.0.1:5001 \\
            --workers 4 \\
            --worker-class eventlet \\
            --timeout 30 \\
            --access-logfile /var/www/stvaldivia/logs/access.log \\
            --error-logfile /var/www/stvaldivia/logs/error.log \\
            app:create_app\(\) \\
            > /var/www/stvaldivia/logs/gunicorn.log 2>&1 &
    '
    
    sleep 3
    if ps aux | grep '[g]unicorn' > /dev/null; then
        echo '✅ Gunicorn iniciado'
        ps aux | grep '[g]unicorn' | head -2
    else
        echo '❌ Error iniciando gunicorn'
        tail -30 /var/www/stvaldivia/logs/gunicorn.log
    fi
"

echo ""
echo "✅ CONFIGURACIÓN COMPLETADA"
echo "La instancia de producción ahora es independiente con PostgreSQL local"


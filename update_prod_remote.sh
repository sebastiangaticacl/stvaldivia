#!/bin/bash
# Script que se ejecuta en la VM para actualizar código desde GitHub

cd /var/www/stvaldivia

echo "📥 Actualizando desde GitHub..."
sudo -u deploy git clone https://github.com/stvaldivia/stvaldivia.git /tmp/stvaldivia_update || true

if [ -d /tmp/stvaldivia_update ]; then
    echo "📋 Copiando archivos actualizados..."
    sudo -u deploy cp -r /tmp/stvaldivia_update/app/* app/
    
    echo "🔄 Reiniciando gunicorn..."
    sudo pkill -f 'gunicorn.*app:create_app' || true
    sleep 3
    
    cd /var/www/stvaldivia
    sudo -u deploy bash -c "source venv/bin/activate && gunicorn --pythonpath /var/www/stvaldivia --bind 127.0.0.1:5001 --workers 4 --worker-class eventlet --timeout 30 --access-logfile /var/www/stvaldivia/logs/access.log --error-logfile /var/www/stvaldivia/logs/error.log --daemon app:create_app"
    
    echo "✅ Actualización completada"
    rm -rf /tmp/stvaldivia_update
else
    echo "❌ Error al clonar repositorio"
    exit 1
fi




#!/bin/bash
set -e

echo "🔧 CREANDO SERVICIO SYSTEMD PARA GUNICORN"
echo "=========================================="

VM_USER="stvaldiviazal"
VM_IP="34.176.144.166"
SSH_KEY="$HOME/.ssh/id_ed25519_gcp"

ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$VM_USER@$VM_IP" "sudo bash << 'SYSTEMD'
cat > /etc/systemd/system/stvaldivia.service << 'SERVICE'
[Unit]
Description=StValdivia BIMBA Application
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=notify
User=deploy
Group=deploy
WorkingDirectory=/var/www/stvaldivia
Environment=\"PATH=/var/www/stvaldivia/venv/bin:/usr/local/bin:/usr/bin:/bin\"
Environment=\"PYTHONPATH=/var/www/stvaldivia\"
ExecStart=/var/www/stvaldivia/venv/bin/gunicorn \\
    --pythonpath /var/www/stvaldivia \\
    --bind 127.0.0.1:5001 \\
    --workers 4 \\
    --worker-class eventlet \\
    --timeout 30 \\
    --access-logfile /var/www/stvaldivia/logs/access.log \\
    --error-logfile /var/www/stvaldivia/logs/error.log \\
    app:create_app
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SERVICE

systemctl daemon-reload
systemctl enable stvaldivia.service
systemctl restart stvaldivia.service
sleep 3
systemctl status stvaldivia.service --no-pager | head -15
SYSTEMD
" 2>&1

echo ""
echo "✅ Servicio systemd creado y iniciado"

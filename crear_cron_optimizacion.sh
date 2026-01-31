#!/bin/bash
# Script para crear tareas cron de optimización de BD

VM_USER="stvaldiviazal"
VM_IP="34.176.144.166"
SSH_KEY="$HOME/.ssh/id_ed25519_gcp"

ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$VM_USER@$VM_IP" "sudo -u deploy bash << 'CRON'
# Crear script de limpieza de caché
cat > /var/www/stvaldivia/scripts/clean_cache.sh << 'SCRIPT'
#!/bin/bash
sudo -u postgres psql -d bimba -c \"SELECT clean_expired_cache();\"
SCRIPT

chmod +x /var/www/stvaldivia/scripts/clean_cache.sh

# Crear script de actualización de métricas
cat > /var/www/stvaldivia/scripts/update_metrics.sh << 'SCRIPT'
#!/bin/bash
YESTERDAY=\$(date -d 'yesterday' +%Y-%m-%d)
sudo -u postgres psql -d bimba -c \"SELECT update_daily_metrics('\$YESTERDAY'::DATE);\"
SCRIPT

chmod +x /var/www/stvaldivia/scripts/update_metrics.sh

# Agregar a crontab (limpiar caché cada hora, actualizar métricas diariamente)
(crontab -l 2>/dev/null | grep -v clean_cache.sh | grep -v update_metrics.sh; echo '0 * * * * /var/www/stvaldivia/scripts/clean_cache.sh >> /var/www/stvaldivia/logs/cron.log 2>&1'; echo '0 1 * * * /var/www/stvaldivia/scripts/update_metrics.sh >> /var/www/stvaldivia/logs/cron.log 2>&1') | crontab -

echo '✅ Tareas cron configuradas'
crontab -l
CRON
" 2>&1

echo "✅ Script de cron creado"
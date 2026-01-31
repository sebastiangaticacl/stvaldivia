#!/bin/bash
# Script para configurar variables de entorno SumUp en producción
# Uso: ./configurar_sumup_produccion.sh

set -e

VM_USER="stvaldiviazal"
VM_IP="34.176.144.166"
SSH_KEY="$HOME/.ssh/id_ed25519_gcp"

# Variables de SumUp
SUMUP_API_KEY="sup_sk_Tzj0qRj01rcmdYN8YpK2bLIkdRWahvWQI"
PUBLIC_BASE_URL="https://stvaldivia.cl"
SUMUP_MERCHANT_CODE=""  # Opcional, dejar vacío si no se tiene

echo "🔧 CONFIGURANDO SUMUP EN PRODUCCIÓN"
echo "===================================="
echo ""
echo "Variables a configurar:"
echo "  SUMUP_API_KEY: ${SUMUP_API_KEY:0:20}..."
echo "  PUBLIC_BASE_URL: $PUBLIC_BASE_URL"
if [ -n "$SUMUP_MERCHANT_CODE" ]; then
    echo "  SUMUP_MERCHANT_CODE: $SUMUP_MERCHANT_CODE"
fi
echo ""

ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$VM_USER@$VM_IP" "sudo bash << 'CONFIG_SUMUP'
set -e

SERVICE_FILE=\"/etc/systemd/system/stvaldivia.service\"
BACKUP_FILE=\"\${SERVICE_FILE}.backup.\$(date +%Y%m%d_%H%M%S)\"

echo '📋 Creando backup del servicio...'
cp \"\$SERVICE_FILE\" \"\$BACKUP_FILE\"
echo \"✅ Backup creado: \$BACKUP_FILE\"
echo ''

echo '📝 Actualizando servicio systemd...'

# Leer el archivo actual y agregar variables de entorno
python3 << 'PYTHON_SCRIPT'
import sys
import re

service_file = '/etc/systemd/system/stvaldivia.service'
backup_file = service_file + '.backup.' + __import__('datetime').datetime.now().strftime('%Y%m%d_%H%M%S')

# Variables a agregar
sumup_api_key = 'sup_sk_Tzj0qRj01rcmdYN8YpK2bLIkdRWahvWQI'
public_base_url = 'https://stvaldivia.cl'
sumup_merchant_code = ''

# Leer archivo
with open(service_file, 'r') as f:
    content = f.read()

# Verificar si las variables ya existen
has_sumup_key = 'Environment=\"SUMUP_API_KEY=' in content or \"Environment='SUMUP_API_KEY=\" in content
has_public_url = 'Environment=\"PUBLIC_BASE_URL=' in content or \"Environment='PUBLIC_BASE_URL=\" in content
has_merchant_code = sumup_merchant_code and ('Environment=\"SUMUP_MERCHANT_CODE=' in content or \"Environment='SUMUP_MERCHANT_CODE=\" in content)

# Si ya existen, actualizar. Si no, agregar
new_env_lines = []

if not has_sumup_key:
    new_env_lines.append(f'Environment=\"SUMUP_API_KEY={sumup_api_key}\"')
elif 'SUMUP_API_KEY=' in content:
    # Actualizar existente
    content = re.sub(r'Environment=[\"\'].*SUMUP_API_KEY=.*[\"\']', f'Environment=\"SUMUP_API_KEY={sumup_api_key}\"', content)

if not has_public_url:
    new_env_lines.append(f'Environment=\"PUBLIC_BASE_URL={public_base_url}\"')
elif 'PUBLIC_BASE_URL=' in content:
    content = re.sub(r'Environment=[\"\'].*PUBLIC_BASE_URL=.*[\"\']', f'Environment=\"PUBLIC_BASE_URL={public_base_url}\"', content)

if sumup_merchant_code and not has_merchant_code:
    new_env_lines.append(f'Environment=\"SUMUP_MERCHANT_CODE={sumup_merchant_code}\"')

# Si hay nuevas líneas, agregarlas después de la sección [Service] o después de otras líneas Environment
if new_env_lines:
    # Buscar la sección [Service] y agregar después de otras líneas Environment
    lines = content.split('\n')
    new_lines = []
    service_section = False
    env_added = False
    
    for line in lines:
        new_lines.append(line)
        if line.strip() == '[Service]':
            service_section = True
        elif service_section and line.strip().startswith('Environment='):
            # Si encontramos una línea Environment, agregar las nuevas después
            if not env_added:
                for env_line in new_env_lines:
                    new_lines.append(env_line)
                env_added = True
        elif service_section and (line.strip().startswith('ExecStart=') or line.strip().startswith('User=') or line.strip().startswith('WorkingDirectory=')):
            # Si llegamos a otras secciones antes de encontrar Environment, agregar antes
            if not env_added:
                for env_line in reversed(new_env_lines):
                    new_lines.insert(-1, env_line)
                env_added = True
    
    # Si no se agregaron, agregar después de [Service]
    if not env_added and service_section:
        for env_line in new_env_lines:
            new_lines.insert(1, env_line)
    
    content = '\n'.join(new_lines)

# Escribir archivo actualizado
with open(service_file, 'w') as f:
    f.write(content)

print('✅ Servicio actualizado')
PYTHON_SCRIPT

echo ''
echo '🔄 Recargando systemd...'
systemctl daemon-reload

echo ''
echo '🔄 Reiniciando servicio...'
systemctl restart stvaldivia.service

echo ''
echo '⏳ Esperando inicio del servicio...'
sleep 3

echo ''
echo '📊 Estado del servicio:'
systemctl status stvaldivia.service --no-pager | head -20

echo ''
echo '✅ CONFIGURACIÓN COMPLETADA'
echo ''
echo 'Verificar variables configuradas:'
systemctl show stvaldivia.service --property=Environment --no-pager | grep -i sumup || echo '  (ejecutar: sudo systemctl show stvaldivia.service --property=Environment)'

CONFIG_SUMUP
"

echo ""
echo "✅ Script completado"
echo ""
echo "📋 Verificación:"
echo "   Para ver las variables configuradas:"
echo "   ssh stvaldivia 'sudo systemctl show stvaldivia.service --property=Environment'"


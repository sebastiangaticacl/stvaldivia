#!/bin/bash
# Deployment final usando gcloud compute ssh (maneja claves automáticamente)

set -e

INSTANCE_NAME="stvaldivia"
ZONE="southamerica-west1-a"
PROJECT_ID="stvaldivia"
VM_IP="34.176.144.166"

echo "🚀 DEPLOYMENT FINAL A VM"
echo "========================"
echo "📍 IP: $VM_IP"
echo ""

# Intentar con gcloud compute ssh primero (si está autenticado)
if gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q . 2>/dev/null; then
    echo "✅ Usando gcloud compute ssh..."
    gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --project=$PROJECT_ID --command="
        set -e
        echo '🔄 Actualizando código...'
        cd ~/tickets_cursor_clean || cd ~/tickets || cd ~/app || { echo '❌ Directorio no encontrado'; exit 1; }
        echo '✅ Directorio: $(pwd)'
        if [ -d .git ]; then git pull origin main || git pull origin master || true; fi
        if [ -d venv ]; then source venv/bin/activate; fi
        if [ -f requirements.txt ]; then pip install -q -r requirements.txt || true; fi
        echo '🔄 Reiniciando servicio...'
        if systemctl is-active --quiet bimba.service 2>/dev/null; then
            sudo systemctl restart bimba.service && echo '✅ systemd reiniciado'
        elif command -v supervisorctl &>/dev/null && supervisorctl status bimba &>/dev/null 2>/dev/null; then
            sudo supervisorctl restart bimba && echo '✅ supervisor reiniciado'
        elif command -v pm2 &>/dev/null && pm2 list | grep -q bimba; then
            pm2 restart bimba && echo '✅ PM2 reiniciado'
        elif screen -list 2>/dev/null | grep -q bimba; then
            screen -S bimba -X stuff '^C' && sleep 2 && screen -S bimba -X stuff 'python3 run_local.py\n' && echo '✅ screen reiniciado'
        else
            echo '⚠️  Servicio no encontrado. Busca con: ps aux | grep python'
        fi
        echo '✅ Deploy completado'
    "
else
    echo "⚠️  gcloud no está autenticado"
    echo "Ejecuta primero: gcloud auth login"
    echo ""
    echo "O usa SSH directo con clave configurada:"
    echo "  ssh stvaldiviazal@$VM_IP"
    exit 1
fi

echo ""
echo "✅ DEPLOYMENT COMPLETADO"
echo "📍 Verifica: http://$VM_IP:5001"
echo ""

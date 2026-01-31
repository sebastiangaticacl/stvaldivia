# 🚀 COMANDOS PARA DEPLOYMENT MANUAL

## Paso 1: Autenticarse
```bash
gcloud auth login
```
(Se abrirá el navegador para autenticarte)

## Paso 2: Ejecutar el script de deployment
```bash
./deploy_manual.sh
```

## O ejecutar comandos manualmente:

### Conectar por SSH:
```bash
gcloud compute ssh --zone "southamerica-west1-a" "stvaldivia" --project "stvaldivia"
```

### Una vez dentro de la VM, ejecutar:
```bash
# Navegar al directorio
cd ~/tickets_cursor_clean || cd ~/tickets || cd ~/app

# Hacer pull (si usas git)
git pull origin main || git pull origin master

# Activar entorno virtual
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Reiniciar servicio (elige el método que uses):
# Opción 1: systemd
sudo systemctl restart bimba.service

# Opción 2: supervisor
sudo supervisorctl restart bimba

# Opción 3: PM2
pm2 restart bimba

# Opción 4: screen
screen -S bimba -X stuff '^C'
sleep 2
screen -S bimba -X stuff 'python3 run_local.py\n'
```






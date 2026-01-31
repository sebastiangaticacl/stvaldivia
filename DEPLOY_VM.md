# 🚀 DEPLOY EN VM DE GOOGLE COMPUTE ENGINE

## ⚡ USO RÁPIDO

```bash
# Opción 1: Usar valores por defecto
./deploy_vm.sh

# Opción 2: Especificar instancia, zona y proyecto
./deploy_vm.sh bimba-vm southamerica-west1-a stvaldiviacl
```

## 📋 QUÉ HACE EL SCRIPT

1. ✅ Verifica autenticación en Google Cloud
2. ✅ Configura el proyecto
3. ✅ Verifica que la instancia existe
4. ✅ Obtiene la IP externa
5. ✅ Se conecta por SSH a la VM
6. ✅ Hace pull del código (si usa git)
7. ✅ Instala/actualiza dependencias
8. ✅ Reinicia el servicio (systemd/supervisor/PM2/screen)

## ⚙️ CONFIGURACIÓN

Antes de ejecutar, ajusta estos valores en el script si es necesario:

- **INSTANCE_NAME**: Nombre de tu instancia VM (default: `bimba-vm`)
- **ZONE**: Zona de la VM (default: `southamerica-west1-a`)
- **PROJECT_ID**: ID del proyecto (default: `stvaldiviacl`)
- **Directorio del proyecto**: El script busca en `~/tickets_cursor_clean`, `~/tickets`, o `~/app`

## 🔧 REQUISITOS

1. **Autenticación en Google Cloud:**
   ```bash
   gcloud auth login
   ```

2. **Permisos SSH en la VM:**
   - La VM debe tener firewall abierto para SSH (puerto 22)
   - Tu cuenta debe tener permisos de Compute Instance Admin o Editor

3. **Estructura en la VM:**
   - El código debe estar en uno de estos directorios:
     - `~/tickets_cursor_clean`
     - `~/tickets`
     - `~/app`
   - O ajusta el script con tu ruta

## 🔍 VERIFICAR INSTANCIA

Para ver todas las instancias disponibles:

```bash
gcloud compute instances list --project=stvaldiviacl
```

## 🛠️ REINICIO MANUAL (si el script no encuentra el servicio)

Si el script no encuentra tu servicio, puedes reiniciarlo manualmente:

### Opción 1: SSH directo
```bash
gcloud compute ssh bimba-vm --zone=southamerica-west1-a --project=stvaldiviacl
```

Luego dentro de la VM:
```bash
cd ~/tickets_cursor_clean
git pull
source venv/bin/activate  # si usas venv
pip install -r requirements.txt
# Reiniciar según tu método:
sudo systemctl restart bimba.service
# O
sudo supervisorctl restart bimba
# O
pm2 restart bimba
# O
screen -S bimba -X stuff '^C'
screen -S bimba -X stuff 'python3 run_local.py\n'
```

### Opción 2: Reiniciar la VM completa
```bash
gcloud compute instances reset bimba-vm --zone=southamerica-west1-a --project=stvaldiviacl
```

## 📊 VERIFICAR DEPLOY

Después del deploy, verifica que el servicio está funcionando:

```bash
# Obtener IP externa
EXTERNAL_IP=$(gcloud compute instances describe bimba-vm --zone=southamerica-west1-a --project=stvaldiviacl --format="get(networkInterfaces[0].accessConfigs[0].natIP)")

# Probar endpoint
curl http://$EXTERNAL_IP:5001/
```

## 🔍 VER LOGS

Para ver logs del servicio en la VM:

```bash
gcloud compute ssh bimba-vm --zone=southamerica-west1-a --project=stvaldiviacl

# Luego dentro de la VM:
sudo journalctl -u bimba.service -f  # si usas systemd
# O
sudo supervisorctl tail -f bimba  # si usas supervisor
# O
pm2 logs bimba  # si usas PM2
```

## ⚠️ NOTAS IMPORTANTES

- El script asume que el servicio corre en el puerto **5001**
- Si usas otro puerto, ajusta el script
- El script intenta detectar automáticamente el método de servicio (systemd/supervisor/PM2/screen)
- Si no encuentra ninguno, te mostrará un mensaje para reiniciar manualmente










# Instrucciones para Conectarse a la VM

## Prerrequisitos

1. Tener `gcloud` instalado y configurado
2. Tener permisos de acceso al proyecto `stvaldivia`

## Configuración Inicial (Una vez)

```bash
# Configurar proyecto y zona
gcloud config set project stvaldivia
gcloud config set compute/zone southamerica-west1-a
```

## Conectarse a la VM

### Opción 1: Conexión SSH Directa

```bash
gcloud compute ssh stvaldivia --zone=southamerica-west1-a
```

### Opción 2: Con ruta completa

```bash
gcloud compute ssh stvaldivia \
  --project=stvaldivia \
  --zone=southamerica-west1-a
```

### Opción 3: Con túnel IAP (si hay problemas de red)

```bash
gcloud compute ssh stvaldivia \
  --zone=southamerica-west1-a \
  --tunnel-through-iap
```

## Ejecutar Comandos sin Conectarse Interactivamente

### Ejecutar un comando simple

```bash
gcloud compute ssh stvaldivia --zone=southamerica-west1-a --command "comando_aqui"
```

### Ejecutar múltiples comandos

```bash
gcloud compute ssh stvaldivia --zone=southamerica-west1-a --command "
  cd /var/www/stvaldivia
  ls -la
  sudo systemctl status stvaldivia
"
```

### Ejecutar un script en la VM

```bash
gcloud compute ssh stvaldivia --zone=southamerica-west1-a --command "bash -s" < mi_script.sh
```

## Verificar Conexión

```bash
# Verificar que puedes conectarte
gcloud compute ssh stvaldivia --zone=southamerica-west1-a --command "whoami && hostname"

# Verificar estado de servicios
gcloud compute ssh stvaldivia --zone=southamerica-west1-a --command "
  sudo systemctl status stvaldivia
  sudo systemctl status cloud-sql-proxy
"
```

## Comandos Útiles

### Ver logs de la aplicación

```bash
gcloud compute ssh stvaldivia --zone=southamerica-west1-a --command "
  sudo tail -50 /var/www/stvaldivia/logs/error.log
"
```

### Ver logs del proxy Cloud SQL

```bash
gcloud compute ssh stvaldivia --zone=southamerica-west1-a --command "
  sudo journalctl -u cloud-sql-proxy -n 50 --no-pager
"
```

### Reiniciar servicios

```bash
gcloud compute ssh stvaldivia --zone=southamerica-west1-a --command "
  sudo systemctl restart stvaldivia
  sudo systemctl restart cloud-sql-proxy
"
```

### Verificar base de datos

```bash
gcloud compute ssh stvaldivia --zone=southamerica-west1-a --command "
  cd /var/www/stvaldivia
  sudo -u deploy /var/www/stvaldivia/venv/bin/python3 -c '
    from app import create_app
    from app.models import db
    app = create_app()
    with app.app_context():
        print(\"BD:\", str(db.engine.url))
  '
"
```

## Copiar Archivos

### De local a VM

```bash
gcloud compute scp archivo_local stvaldivia:/ruta/destino --zone=southamerica-west1-a
```

### De VM a local

```bash
gcloud compute scp stvaldivia:/ruta/origen archivo_local --zone=southamerica-west1-a
```

### Ejemplo: Copiar script de migración

```bash
gcloud compute scp migrate_sqlite_to_cloudsql_postgres.sh \
  stvaldivia:/tmp/ \
  --zone=southamerica-west1-a
```

## Solución de Problemas

### Si falla la conexión SSH

```bash
# Verificar que la VM está corriendo
gcloud compute instances describe stvaldivia --zone=southamerica-west1-a

# Verificar firewall
gcloud compute firewall-rules list | grep ssh

# Usar IAP tunnel
gcloud compute ssh stvaldivia --zone=southamerica-west1-a --tunnel-through-iap
```

### Si necesitas permisos sudo

```bash
# Los comandos con sudo funcionan normalmente
gcloud compute ssh stvaldivia --zone=southamerica-west1-a --command "sudo comando"
```

## Variables de Entorno Útiles

```bash
# Agregar al ~/.bashrc o ~/.zshrc
export PATH="$HOME/google-cloud-sdk/bin:$PATH"
export PROJECT_ID="stvaldivia"
export ZONE="southamerica-west1-a"
export VM_NAME="stvaldivia"
```

## Atajos Rápidos

```bash
# Crear alias en ~/.bashrc o ~/.zshrc
alias vm-ssh='gcloud compute ssh stvaldivia --zone=southamerica-west1-a'
alias vm-cmd='gcloud compute ssh stvaldivia --zone=southamerica-west1-a --command'

# Uso:
vm-ssh
vm-cmd "sudo systemctl status stvaldivia"
```


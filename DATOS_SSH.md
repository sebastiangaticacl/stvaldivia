# 🔐 Datos de Conexión SSH - stvaldivia.cl

## 📍 Información del Servidor

- **IP Pública:** `34.176.144.166`
- **Hostname:** `stvaldivia.cl`
- **Usuario SSH:** `stvaldiviazal` ⚠️ (NO `sebagatica`)
- **Instancia GCP:** `stvaldivia`
- **Zona GCP:** `southamerica-west1-a`
- **Proyecto GCP:** `stvaldivia`

## 🔑 Conexión SSH

### Comando básico:
```bash
ssh -i ~/.ssh/id_ed25519_gcp stvaldiviazal@34.176.144.166
```

### O usando el alias (después de configurar):
```bash
ssh stvaldivia
```

## 📁 Ubicación del Proyecto

Una vez conectado, el proyecto está en:
```bash
cd /var/www/stvaldivia
```

## 🔐 Clave SSH

**Ubicación de la clave privada:**
```bash
~/.ssh/id_ed25519_gcp
```

**Clave pública (ya agregada al servidor):**
```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIIW0Kze09D1j1pIa/67DKc4ztmNJW+ae2hHpVQKRVSXS sebagatica@gcp
```

## 🚀 Comandos Útiles

### Conectar y ver estado:
```bash
ssh stvaldivia "cd /var/www/stvaldivia && git status"
```

### Ver logs del servicio:
```bash
ssh stvaldivia "sudo journalctl -u gunicorn -n 50"
```

### Reiniciar servicios:
```bash
ssh stvaldivia "sudo systemctl restart gunicorn nginx"
```

### Ejecutar script de comparación:
```bash
ssh stvaldivia "cd /var/www/stvaldivia && python3 scripts/compare_db_simple.py"
```

## 📋 Configurar SSH en tu máquina local

Si no tienes la clave configurada, agrega esto a `~/.ssh/config`:

```
Host stvaldivia
    HostName 34.176.144.166
    User stvaldiviazal
    IdentityFile ~/.ssh/id_ed25519_gcp
    StrictHostKeyChecking no
```

Luego puedes conectar simplemente con:
```bash
ssh stvaldivia
```

## 🔍 Verificar Conexión

```bash
# Probar conexión (con alias configurado)
ssh stvaldivia "echo '✅ SSH funciona correctamente'"

# O sin alias
ssh -i ~/.ssh/id_ed25519_gcp stvaldiviazal@34.176.144.166 "echo '✅ SSH funciona correctamente'"
```

## 📝 Notas

- ✅ **Usuario correcto:** `stvaldiviazal` (NO `sebagatica`)
- ✅ La clave SSH ya está configurada en el servidor
- El usuario `stvaldiviazal` tiene permisos sudo
- El proyecto está en `/var/www/stvaldivia`
- Los servicios se gestionan con `systemctl` (gunicorn, nginx)

## 🆘 Si no puedes conectar

1. Verificar que la clave existe:
   ```bash
   ls -la ~/.ssh/id_ed25519_gcp
   ```

2. Verificar permisos de la clave:
   ```bash
   chmod 600 ~/.ssh/id_ed25519_gcp
   ```

3. Usar consola web de GCP:
   - Ve a: https://console.cloud.google.com/compute/instances?project=stvaldivia
   - Haz clic en "SSH" en la instancia `stvaldivia`


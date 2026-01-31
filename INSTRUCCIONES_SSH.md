# 🔐 Instrucciones para Configurar SSH

## ✅ Lo que ya está hecho:

1. ✅ Clave SSH generada: `~/.ssh/id_ed25519_gcp`
2. ✅ Endpoint de deployment actualizado para usar SSH
3. ✅ Script de configuración creado: `configurar_ssh.sh`

## 📋 Tu Clave Pública SSH:

```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIIW0Kze09D1j1pIa/67DKc4ztmNJW+ae2hHpVQKRVSXS sebagatica@gcp
```

## 🚀 Cómo Agregar la Clave a la VM:

### OPCIÓN 1: Usar Consola Web de GCP (MÁS FÁCIL)

1. Ve a: https://console.cloud.google.com/compute/instances?project=stvaldivia
2. Encuentra la instancia `stvaldivia`
3. Haz clic en el botón **"SSH"** (se abrirá una terminal en el navegador)
4. En la terminal, ejecuta:

```bash
mkdir -p ~/.ssh
chmod 700 ~/.ssh
echo "sebagatica:ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIIW0Kze09D1j1pIa/67DKc4ztmNJW+ae2hHpVQKRVSXS sebagatica@gcp" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

### OPCIÓN 2: Editar Metadata de la Instancia

1. Ve a: https://console.cloud.google.com/compute/instances?project=stvaldivia
2. Haz clic en la instancia `stvaldivia`
3. Haz clic en **"EDIT"** (Editar)
4. Baja hasta **"SSH Keys"**
5. Haz clic en **"ADD ITEM"**
6. Pega esta línea completa:
   ```
   sebagatica:ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIIW0Kze09D1j1pIa/67DKc4ztmNJW+ae2hHpVQKRVSXS sebagatica@gcp
   ```
7. Haz clic en **"SAVE"**

### OPCIÓN 3: Usar gcloud (si logras autenticarte)

```bash
gcloud auth login
./configurar_ssh.sh
```

## 🧪 Probar la Conexión:

Después de agregar la clave, prueba:

```bash
ssh -i ~/.ssh/id_ed25519_gcp sebagatica@34.176.144.166 "echo 'SSH funciona'"
```

Si funciona, verás: `SSH funciona`

## ✅ Una vez configurado:

El deployment desde el navegador funcionará automáticamente:
- Ve a: http://127.0.0.1:5001/admin/panel_control
- Haz clic en **"🚀 Actualizar Sitio"**

El endpoint intentará primero con gcloud, y si falla, usará SSH directo con tu clave.






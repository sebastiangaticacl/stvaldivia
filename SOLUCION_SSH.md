# 🔧 Solución: SSH no funciona desde terminal

## ❌ Problema
```
Permission denied (publickey)
```

La clave SSH no está autorizada en el servidor.

## ✅ SOLUCIÓN RÁPIDA (Usar Consola Web de GCP)

### Paso 1: Abrir consola SSH en el navegador
1. Ve a: **https://console.cloud.google.com/compute/instances?project=stvaldivia**
2. Busca la instancia **`stvaldivia`**
3. Haz clic en el botón **"SSH"** (se abrirá una terminal en el navegador)

### Paso 2: Agregar tu clave SSH
En la terminal que se abrió, ejecuta estos comandos:

```bash
mkdir -p ~/.ssh
chmod 700 ~/.ssh
echo "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIIW0Kze09D1j1pIa/67DKc4ztmNJW+ae2hHpVQKRVSXS sebagatica@gcp" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

### Paso 3: Probar desde tu terminal local
```bash
ssh -i ~/.ssh/id_ed25519_gcp sebagatica@34.176.144.166 "echo '✅ SSH funciona'"
```

---

## 🔄 ALTERNATIVA: Agregar clave desde Metadata de GCP

### Paso 1: Editar instancia
1. Ve a: **https://console.cloud.google.com/compute/instances?project=stvaldivia**
2. Haz clic en la instancia **`stvaldivia`**
3. Haz clic en **"EDIT"** (Editar)

### Paso 2: Agregar SSH Key
1. Baja hasta la sección **"SSH Keys"**
2. Haz clic en **"ADD ITEM"**
3. Pega esta línea completa:
   ```
   sebagatica:ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIIW0Kze09D1j1pIa/67DKc4ztmNJW+ae2hHpVQKRVSXS sebagatica@gcp
   ```
4. Haz clic en **"SAVE"**

### Paso 3: Esperar 1-2 minutos y probar
```bash
ssh -i ~/.ssh/id_ed25519_gcp sebagatica@34.176.144.166
```

---

## 🛠️ Configurar alias para facilitar conexión

Después de que funcione, agrega esto a `~/.ssh/config`:

```bash
cat >> ~/.ssh/config << 'EOF'
Host stvaldivia
    HostName 34.176.144.166
    User sebagatica
    IdentityFile ~/.ssh/id_ed25519_gcp
    StrictHostKeyChecking no
EOF
```

Luego podrás conectar simplemente con:
```bash
ssh stvaldivia
```

---

## ✅ Verificación

Una vez configurado, prueba:

```bash
# Conexión básica
ssh stvaldivia

# Ejecutar comando remoto
ssh stvaldivia "cd /var/www/stvaldivia && git status"

# Ver logs
ssh stvaldivia "sudo journalctl -u gunicorn -n 20"
```

---

## 📝 Notas

- La clave SSH local está en: `~/.ssh/id_ed25519_gcp`
- El servidor responde (ping funciona)
- Solo falta autorizar la clave en el servidor
- Una vez autorizada, funcionará permanentemente


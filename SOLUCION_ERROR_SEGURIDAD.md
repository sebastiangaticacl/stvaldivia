# 🛠️ SOLUCIÓN: Error de Seguridad Google Cloud

**Error:** "Error de seguridad. Por favor, recarga la página e intenta nuevamente."

---

## 🔍 CAUSAS COMUNES

1. **Sesión expirada** - La sesión de Google Cloud expiró
2. **Cookies/Caché** - El navegador tiene datos corruptos
3. **Múltiples cuentas** - Conflicto entre cuentas de Google
4. **Permisos** - La cuenta no tiene permisos suficientes

---

## ✅ SOLUCIONES RÁPIDAS

### SOLUCIÓN 1: Limpiar Sesión del Navegador

1. **Cerrar todas las pestañas de Google Cloud**
2. **Cerrar sesión de Google completamente:**
   - Ve a: https://accounts.google.com/logout
   - Cierra sesión de TODAS las cuentas
3. **Limpiar caché y cookies de Google Cloud:**
   - Chrome: Settings → Privacy → Clear browsing data → Cookies
   - Safari: Preferences → Privacy → Manage Website Data → Remove All
4. **Abrir ventana de incógnito/privada**
5. **Ir a:** https://console.cloud.google.com/run?project=stvaldiviacl
6. **Iniciar sesión nuevamente**

---

### SOLUCIÓN 2: Usar CLI (Recomendado)

Si el navegador sigue fallando, usa la línea de comandos:

#### Paso 1: Autenticación con código manual

```bash
# Iniciar autenticación sin abrir navegador
gcloud auth login --no-launch-browser

# Esto te dará un link y un código
# 1. Copia el link
# 2. Ábrelo en otro navegador (Chrome/Firefox)
# 3. Completa la autenticación
# 4. Copia el código de verificación
# 5. Pégalo en la terminal
```

#### Paso 2: Verificar autenticación

```bash
gcloud auth list
# Deberías ver tu cuenta activa
```

#### Paso 3: Deploy

```bash
cd /Users/sebagatica/tickets_cursor_clean
bash deploy_cloud_run.sh
```

---

### SOLUCIÓN 3: Usar Service Account (Para automatización)

Si necesitas deploy automático sin autenticación manual:

1. **Crear Service Account:**
   - Ve a: https://console.cloud.google.com/iam-admin/serviceaccounts?project=stvaldiviacl
   - Click "CREATE SERVICE ACCOUNT"
   - Nombre: `cloud-run-deployer`
   - Permisos: `Cloud Run Admin`, `Storage Admin`, `Cloud Build Service Account`

2. **Crear y descargar clave:**
   - Click en el service account creado
   - Pestaña "KEYS" → "ADD KEY" → "Create new key"
   - Tipo: JSON
   - Descargar el archivo

3. **Activar service account:**
```bash
gcloud auth activate-service-account --key-file=/path/to/service-account-key.json
```

4. **Deploy:**
```bash
bash deploy_cloud_run.sh
```

---

### SOLUCIÓN 4: Deploy Directo con Docker (Sin Cloud Build)

Si todo lo anterior falla, construye y despliega manualmente:

```bash
# 1. Configurar proyecto
gcloud config set project stvaldiviacl

# 2. Configurar Docker para GCR
gcloud auth configure-docker

# 3. Construir imagen localmente
docker build -t gcr.io/stvaldiviacl/bimba:latest .

# 4. Subir imagen
docker push gcr.io/stvaldiviacl/bimba:latest

# 5. Deploy a Cloud Run
gcloud run deploy bimba \
  --image gcr.io/stvaldiviacl/bimba:latest \
  --region southamerica-west1 \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars="FLASK_ENV=production,FLASK_SECRET_KEY=<TU_FLASK_SECRET_KEY>,DATABASE_URL=<tu_database_url>" \
  --memory=512Mi \
  --cpu=1 \
  --timeout=300 \
  --max-instances=10 \
  --min-instances=0
```

---

## 🎯 RECOMENDACIÓN RÁPIDA

**Para resolver rápido:**

1. ✅ **Cierra sesión de Google completamente**
2. ✅ **Abre ventana de incógnito**
3. ✅ **Vuelve a iniciar sesión**
4. ✅ **Intenta acceder a la consola**

**O usa CLI:**
```bash
gcloud auth login --no-launch-browser
# Sigue las instrucciones
```

---

## 📞 VERIFICAR ESTADO DEL PROYECTO

```bash
# Ver proyecto actual
gcloud config get-value project

# Ver servicios Cloud Run existentes
gcloud run services list --region=southamerica-west1

# Ver detalles del servicio bimba
gcloud run services describe bimba --region=southamerica-west1
```

---

**Si el problema persiste:** Puede ser un tema de permisos del proyecto. Verifica que tu cuenta tenga los roles necesarios en el proyecto `stvaldiviacl`.



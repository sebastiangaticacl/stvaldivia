# 🚀 INSTRUCCIONES PARA DEPLOY EN CLOUD RUN

**Proyecto:** `stvaldiviacl`  
**Estado:** Listo para deploy manual desde Console

---

## ⚠️ IMPORTANTE: DATABASE_URL REQUERIDO

Antes de desplegar, necesitas tener el `DATABASE_URL` de tu base de datos PostgreSQL en producción.

**Formato esperado:**
```
postgresql://usuario:password@host:5432/database
```

O si usas Cloud SQL:
```
postgresql://usuario:password@/database?host=/cloudsql/PROJECT:REGION:INSTANCE
```

---

## 📋 PASOS PARA DEPLOY DESDE CONSOLE

### PASO 1: Ir a Cloud Run Console
1. Abre: https://console.cloud.google.com/run?project=stvaldiviacl
2. Asegúrate de que el proyecto `stvaldiviacl` está seleccionado

### PASO 2: Crear Nuevo Servicio
1. Click **"CREATE SERVICE"**
2. En **"Deploy one revision from an existing container image"** o **"Continuously deploy new revisions from a source repository"**

**Si eliges Source Repository:**
- Click **"SET UP WITH CLOUD BUILD"**
- Autoriza GitHub si es necesario
- Selecciona: `stvaldivia/stvaldivia`
- Branch: `main`
- Build type: **Dockerfile** (debe detectarlo automáticamente)

**Si eliges Container Image:**
- Necesitarás construir la imagen primero con Cloud Build

### PASO 3: Configurar Servicio

**Service name:** `bimba`  
**Region:** `southamerica-west1` (Santiago)  
**CPU allocation:** **CPU is only allocated during request processing**  
**Minimum instances:** `0`  
**Maximum instances:** `10`  
**CPU:** `1`  
**Memory:** `512 MiB`  
**Timeout:** `300` segundos  
**Concurrency:** `80`  

### PASO 4: Variables de Entorno

Click **"Variables & Secrets"** → **"ADD VARIABLE"**

**Variables OBLIGATORIAS:**
```
FLASK_ENV = production
FLASK_SECRET_KEY = <TU_FLASK_SECRET_KEY>
DATABASE_URL = <TU_CONEXION_POSTGRESQL_AQUI>
```

**Variables OPCIONALES:**
```
OPENAI_API_KEY = <si usas el bot>
BIMBA_INTERNAL_API_KEY = <si usas API operational>
```

### PASO 5: Crear y Desplegar
1. Click **"CREATE"**
2. Esperar que Cloud Build compile (5-10 minutos)
3. Verificar que el servicio está **ACTIVE**

---

## 🔧 COMANDOS ALTERNATIVOS (Si tienes permisos)

Si tienes permisos completos, puedes usar:

```bash
# Configurar proyecto
gcloud config set project stvaldiviacl

# Habilitar APIs
gcloud services enable run.googleapis.com cloudbuild.googleapis.com containerregistry.googleapis.com

# Deploy (necesitas DATABASE_URL)
gcloud run deploy bimba \
  --source . \
  --region=southamerica-west1 \
  --platform=managed \
  --allow-unauthenticated \
  --set-env-vars="FLASK_ENV=production" \
  --set-env-vars="FLASK_SECRET_KEY=<TU_FLASK_SECRET_KEY>" \
  --set-env-vars="DATABASE_URL=<TU_DATABASE_URL>" \
  --memory=512Mi \
  --cpu=1 \
  --timeout=300 \
  --max-instances=10 \
  --min-instances=0
```

---

## 📊 DESPUÉS DEL DEPLOY

### Obtener URL del Servicio
```bash
gcloud run services describe bimba --region=southamerica-west1 --format="value(status.url)"
```

### Ver Logs
```bash
gcloud run services logs read bimba --region=southamerica-west1 --limit=50
```

### Probar Endpoint
```bash
curl https://<service-url>/api/v1/public/evento/hoy
```

---

## ⚠️ PROBLEMAS COMUNES

### Error: "DATABASE_URL not configured"
- Asegúrate de configurar `DATABASE_URL` en variables de entorno
- Verifica que la conexión es correcta

### Error: "FLASK_SECRET_KEY must be configured"
- Asegúrate de configurar `FLASK_SECRET_KEY` en variables de entorno
- Usa una clave segura: `<TU_FLASK_SECRET_KEY>`

### Error: "Build failed"
- Verifica que Dockerfile está en la raíz del repo
- Verifica que requirements.txt tiene todas las dependencias
- Revisa logs de Cloud Build

---

## 🎯 PRÓXIMOS PASOS DESPUÉS DEL DEPLOY

1. **Obtener URL del servicio Cloud Run**
2. **Crear Load Balancer** con IP estática
3. **Configurar DNS** para apuntar al Load Balancer
4. **Configurar SSL** (automático con Load Balancer)

---

**¿Necesitas ayuda con algún paso específico?** Avísame y te guío.


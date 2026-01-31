# 🚀 Guía de Deploy en Google Cloud Run

**Fecha:** 2026-01-03  
**Incluye:** Integración n8n corregida

---

## 📋 Prerrequisitos

1. **Google Cloud SDK instalado:**
   ```bash
   # Verificar instalación
   gcloud --version
   
   # Si no está instalado, descargar desde:
   # https://cloud.google.com/sdk/docs/install
   ```

2. **Autenticación:**
   ```bash
   gcloud auth login
   gcloud auth application-default login
   ```

3. **Proyecto configurado:**
   ```bash
   gcloud config set project stvaldivia
   ```

---

## 🚀 Opción 1: Deploy Automático (Recomendado)

### Paso 1: Configurar variables de entorno (opcional)

```bash
# Variables obligatorias
export DATABASE_URL="postgresql://user:pass@host:5432/database"

# Variables opcionales para n8n
export N8N_WEBHOOK_URL="https://tu-n8n-instance.com/webhook/bimba"
export N8N_WEBHOOK_SECRET="tu-secret-key"
export N8N_API_KEY="tu-api-key"

# Variables opcionales para OpenAI
export OPENAI_API_KEY="tu-openai-key"
```

### Paso 2: Ejecutar script de deploy

```bash
./deploy_gcloud_n8n.sh
```

El script:
- ✅ Verifica autenticación
- ✅ Configura proyecto
- ✅ Habilita APIs necesarias
- ✅ Verifica archivos (Dockerfile, requirements.txt)
- ✅ Verifica integración n8n
- ✅ Despliega a Cloud Run
- ✅ Prueba el servicio

---

## 🚀 Opción 2: Deploy Manual

### Paso 1: Habilitar APIs

```bash
gcloud services enable \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    containerregistry.googleapis.com \
    --project=stvaldivia
```

### Paso 2: Deploy con gcloud

```bash
gcloud run deploy bimba \
    --source . \
    --region=southamerica-west1 \
    --platform=managed \
    --allow-unauthenticated \
    --set-env-vars="FLASK_ENV=production,FLASK_SECRET_KEY=<TU_FLASK_SECRET_KEY>,DATABASE_URL=TU_DATABASE_URL_AQUI" \
    --memory=512Mi \
    --cpu=1 \
    --timeout=300 \
    --max-instances=10 \
    --min-instances=0 \
    --project=stvaldivia
```

### Paso 3: Agregar variables de entorno adicionales (opcional)

```bash
# Agregar n8n
gcloud run services update bimba \
    --region=southamerica-west1 \
    --update-env-vars="N8N_WEBHOOK_URL=https://tu-n8n-instance.com/webhook/bimba,N8N_WEBHOOK_SECRET=tu-secret,N8N_API_KEY=tu-api-key"

# Agregar OpenAI
gcloud run services update bimba \
    --region=southamerica-west1 \
    --update-env-vars="OPENAI_API_KEY=tu-openai-key"
```

---

## 🔍 Verificación Post-Deploy

### 1. Obtener URL del servicio

```bash
gcloud run services describe bimba \
    --region=southamerica-west1 \
    --format="value(status.url)"
```

### 2. Probar endpoint

```bash
curl https://<service-url>/api/v1/public/evento/hoy
```

### 3. Ver logs

```bash
gcloud run services logs read bimba \
    --region=southamerica-west1 \
    --limit=50
```

### 4. Verificar panel admin

1. Ir a: `https://<service-url>/admin/panel_control`
2. Verificar que la sección n8n aparece
3. Probar abrir el modal de configuración n8n

---

## ⚙️ Configuración de Variables de Entorno

### Variables OBLIGATORIAS

| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| `FLASK_ENV` | Entorno de Flask | `production` |
| `FLASK_SECRET_KEY` | Clave secreta de Flask | `<TU_FLASK_SECRET_KEY>` |
| `DATABASE_URL` | URL de conexión a PostgreSQL | `postgresql://user:pass@host:5432/database` |

### Variables OPCIONALES

| Variable | Descripción | Cuándo usar |
|----------|-------------|------------|
| `N8N_WEBHOOK_URL` | URL del webhook de n8n | Si usas n8n |
| `N8N_WEBHOOK_SECRET` | Secreto para validar webhooks | Si usas n8n con firma |
| `N8N_API_KEY` | API Key para autenticación | Si usas n8n con API key |
| `OPENAI_API_KEY` | Clave de API de OpenAI | Si usas el bot de IA |
| `USE_DIALOGFLOW` | Usar Dialogflow en lugar de OpenAI | Si prefieres Dialogflow |

---

## 🔧 Actualizar Variables de Entorno Después del Deploy

```bash
# Actualizar una variable
gcloud run services update bimba \
    --region=southamerica-west1 \
    --update-env-vars="N8N_WEBHOOK_URL=https://nueva-url.com/webhook"

# Actualizar múltiples variables
gcloud run services update bimba \
    --region=southamerica-west1 \
    --update-env-vars="N8N_WEBHOOK_URL=https://nueva-url.com/webhook,N8N_WEBHOOK_SECRET=nuevo-secret"

# Eliminar una variable
gcloud run services update bimba \
    --region=southamerica-west1 \
    --remove-env-vars="N8N_WEBHOOK_URL"
```

---

## 📊 Monitoreo

### Ver logs en tiempo real

```bash
gcloud run services logs tail bimba \
    --region=southamerica-west1
```

### Ver métricas

```bash
# Ver detalles del servicio
gcloud run services describe bimba \
    --region=southamerica-west1

# Ver en la consola web
# https://console.cloud.google.com/run?project=stvaldivia
```

---

## ⚠️ Problemas Comunes

### Error: "DATABASE_URL not configured"

**Solución:**
```bash
gcloud run services update bimba \
    --region=southamerica-west1 \
    --update-env-vars="DATABASE_URL=postgresql://user:pass@host:5432/database"
```

### Error: "FLASK_SECRET_KEY must be configured"

**Solución:**
```bash
gcloud run services update bimba \
    --region=southamerica-west1 \
    --update-env-vars="FLASK_SECRET_KEY=<TU_FLASK_SECRET_KEY>"
```

### Error: "Build failed"

**Verificar:**
1. Dockerfile existe en la raíz
2. requirements.txt tiene todas las dependencias
3. Revisar logs de Cloud Build:
   ```bash
   gcloud builds list --limit=5
   ```

### El servicio no responde

**Verificar:**
1. Logs del servicio
2. Variables de entorno configuradas
3. Base de datos accesible desde Cloud Run

---

## 🎯 Próximos Pasos Después del Deploy

1. **Configurar n8n:**
   - Ir a `/admin/panel_control`
   - Configurar URL del webhook de n8n
   - Probar conexión

2. **Configurar dominio personalizado:**
   - Crear Load Balancer con IP estática
   - Configurar DNS
   - Configurar SSL (automático con Load Balancer)

3. **Monitorear:**
   - Revisar logs regularmente
   - Configurar alertas si es necesario
   - Verificar métricas de uso

---

## 📝 Notas Importantes

- ✅ **Integración n8n:** Ya está corregida y lista para usar
- ✅ **Frontend:** Funciones JavaScript corregidas
- ✅ **Backend:** Eventos integrados en 5 ubicaciones
- ⚠️ **Variables de entorno:** Configurar desde panel admin o gcloud CLI
- ⚠️ **Base de datos:** Asegurar que Cloud Run puede acceder a PostgreSQL

---

**¿Necesitas ayuda?** Revisa los logs o contacta al equipo de desarrollo.

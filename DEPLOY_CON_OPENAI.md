# 🚀 Deploy con OpenAI Configurado

## ✅ Cambios Incluidos

- ✅ API key de OpenAI configurada
- ✅ Script de deploy actualizado
- ✅ Sistema listo para usar ChatGPT

## 📋 OPCIÓN 1: Deploy desde Consola Web (Recomendado)

### Paso 1: Abrir Cloud Run Console
🔗 **URL:** https://console.cloud.google.com/run?project=stvaldiviacl

### Paso 2: Seleccionar Servicio
1. Busca el servicio **`bimba`**
2. Click en el nombre del servicio

### Paso 3: Desplegar Nueva Revisión
1. Click en **"EDIT & DEPLOY NEW REVISION"**
2. Si está conectado a GitHub:
   - Selecciona branch: **`main`**
   - Click **"DEPLOY"**
3. Si NO está conectado:
   - Necesitas conectar el repositorio primero

### Paso 4: Configurar Variables de Entorno

**IMPORTANTE:** Agrega la variable de OpenAI:

1. En la página del servicio, click en **"EDIT & DEPLOY NEW REVISION"**
2. Expande **"Variables & Secrets"**
3. Click **"ADD VARIABLE"** y agrega:

```
OPENAI_API_KEY = <TU_OPENAI_API_KEY>
USE_DIALOGFLOW = false
```

**Variables que ya deberían estar:**
```
FLASK_ENV = production
FLASK_SECRET_KEY = <TU_FLASK_SECRET_KEY>
DATABASE_URL = (tu conexión PostgreSQL)
```

4. Click **"DEPLOY"**

---

## 📋 OPCIÓN 2: Deploy desde Terminal (Requiere Autenticación)

### Paso 1: Autenticarse
```bash
gcloud auth login
```

### Paso 2: Ejecutar Deploy
```bash
cd /Users/sebagatica/Documents/GitHub/stvaldivia
./deploy_cloud_run.sh
```

El script ya incluye la API key de OpenAI.

---

## ✅ Verificar que Funciona

Después del deploy:

1. Obtén la URL del servicio (aparece en la consola)
2. Prueba el chatbot:
   ```
   https://tu-url-cloud-run.run.app/bimba
   ```
3. Envía un mensaje de prueba
4. El bot debería responder usando ChatGPT

---

## 📊 Ver Logs

Para ver los logs del servicio:

```bash
gcloud run services logs read bimba --region=southamerica-west1 --limit=50
```

O desde la consola web, pestaña **"LOGS"**

---

## 🎯 Resumen Rápido

1. ✅ Abre: https://console.cloud.google.com/run?project=stvaldiviacl
2. ✅ Selecciona servicio `bimba`
3. ✅ Click "EDIT & DEPLOY NEW REVISION"
4. ✅ Agrega variable `OPENAI_API_KEY` con tu API key
5. ✅ Click "DEPLOY"
6. ✅ Prueba el chatbot en `/bimba`

**Tiempo estimado:** 5-10 minutos


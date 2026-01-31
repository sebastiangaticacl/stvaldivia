# 🚀 INSTRUCCIONES PARA DESPLEGAR AHORA

## ⚠️ IMPORTANTE: Despliegue desde Consola Web

No tienes permisos para desplegar desde CLI, pero puedes hacerlo fácilmente desde la consola web.

---

## 📋 PASOS RÁPIDOS (5 minutos)

### PASO 1: Abrir Cloud Run Console
🔗 **URL directa:** https://console.cloud.google.com/run?project=stvaldiviacl

1. Abre el link arriba
2. Verifica que el proyecto `stvaldiviacl` está seleccionado (arriba a la izquierda)

### PASO 2: Seleccionar Servicio
1. Busca el servicio **`bimba`** en la lista
2. Haz click en el nombre del servicio

### PASO 3: Desplegar Nueva Revisión
1. Click en el botón **"EDIT & DEPLOY NEW REVISION"** (arriba)
2. Si el servicio está conectado a GitHub:
   - En la sección **"Source"**, selecciona:
     - Repository: `stvaldivia/stvaldivia`
     - Branch: **`main`** (debe estar seleccionado por defecto)
   - Click en **"DEPLOY"**
3. Si NO está conectado a GitHub:
   - Necesitarás conectar el repositorio primero (ver abajo)

### PASO 4: Configurar Variables de GetNet (Después del Deploy)

Una vez desplegado, configura las variables de entorno:

1. En la página del servicio, click en **"EDIT & DEPLOY NEW REVISION"** nuevamente
2. Expande la sección **"Variables & Secrets"**
3. Click en **"ADD VARIABLE"** y agrega cada una:

**Variables para Pagos Online:**

```
GETNET_LOGIN = tu_login_getnet
GETNET_TRANKEY = tu_trankey_getnet
PUBLIC_BASE_URL = https://stvaldivia.cl
GETNET_API_BASE_URL = https://checkout.test.getnet.cl
GETNET_DEMO_MODE = false
```

**Variables Existentes (verificar que estén):**

```
FLASK_ENV = production
FLASK_SECRET_KEY = <TU_FLASK_SECRET_KEY>
DATABASE_URL = (tu conexión PostgreSQL)
```

4. Click en **"DEPLOY"** nuevamente

---

## 🔗 Si Necesitas Conectar GitHub (Primera Vez)

Si el servicio no está conectado a GitHub:

1. En la página de deploy, click en **"SET UP WITH CLOUD BUILD"**
2. Click en **"CONNECT REPOSITORY"**
3. Selecciona **"GitHub (Cloud Build GitHub App)"**
4. Autoriza GitHub si es necesario
5. Selecciona repositorio: `stvaldivia/stvaldivia`
6. Click en **"CONNECT"**
7. Selecciona branch: `main`
8. Build type: **"Dockerfile"** (debe detectarlo automáticamente)
9. Click en **"NEXT"** y continúa con la configuración

---

## ✅ Verificar que Funciona

Después del deploy:

1. Obtén la URL del servicio (aparece en la página del servicio)
2. Prueba: `https://tu-url-cloud-run.run.app/ecommerce/`
3. Verifica que la página carga correctamente

---

## 📊 Ver Logs

Para ver los logs del servicio:

1. En la página del servicio, click en la pestaña **"LOGS"**
2. O desde terminal:
```bash
gcloud run services logs read bimba --region=southamerica-west1 --limit=50
```

---

## 🎯 Resumen

1. ✅ Abre: https://console.cloud.google.com/run?project=stvaldiviacl
2. ✅ Selecciona servicio `bimba`
3. ✅ Click "EDIT & DEPLOY NEW REVISION"
4. ✅ Selecciona branch `main` (si está conectado a GitHub)
5. ✅ Click "DEPLOY"
6. ✅ Configura variables de GetNet (ver arriba)
7. ✅ Vuelve a hacer deploy con las variables

**Tiempo estimado:** 5-10 minutos




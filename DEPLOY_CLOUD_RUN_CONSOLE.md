# 🚀 DEPLOY CLOUD RUN - GUÍA CONSOLA WEB

**Proyecto:** `stvaldiviacl`  
**Método:** Console Web (más fácil y no requiere permisos CLI)

---

## ✅ PREPARACIÓN

### Datos que necesitas:
1. ✅ **FLASK_SECRET_KEY:** `<TU_FLASK_SECRET_KEY>`
2. ⚠️ **DATABASE_URL:** Necesitas obtenerlo (ver abajo)
3. ✅ **Repo GitHub:** `stvaldivia/stvaldivia` (branch `main`)

---

## 📋 PASO A PASO DESDE CONSOLA WEB

### PASO 1: Abrir Cloud Run Console
1. Ve a: **https://console.cloud.google.com/run?project=stvaldiviacl**
2. Asegúrate de que el proyecto `stvaldiviacl` está seleccionado (arriba a la izquierda)

### PASO 2: Crear Nuevo Servicio
1. Click en **"CREATE SERVICE"** (botón azul arriba)
2. En la sección **"Deploy"**, selecciona:
   - **"Continuously deploy new revisions from a source repository"**

### PASO 3: Conectar con GitHub
1. Click **"SET UP WITH CLOUD BUILD"**
2. Si es la primera vez:
   - Click **"CONNECT REPOSITORY"**
   - Selecciona **"GitHub (Cloud Build GitHub App)"**
   - Autoriza GitHub si es necesario
   - Selecciona repositorio: `stvaldivia/stvaldivia`
   - Click **"CONNECT"**
3. Si ya está conectado:
   - Selecciona repositorio: `stvaldivia/stvaldivia`
   - Branch: `main`
   - Build type: **"Dockerfile"** (debe detectarlo automáticamente)
   - Click **"NEXT"**

### PASO 4: Configurar Servicio

**Service name:** `bimba`  
**Region:** `southamerica-west1` (Santiago, Chile)  
**CPU allocation:** Selecciona **"CPU is only allocated during request processing"**  
**Minimum instances:** `0` (para ahorrar costos)  
**Maximum instances:** `10`  
**CPU:** `1`  
**Memory:** `512 MiB`  
**Timeout:** `300` segundos  
**Concurrency:** `80` (default)  

### PASO 5: Variables de Entorno

1. Expande la sección **"Variables & Secrets"**
2. Click **"ADD VARIABLE"** para cada una:

**Variable 1:**
- Name: `FLASK_ENV`
- Value: `production`

**Variable 2:**
- Name: `FLASK_SECRET_KEY`
- Value: `<TU_FLASK_SECRET_KEY>`

**Variable 3:**
- Name: `DATABASE_URL`
- Value: `<TU_CONEXION_POSTGRESQL>` (ver abajo cómo obtenerla)

**Variables Opcionales (si las usas):**
- `OPENAI_API_KEY` = `<tu clave OpenAI>`
- `BIMBA_INTERNAL_API_KEY` = `<generar clave>`
- `BIMBA_INTERNAL_API_BASE_URL` = `https://bimba-xxxxx-xx.a.run.app` (se llenará después del deploy)

### PASO 6: Crear y Desplegar
1. Click **"CREATE"** (abajo a la derecha)
2. Esperar que Cloud Build compile la imagen (5-10 minutos)
   - Verás el progreso en la pantalla
   - Puedes ver los logs de build haciendo click en el build
3. Cuando termine, verás que el servicio está **ACTIVE**

### PASO 7: Obtener URL del Servicio
1. Una vez desplegado, verás la URL del servicio tipo:
   ```
   https://bimba-xxxxx-xx.a.run.app
   ```
2. **Guarda esta URL** - la necesitarás para el Load Balancer

### PASO 8: Probar el Servicio
```bash
# Reemplaza con tu URL real
curl https://bimba-xxxxx-xx.a.run.app/api/v1/public/evento/hoy
```

Debe responder:
```json
{"evento": null, "status": "no_event"}
```

---

## 🔍 OBTENER DATABASE_URL

### Opción 1: Si usas Cloud SQL
1. Ve a: https://console.cloud.google.com/sql/instances?project=stvaldiviacl
2. Selecciona tu instancia de PostgreSQL
3. Ve a la pestaña **"Connections"**
4. Busca **"Connection name"** (formato: `PROJECT:REGION:INSTANCE`)
5. El formato será:
   ```
   postgresql://usuario:password@/database?host=/cloudsql/PROJECT:REGION:INSTANCE
   ```

### Opción 2: Si usas PostgreSQL externo
Formato:
```
postgresql://usuario:password@host:5432/database
```

### Opción 3: Verificar en archivos del proyecto
Si tienes credenciales guardadas localmente, busca en:
- `cloud_sql_credentials.txt`
- `.env` (en producción)
- Configuración de la VM

---

## ⚠️ SI EL DEPLOY FALLA

### Error: "Build failed"
1. Ve a Cloud Build logs: https://console.cloud.google.com/cloud-build/builds?project=stvaldiviacl
2. Revisa el último build fallido
3. Verifica que:
   - Dockerfile está en la raíz del repo
   - requirements.txt tiene todas las dependencias
   - No hay errores de sintaxis

### Error: "Service failed to start"
1. Ve a Cloud Run logs: Click en el servicio → pestaña **"Logs"**
2. Busca errores relacionados con:
   - `FLASK_SECRET_KEY` no configurado
   - `DATABASE_URL` no configurado
   - Error de conexión a base de datos

### Error: "Permission denied"
- Asegúrate de tener permisos de **Cloud Run Admin** o **Editor** en el proyecto
- Verifica que el proyecto `stvaldiviacl` está seleccionado

---

## 📊 DESPUÉS DEL DEPLOY EXITOSO

### 1. Verificar Logs
```bash
# Desde Console
# Cloud Run → bimba → Logs
```

### 2. Probar Endpoints
```bash
# API pública
curl https://<tu-url>.run.app/api/v1/public/evento/hoy

# Bot API (si está configurado)
curl -X POST https://<tu-url>.run.app/api/v1/bot/responder \
  -H "Content-Type: application/json" \
  -d '{"mensaje":"qué hay hoy?","canal":"test"}'
```

### 3. Próximos Pasos
1. ✅ Servicio Cloud Run funcionando
2. ⏳ Crear Load Balancer con IP estática
3. ⏳ Configurar DNS para apuntar al Load Balancer
4. ⏳ SSL automático con Load Balancer

---

## 🎯 CHECKLIST

- [ ] Cloud Run Console abierta
- [ ] Proyecto `stvaldiviacl` seleccionado
- [ ] Servicio creado con nombre `bimba`
- [ ] GitHub conectado (`stvaldivia/stvaldivia`)
- [ ] Branch `main` seleccionado
- [ ] Dockerfile detectado
- [ ] Variables de entorno configuradas:
  - [ ] `FLASK_ENV=production`
  - [ ] `FLASK_SECRET_KEY` configurado
  - [ ] `DATABASE_URL` configurado
- [ ] Build completado exitosamente
- [ ] Servicio ACTIVE
- [ ] URL del servicio obtenida
- [ ] Endpoint probado y funcionando

---

**¿Necesitas ayuda con algún paso?** Avísame y te guío específicamente.


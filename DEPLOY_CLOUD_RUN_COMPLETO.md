# 🚀 DEPLOY CLOUD RUN - GUÍA COMPLETA

**Proyecto:** `stvaldiviacl`  
**Método:** Console Web  
**Tiempo estimado:** 15-20 minutos

---

## ✅ DATOS LISTOS PARA USAR

### Variables de Entorno Pre-configuradas:

```
FLASK_ENV = production
FLASK_SECRET_KEY = <TU_FLASK_SECRET_KEY>
DATABASE_URL = <TU_DATABASE_URL>
```

**⚠️ NOTA:** El DATABASE_URL apunta al proyecto `pelagic-river-479014-a3`. Si Cloud Run está en `stvaldiviacl`, necesitarás:
- O usar el proyecto `pelagic-river-479014-a3` para Cloud Run
- O configurar Cloud SQL en `stvaldiviacl` y migrar la base de datos
- O usar una conexión IP pública si Cloud SQL permite conexiones externas

---

## 📋 PASO A PASO DESDE CONSOLA WEB

### PASO 1: Abrir Cloud Run Console
🔗 **URL directa:** https://console.cloud.google.com/run?project=stvaldiviacl

1. Abre el link arriba
2. Verifica que el proyecto `stvaldiviacl` está seleccionado (arriba a la izquierda)
3. Si no, cambia el proyecto usando el selector de proyectos

### PASO 2: Crear Nuevo Servicio
1. Click en **"CREATE SERVICE"** (botón azul grande arriba)
2. En la sección **"Deploy"**, selecciona:
   - ✅ **"Continuously deploy new revisions from a source repository"**

### PASO 3: Conectar con GitHub
1. Click **"SET UP WITH CLOUD BUILD"**

**Si es la primera vez conectando GitHub:**
- Click **"CONNECT REPOSITORY"**
- Selecciona **"GitHub (Cloud Build GitHub App)"**
- Autoriza GitHub si es necesario
- Selecciona repositorio: `stvaldivia/stvaldivia`
- Click **"CONNECT"**

**Si ya está conectado:**
- Repository: `stvaldivia/stvaldivia`
- Branch: `main`
- Build type: **"Dockerfile"** (debe detectarlo automáticamente)
- Click **"NEXT"**

### PASO 4: Configurar Servicio

**Service name:** `bimba`  
**Region:** `southamerica-west1` (Santiago, Chile) o `us-central1`  
**CPU allocation:** ✅ **"CPU is only allocated during request processing"**  
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
- Value: `<TU_DATABASE_URL>`

**⚠️ IMPORTANTE:** Si Cloud Run está en `stvaldiviacl` pero Cloud SQL está en `pelagic-river-479014-a3`, necesitarás:
- Configurar Cloud SQL Proxy en Cloud Run, O
- Usar el proyecto `pelagic-river-479014-a3` para Cloud Run también

**Variables Opcionales (si las usas):**
- `OPENAI_API_KEY` = `<tu clave OpenAI>` (si usas el bot)
- `BIMBA_INTERNAL_API_KEY` = `<generar clave>` (si usas API operational)

### PASO 6: Configurar Conexión a Cloud SQL (Si es necesario)

Si Cloud SQL está en otro proyecto:
1. En la sección **"Connections"**, click **"ADD CONNECTION"**
2. Selecciona la instancia de Cloud SQL
3. Si no aparece, necesitarás configurar VPC connector o usar IP pública

### PASO 7: Crear y Desplegar
1. Click **"CREATE"** (abajo a la derecha)
2. Esperar que Cloud Build compile la imagen (5-10 minutos)
   - Verás el progreso en la pantalla
   - Puedes ver los logs de build haciendo click en el build
3. Cuando termine, verás que el servicio está **ACTIVE**

### PASO 8: Obtener URL del Servicio
1. Una vez desplegado, verás la URL del servicio tipo:
   ```
   https://bimba-xxxxx-xx.a.run.app
   ```
2. **Guarda esta URL** - la necesitarás para el Load Balancer

### PASO 9: Probar el Servicio
```bash
# Reemplaza con tu URL real
curl https://bimba-xxxxx-xx.a.run.app/api/v1/public/evento/hoy
```

Debe responder:
```json
{"evento": null, "status": "no_event"}
```

---

## ⚠️ PROBLEMA POTENCIAL: Cloud SQL en Diferente Proyecto

Si Cloud SQL está en `pelagic-river-479014-a3` pero Cloud Run está en `stvaldiviacl`:

### Opción 1: Usar el mismo proyecto para Cloud Run (Recomendado)
1. Cambiar a proyecto `pelagic-river-479014-a3` en Cloud Run Console
2. Desplegar ahí (Cloud SQL estará disponible directamente)

### Opción 2: Configurar VPC Connector
1. Crear VPC connector en `stvaldiviacl`
2. Conectar con el proyecto `pelagic-river-479014-a3`
3. Configurar Cloud SQL Proxy

### Opción 3: Usar IP Pública (Si está habilitada)
1. Habilitar IP pública en Cloud SQL
2. Cambiar DATABASE_URL a formato IP:
   ```
   postgresql://bimba_user:password@IP_PUBLICA:5432/bimba
   ```

---

## 🔍 VERIFICAR LOGS DESPUÉS DEL DEPLOY

### Desde Console:
1. Ve a Cloud Run → `bimba` → pestaña **"Logs"**
2. Busca mensajes como:
   - ✅ "Starting gunicorn..."
   - ✅ "Listening at: http://0.0.0.0:8080"
   - ❌ Errores de conexión a base de datos
   - ❌ Errores de variables de entorno

### Desde CLI:
```bash
gcloud run services logs read bimba --region=southamerica-west1 --limit=50
```

---

## 📊 CHECKLIST FINAL

- [ ] Cloud Run Console abierta
- [ ] Proyecto correcto seleccionado
- [ ] Servicio creado con nombre `bimba`
- [ ] GitHub conectado (`stvaldivia/stvaldivia`)
- [ ] Branch `main` seleccionado
- [ ] Dockerfile detectado
- [ ] Variables de entorno configuradas:
  - [ ] `FLASK_ENV=production`
  - [ ] `FLASK_SECRET_KEY` configurado
  - [ ] `DATABASE_URL` configurado
- [ ] Conexión a Cloud SQL configurada (si es necesario)
- [ ] Build completado exitosamente
- [ ] Servicio ACTIVE
- [ ] URL del servicio obtenida
- [ ] Endpoint probado y funcionando
- [ ] Logs revisados (sin errores críticos)

---

## 🎯 PRÓXIMOS PASOS DESPUÉS DEL DEPLOY

1. ✅ Servicio Cloud Run funcionando
2. ⏳ Crear Load Balancer con IP estática
3. ⏳ Configurar DNS para apuntar al Load Balancer
4. ⏳ SSL automático con Load Balancer
5. ⏳ Verificar que https://stvaldivia.cl funciona

---

**¿Listo para empezar?** Abre el link del PASO 1 y sigue los pasos. Si encuentras algún problema, avísame y te ayudo a resolverlo.


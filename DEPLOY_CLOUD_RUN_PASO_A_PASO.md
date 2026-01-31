# 🚀 DEPLOY CLOUD RUN - PASO A PASO

**Objetivo:** Desplegar BIMBA en Cloud Run y conectarlo con stvaldivia.cl

---

## 📋 PRE-REQUISITOS VERIFICADOS

✅ Repo en GitHub: `stvaldivia/stvaldivia`  
✅ Branch: `main`  
✅ Dockerfile configurado  
✅ Código listo para producción  

---

## PASO 1: CONFIGURAR PROYECTO GOOGLE CLOUD

### 1.1. Verificar/Configurar Proyecto
```bash
# Ver proyecto actual
gcloud config get-value project

# Si necesitas cambiar de proyecto
gcloud config set project pelagic-river-479014-a3

# Verificar
gcloud config get-value project
```

### 1.2. Habilitar APIs Necesarias
```bash
# Habilitar Cloud Run API
gcloud services enable run.googleapis.com

# Habilitar Cloud Build API (para GitHub)
gcloud services enable cloudbuild.googleapis.com

# Habilitar Container Registry API
gcloud services enable containerregistry.googleapis.com

# Verificar APIs habilitadas
gcloud services list --enabled | grep -E "run|cloudbuild|containerregistry"
```

---

## PASO 2: CONECTAR GITHUB CON CLOUD BUILD

### 2.1. Conectar Repositorio (Desde Console)

**Opción A: Desde Console Web (Más fácil)**
1. Ir a: https://console.cloud.google.com/cloud-build/triggers
2. Click **"CONNECT REPOSITORY"**
3. Seleccionar **"GitHub (Cloud Build GitHub App)"**
4. Autorizar GitHub si es necesario
5. Seleccionar repositorio: `stvaldivia/stvaldivia`
6. Click **"CONNECT"**

**Opción B: Desde CLI**
```bash
# Conectar repositorio (requiere autenticación web)
gcloud builds triggers create github \
  --repo-name=stvaldivia \
  --repo-owner=stvaldivia \
  --branch-pattern="^main$" \
  --build-config=Dockerfile \
  --name=stvaldivia-deploy
```

---

## PASO 3: DESPLEGAR SERVICIO CLOUD RUN

### 3.1. Desplegar desde GitHub (Recomendado - CI/CD)

**Desde Console:**
1. Ir a: https://console.cloud.google.com/run
2. Click **"CREATE SERVICE"**
3. **Source:** Seleccionar **"Continuously deploy new revisions from a source repository"**
4. **Repository:** Seleccionar `stvaldivia/stvaldivia`
5. **Branch:** `main`
6. **Build type:** **Dockerfile** (debe detectarlo automáticamente)
7. Click **"NEXT"**

### 3.2. Configurar Servicio

**Service name:** `bimba` o `stvaldivia`  
**Region:** `southamerica-west1` (Santiago) o `us-central1`  
**CPU allocation:** **CPU is only allocated during request processing**  
**Minimum instances:** `0` (para ahorrar costos)  
**Maximum instances:** `10`  
**CPU:** `1`  
**Memory:** `512 MiB` (mínimo, aumentar si es necesario)  
**Timeout:** `300` segundos (5 minutos)  
**Concurrency:** `80`  

### 3.3. Configurar Variables de Entorno

Click en **"Variables & Secrets"** → **"ADD VARIABLE"**

**Variables OBLIGATORIAS:**
```
FLASK_ENV = production
FLASK_SECRET_KEY = Ovr25k_RZ9JH1BToxKu4PIj-xn-_HsmChGJ2ayQqYERXTyd2ke2UBQ2WmS9emwawQsSkFfECddMuGbdVO1_CEQ
DATABASE_URL = <tu conexión PostgreSQL>
```

**Variables OPCIONALES (si las usas):**
```
OPENAI_API_KEY = <si usas el bot>
BIMBA_INTERNAL_API_KEY = <si usas API operational>
BIMBA_INTERNAL_API_BASE_URL = https://<service-name>-xxxxx-xx.a.run.app
```

**⚠️ IMPORTANTE:** Necesitas tener `DATABASE_URL` listo antes de continuar.

### 3.4. Crear y Desplegar

1. Click **"CREATE"**
2. Esperar que Cloud Build compile la imagen (5-10 minutos)
3. Verificar que el servicio está **ACTIVE**

---

## PASO 4: VERIFICAR DEPLOY

### 4.1. Obtener URL del Servicio
```bash
# Ver servicios Cloud Run
gcloud run services list

# Obtener URL específica
gcloud run services describe bimba --region=southamerica-west1 --format="value(status.url)"
```

### 4.2. Probar Endpoint
```bash
# Obtener URL (reemplaza con tu servicio)
SERVICE_URL=$(gcloud run services describe bimba --region=southamerica-west1 --format="value(status.url)")

# Test API pública
curl $SERVICE_URL/api/v1/public/evento/hoy

# Debe responder: {"evento": null, "status": "no_event"}
```

### 4.3. Ver Logs
```bash
# Ver logs en tiempo real
gcloud run services logs read bimba --region=southamerica-west1 --limit=50

# O desde Console:
# https://console.cloud.google.com/run/detail/<region>/<service-name>/logs
```

---

## PASO 5: CONFIGURAR LOAD BALANCER Y DNS

### 5.1. Crear IP Estática Global
```bash
# Crear IP estática
gcloud compute addresses create stvaldivia-ip \
  --global \
  --ip-version IPV4

# Ver IP asignada
gcloud compute addresses describe stvaldivia-ip --global --format="value(address)"
```

**Guarda esta IP** - la necesitarás para DNS.

### 5.2. Crear Load Balancer (Desde Console)

1. Ir a: https://console.cloud.google.com/net-services/loadbalancing/list
2. Click **"CREATE LOAD BALANCER"**
3. Seleccionar: **"HTTP(S) Load Balancing"** → **"EXTERNAL"** → **"START CONFIGURATION"**

**Configuración Frontend:**
- Name: `stvaldivia-lb-frontend`
- IP address: Seleccionar `stvaldivia-ip` (la que creaste)
- Port: `443` (HTTPS)
- Certificate: **"CREATE A NEW CERTIFICATE"**
  - Name: `stvaldivia-cert`
  - Domain: `stvaldivia.cl`
  - Additional domain: `www.stvaldivia.cl`
  - Type: **Google-managed certificate**
  - Click **"CREATE"**

**Configuración Backend:**
- Click **"CREATE A BACKEND SERVICE"**
- Name: `stvaldivia-backend`
- Backend type: **Cloud Run**
- Cloud Run service: Seleccionar `bimba` (tu servicio)
- Region: Seleccionar región donde está Cloud Run
- Click **"CREATE"**

**Routing Rules:**
- Host and path rules: Default → `stvaldivia-backend`
- Click **"CREATE"**

### 5.3. Esperar Provisión
- Load Balancer: 5-15 minutos
- Certificado SSL: 10-60 minutos

Verificar estado:
```bash
# Ver estado del Load Balancer
gcloud compute forwarding-rules list

# Ver estado del certificado
gcloud compute ssl-certificates list
```

### 5.4. Configurar DNS

En tu proveedor de DNS (donde compraste stvaldivia.cl):

**Registro A para stvaldivia.cl:**
- Type: **A**
- Name: `@` o `stvaldivia.cl`
- Value: `<IP del Load Balancer>` (la IP estática)
- TTL: `3600`

**Registro A para www.stvaldivia.cl:**
- Type: **A**
- Name: `www`
- Value: `<IP del Load Balancer>` (misma IP)
- TTL: `3600`

### 5.5. Verificar DNS
```bash
# Verificar propagación DNS
dig stvaldivia.cl +short
dig www.stvaldivia.cl +short

# Debe mostrar la IP del Load Balancer
```

---

## PASO 6: VERIFICACIÓN FINAL

### 6.1. Verificar HTTPS
```bash
# Test HTTPS
curl -I https://stvaldivia.cl
curl -I https://www.stvaldivia.cl

# Debe responder HTTP/2 200
```

### 6.2. Verificar API
```bash
# Test API pública
curl https://stvaldivia.cl/api/v1/public/evento/hoy

# Debe responder: {"evento": null, "status": "no_event"}
```

### 6.3. Verificar en Navegador
1. Abrir: https://stvaldivia.cl
2. Verificar certificado SSL (candado verde)
3. Verificar que carga correctamente

---

## 🔧 COMANDOS ÚTILES

### Ver Estado del Servicio
```bash
gcloud run services describe bimba --region=southamerica-west1
```

### Ver Logs
```bash
gcloud run services logs read bimba --region=southamerica-west1 --limit=100
```

### Actualizar Variables de Entorno
```bash
gcloud run services update bimba \
  --region=southamerica-west1 \
  --update-env-vars FLASK_ENV=production
```

### Ver IP del Load Balancer
```bash
gcloud compute addresses describe stvaldivia-ip --global --format="value(address)"
```

### Ver Estado del Certificado SSL
```bash
gcloud compute ssl-certificates describe stvaldivia-cert --global
```

---

## ⚠️ TROUBLESHOOTING

### Error: "Service failed to start"
- Verificar variables de entorno (FLASK_SECRET_KEY, DATABASE_URL)
- Ver logs: `gcloud run services logs read <service-name> --region=<region>`
- Verificar que DATABASE_URL es correcto

### Error: "Build failed"
- Verificar Dockerfile está en la raíz
- Ver logs de Cloud Build en Console
- Verificar que requirements.txt tiene todas las dependencias

### Error: "Certificate provisioning failed"
- Verificar que DNS apunta correctamente al Load Balancer
- Esperar más tiempo (puede tardar hasta 1 hora)
- Verificar que el dominio está verificado

### Error: "502 Bad Gateway"
- Verificar que Cloud Run está activo
- Verificar logs de Cloud Run
- Verificar configuración del Load Balancer backend

---

## 📊 CHECKLIST FINAL

- [ ] Proyecto Google Cloud configurado
- [ ] APIs habilitadas (Cloud Run, Cloud Build)
- [ ] GitHub conectado con Cloud Build
- [ ] Servicio Cloud Run creado
- [ ] Variables de entorno configuradas
- [ ] Build completado exitosamente
- [ ] Servicio Cloud Run ACTIVE
- [ ] URL del servicio obtenida
- [ ] IP estática creada
- [ ] Load Balancer creado
- [ ] Certificado SSL aprovisionado
- [ ] DNS configurado (A records)
- [ ] DNS propagado
- [ ] HTTPS funcionando
- [ ] API respondiendo correctamente

---

## 🎯 PRÓXIMOS PASOS DESPUÉS DEL DEPLOY

1. **Monitorear logs** para detectar errores
2. **Configurar alertas** en Cloud Monitoring
3. **Ajustar recursos** según uso real
4. **Configurar dominio personalizado** si es necesario
5. **Backup de base de datos** regularmente

---

**¿Listo para empezar?** Empieza por el PASO 1 y avísame si necesitas ayuda en algún paso específico.


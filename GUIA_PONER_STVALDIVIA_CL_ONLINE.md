# 🚀 GUÍA: PONER stvaldivia.cl EN LÍNEA

**Objetivo:** Dejar https://stvaldivia.cl funcionando correctamente

---

## 📊 ESTADO ACTUAL

✅ **Código listo:** Repo configurado para Cloud Run  
✅ **Dockerfile:** Configurado correctamente  
✅ **Push a GitHub:** Completado  
⚠️ **Cloud Run:** Pendiente de deploy  
⚠️ **DNS:** No configurado  
⚠️ **SSL:** Pendiente  

---

## 🎯 PLAN DE ACCIÓN (Cloud Run - Recomendado)

### PASO 1: Desplegar en Cloud Run

#### 1.1. Ir a Google Cloud Console
1. Abre: https://console.cloud.google.com/run
2. Selecciona tu proyecto: `pelagic-river-479014-a3` (o el que uses)

#### 1.2. Crear Nuevo Servicio
1. Click en **"CREATE SERVICE"**
2. **Configuración básica:**
   - Service name: `bimba` o `stvaldivia`
   - Region: `southamerica-west1` (o la más cercana)

#### 1.3. Conectar con GitHub
1. En **"Source"**, selecciona **"Continuously deploy new revisions from a source repository"**
2. Click **"SET UP WITH CLOUD BUILD"**
3. Autoriza GitHub si es necesario
4. Selecciona:
   - Repository: `stvaldivia/stvaldivia`
   - Branch: `main`
   - Build type: **"Dockerfile"** (debe detectarlo automáticamente)

#### 1.4. Configurar Variables de Entorno
En la sección **"Variables & Secrets"**, agrega:

**OBLIGATORIAS:**
```
FLASK_ENV = production
FLASK_SECRET_KEY = <generar clave segura - ver abajo>
DATABASE_URL = <tu conexión PostgreSQL>
```

**OPCIONALES (si usas estas features):**
```
OPENAI_API_KEY = <si usas el bot>
BIMBA_INTERNAL_API_KEY = <si usas API operational>
BIMBA_INTERNAL_API_BASE_URL = https://<tu-servicio>.run.app
```

**Generar FLASK_SECRET_KEY:**
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
```

#### 1.5. Configurar Recursos
- **CPU:** 1 vCPU (mínimo)
- **Memory:** 512 MiB (mínimo, aumentar si es necesario)
- **Timeout:** 300 segundos (5 minutos)
- **Concurrency:** 80 (default)
- **Min instances:** 0 (para ahorrar costos)
- **Max instances:** 10 (ajustar según necesidad)

#### 1.6. Desplegar
1. Click **"CREATE"**
2. Esperar que el build termine (5-10 minutos)
3. Verificar que el servicio está **ACTIVE**

#### 1.7. Obtener URL del Servicio
Después del deploy, verás una URL tipo:
```
https://bimba-xxxxx-xx.a.run.app
```

**Guarda esta URL** - la necesitarás para el Load Balancer.

---

### PASO 2: Configurar Load Balancer (Para DNS y SSL)

#### 2.1. Crear IP Estática
```bash
gcloud compute addresses create stvaldivia-ip \
  --global \
  --ip-version IPV4
```

O desde Console:
1. Ir a: https://console.cloud.google.com/networking/addresses/list
2. Click **"RESERVE EXTERNAL STATIC IP ADDRESS"**
3. Name: `stvaldivia-ip`
4. Type: **Global**
5. IP version: **IPv4**
6. Click **"RESERVE"**

**Guarda la IP** que se asigna.

#### 2.2. Crear Load Balancer
1. Ir a: https://console.cloud.google.com/net-services/loadbalancing/list
2. Click **"CREATE LOAD BALANCER"**
3. Seleccionar: **"HTTP(S) Load Balancing"** → **"EXTERNAL"** → **"START CONFIGURATION"**

#### 2.3. Configurar Frontend
1. **Name:** `stvaldivia-lb`
2. **IP address:** Seleccionar la IP estática creada (`stvaldivia-ip`)
3. **Port:** 443 (HTTPS)
4. **Certificate:** Click **"CREATE A NEW CERTIFICATE"**
   - Name: `stvaldivia-cert`
   - Domain: `stvaldivia.cl`
   - Additional domain: `www.stvaldivia.cl`
   - Type: **Google-managed certificate**
   - Click **"CREATE"**

#### 2.4. Configurar Backend
1. **Backend services:** Click **"CREATE A BACKEND SERVICE"**
2. **Name:** `stvaldivia-backend`
3. **Backend type:** **Cloud Run**
4. **Cloud Run service:** Seleccionar el servicio creado (`bimba` o `stvaldivia`)
5. **Region:** Seleccionar la región donde está Cloud Run
6. Click **"CREATE"**

#### 2.5. Configurar Routing Rules
1. **Host and path rules:** 
   - Default: `stvaldivia-backend`
2. Click **"CREATE"**

#### 2.6. Esperar Provisión
- El Load Balancer tarda 5-15 minutos en provisionarse
- El certificado SSL tarda 10-60 minutos en aprovisionarse
- Verificar estado en la consola

---

### PASO 3: Configurar DNS

#### 3.1. Ir a tu Proveedor de DNS
(Donde compraste el dominio stvaldivia.cl)

#### 3.2. Configurar Registros A
Crear/editar registros:

**Para stvaldivia.cl:**
- Type: **A**
- Name: `@` o `stvaldivia.cl`
- Value: `<IP del Load Balancer>` (la IP estática que creaste)
- TTL: 3600 (1 hora)

**Para www.stvaldivia.cl:**
- Type: **A**
- Name: `www`
- Value: `<IP del Load Balancer>` (misma IP)
- TTL: 3600 (1 hora)

#### 3.3. Esperar Propagación DNS
- Puede tardar 5 minutos a 24 horas
- Verificar con: `dig stvaldivia.cl +short`
- Debe mostrar la IP del Load Balancer

---

### PASO 4: Verificar que Funciona

#### 4.1. Verificar DNS
```bash
dig stvaldivia.cl +short
# Debe mostrar la IP del Load Balancer

dig www.stvaldivia.cl +short
# Debe mostrar la misma IP
```

#### 4.2. Verificar SSL
```bash
curl -I https://stvaldivia.cl
# Debe responder HTTP/2 200

curl -I https://www.stvaldivia.cl
# Debe responder HTTP/2 200
```

#### 4.3. Verificar API
```bash
curl https://stvaldivia.cl/api/v1/public/evento/hoy
# Debe responder: {"evento": null, "status": "no_event"}
```

#### 4.4. Verificar en Navegador
1. Abrir: https://stvaldivia.cl
2. Verificar que carga correctamente
3. Verificar que el certificado SSL es válido (candado verde)

---

## 🔧 ALTERNATIVA: Usar VM + Nginx (Si prefieres)

Si prefieres usar la VM que ya tienes configurada:

### PASO 1: Verificar VM
```bash
gcloud compute ssh sebastian@stvaldivia-vm --zone=southamerica-west1-a

# Verificar Flask
sudo systemctl status flask_app

# Verificar Nginx
sudo systemctl status nginx

# Test local
curl http://127.0.0.1:5001/api/v1/public/evento/hoy
```

### PASO 2: Configurar Firewall
```bash
# Permitir HTTP
gcloud compute firewall-rules create allow-http \
  --allow tcp:80 \
  --source-ranges 0.0.0.0/0 \
  --target-tags http-server

# Permitir HTTPS
gcloud compute firewall-rules create allow-https \
  --allow tcp:443 \
  --source-ranges 0.0.0.0/0 \
  --target-tags https-server
```

### PASO 3: Configurar DNS
En tu proveedor de DNS:
- **stvaldivia.cl** → A → `34.176.74.130`
- **www.stvaldivia.cl** → A → `34.176.74.130`

### PASO 4: Configurar SSL
```bash
# En la VM
sudo certbot --nginx -d stvaldivia.cl -d www.stvaldivia.cl
```

---

## ⚠️ CHECKLIST FINAL

### Cloud Run (Recomendado)
- [ ] Servicio Cloud Run creado y activo
- [ ] Variables de entorno configuradas
- [ ] URL del servicio obtenida
- [ ] IP estática creada
- [ ] Load Balancer creado y configurado
- [ ] Certificado SSL aprovisionado
- [ ] DNS configurado (A records)
- [ ] DNS propagado (verificado con dig)
- [ ] HTTPS funcionando
- [ ] API respondiendo correctamente

### VM + Nginx (Alternativa)
- [ ] Flask corriendo en VM
- [ ] Nginx configurado
- [ ] Firewall configurado (80, 443)
- [ ] DNS configurado (A records)
- [ ] DNS propagado
- [ ] SSL configurado con certbot
- [ ] HTTPS funcionando

---

## 🐛 TROUBLESHOOTING

### Error: "Service not found" en Cloud Run
- Verificar que el servicio existe
- Verificar región correcta
- Verificar permisos de Cloud Run

### Error: "Certificate provisioning failed"
- Verificar que DNS apunta correctamente
- Esperar más tiempo (puede tardar hasta 1 hora)
- Verificar que el dominio está verificado en Google Cloud

### Error: "502 Bad Gateway"
- Verificar que Cloud Run está activo
- Verificar logs de Cloud Run
- Verificar variables de entorno (FLASK_SECRET_KEY, DATABASE_URL)

### DNS no resuelve
- Verificar registros en proveedor DNS
- Esperar propagación (hasta 24 horas)
- Verificar con `dig` o `nslookup`

### SSL no funciona
- Verificar que DNS apunta correctamente
- Verificar que certificado está aprovisionado
- Verificar logs del Load Balancer

---

## 📞 DATOS NECESARIOS

Para completar el deploy necesitas:

1. **DATABASE_URL:**
   - Si usas Cloud SQL: `postgresql://usuario:password@/database?host=/cloudsql/PROJECT:REGION:INSTANCE`
   - Si usas PostgreSQL externo: `postgresql://usuario:password@host:5432/database`

2. **FLASK_SECRET_KEY:**
   - Generar con: `python3 -c "import secrets; print(secrets.token_urlsafe(64))"`

3. **OPENAI_API_KEY (opcional):**
   - Si usas el bot de IA

4. **Acceso a DNS:**
   - Credenciales de tu proveedor de dominio
   - Panel de control DNS

---

## ✅ RESULTADO ESPERADO

Al finalizar, deberías tener:
- ✅ https://stvaldivia.cl funcionando
- ✅ https://www.stvaldivia.cl funcionando (redirige o funciona igual)
- ✅ SSL válido (certificado automático)
- ✅ API funcionando: `/api/v1/public/evento/hoy`
- ✅ Panel admin funcionando: `/admin/panel_control`

---

**¿Necesitas ayuda con algún paso específico?** Puedo ayudarte a ejecutar los comandos o revisar la configuración.


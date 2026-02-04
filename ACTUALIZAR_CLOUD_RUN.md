# 🚀 ACTUALIZAR CLOUD RUN - GUÍA RÁPIDA

> **Deprecado:** Ya no usamos Google Cloud. Deploy por SSH: ver `docs/DEPLOY_PRODUCCION.md` y `./deploy_completo.sh`

**Proyecto:** `stvaldiviacl`  
**Servicio:** `bimba`  
**Región:** `southamerica-west1`

---

## ⚠️ PROBLEMA: AUTENTICACIÓN REQUERIDA

Para actualizar Cloud Run, necesitas autenticarte primero con Google Cloud.

---

## 🔐 OPCIÓN 1: AUTENTICACIÓN CON NAVEGADOR

### Paso 1: Autenticarse
```bash
gcloud auth login
```

### Paso 2: Si Safari falla (HTTP bloqueado)
1. Cuando aparezca el link en la terminal, cópialo
2. Ábrelo en Chrome o Firefox (no Safari)
3. Completa la autenticación
4. Copia el código de verificación
5. Pégalo en la terminal

### Paso 3: Verificar
```bash
gcloud auth list
```

Deberías ver tu cuenta activa.

---

## 🚀 OPCIÓN 2: DEPLOY DESDE CONSOLA WEB (MÁS FÁCIL)

### Paso 1: Ir a Cloud Run Console
🔗 **URL:** https://console.cloud.google.com/run?project=stvaldiviacl

### Paso 2: Seleccionar Servicio
1. Busca el servicio `bimba`
2. Haz click en él

### Paso 3: Deploy Nueva Revisión
1. Click en **"DEPLOY NEW REVISION"**
2. Si está conectado a GitHub:
   - Selecciona el branch (ej: `main`)
   - Click **"DEPLOY"**
3. Si NO está conectado:
   - Sube el código manualmente o
   - Usa Cloud Build para construir desde el código local

---

## 🚀 OPCIÓN 3: DEPLOY AUTOMÁTICO (DESPUÉS DE AUTENTICARSE)

Una vez autenticado, ejecuta:

```bash
cd /Users/sebagatica/tickets_cursor_clean
bash deploy_cloud_run.sh
```

Este script:
- ✅ Verifica autenticación
- ✅ Configura el proyecto
- ✅ Construye la imagen desde código local (`--source .`)
- ✅ Despliega a Cloud Run
- ✅ Configura variables de entorno
- ✅ Muestra la URL del servicio

---

## 📋 CONFIGURACIÓN ACTUAL DEL SERVICIO

**Variables de entorno:**
- `FLASK_ENV=production`
- `FLASK_SECRET_KEY=<TU_FLASK_SECRET_KEY>`
- `DATABASE_URL=<tu_connection_string>`

**Especificaciones:**
- Memory: 512Mi
- CPU: 1
- Timeout: 300s
- Max instances: 10
- Min instances: 0

---

## ✅ VERIFICAR DEPLOY

Después del deploy:

```bash
# Ver logs
gcloud run services logs read bimba --region=southamerica-west1 --limit=50

# Obtener URL
gcloud run services describe bimba --region=southamerica-west1 --format="value(status.url)"

# Probar endpoint
curl https://bimba-5txce3rfsa-tl.a.run.app/api/v1/public/evento/hoy
```

---

## 🎯 RECOMENDACIÓN

**Si tienes problemas con la autenticación CLI:**
- Usa la **Opción 2** (Consola Web) - es más fácil y no requiere autenticación CLI

**Si ya estás autenticado:**
- Usa la **Opción 3** (Script automático) - es más rápido y mantiene la configuración

---

**Estado actual:** ⏳ **PENDIENTE AUTENTICACIÓN**









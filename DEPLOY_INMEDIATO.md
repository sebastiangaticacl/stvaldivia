# ⚡ DEPLOY INMEDIATO - INSTRUCCIONES

He creado un script automático que hace todo el deploy. Solo necesitas autenticarte primero.

---

## 🚀 EJECUTAR AHORA (2 pasos)

### PASO 1: Autenticarte
Abre tu terminal y ejecuta:
```bash
gcloud auth login
```
Esto abrirá tu navegador para autenticarte con Google.

### PASO 2: Ejecutar deploy automático
Una vez autenticado, ejecuta:
```bash
cd /Users/sebagatica/tickets
./deploy_cloud_run.sh
```

**El script hará todo automáticamente:**
- ✅ Configurar proyecto
- ✅ Habilitar APIs
- ✅ Construir imagen Docker
- ✅ Desplegar en Cloud Run
- ✅ Configurar todas las variables
- ✅ Probar el endpoint

---

## ⏱️ TIEMPO

- **Autenticación:** 1-2 minutos
- **Deploy:** 5-10 minutos
- **Total:** ~10-15 minutos

---

## 📋 QUÉ ESTÁ CONFIGURADO

El script ya tiene todo configurado:

✅ **Proyecto:** `stvaldiviacl`  
✅ **Región:** `southamerica-west1`  
✅ **Servicio:** `bimba`  
✅ **FLASK_SECRET_KEY:** Generado y configurado  
✅ **DATABASE_URL:** Configurado con Cloud SQL  
✅ **Recursos:** 512Mi RAM, 1 CPU, timeout 300s  

---

## 🔍 SI HAY PROBLEMAS

### "No hay cuenta autenticada"
```bash
gcloud auth login
```

### "Permission denied"
- Verifica permisos en el proyecto `stvaldiviacl`
- O cambia el proyecto en el script a `pelagic-river-479014-a3`

### "API not enabled"
El script las habilita automáticamente, pero si falla:
```bash
gcloud services enable run.googleapis.com cloudbuild.googleapis.com containerregistry.googleapis.com --project=stvaldiviacl
```

---

## ✅ DESPUÉS DEL DEPLOY

El script mostrará:
- URL del servicio Cloud Run
- Resultado del test
- Comandos para ver logs

**Ejemplo:**
```
✅ SERVICIO DESPLEGADO EXITOSAMENTE
📍 URL del servicio:
   https://bimba-xxxxx-xx.a.run.app
```

---

## 🎯 PRÓXIMOS PASOS

Después del deploy exitoso:
1. Crear Load Balancer con IP estática
2. Configurar DNS
3. SSL automático

---

**¿Listo?** Ejecuta los 2 comandos y el deploy se hará automáticamente.


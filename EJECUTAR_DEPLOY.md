# 🚀 EJECUTAR DEPLOY AUTOMÁTICO

He creado un script que hace todo el deploy automáticamente. Solo necesitas autenticarte primero.

---

## ⚡ PASO RÁPIDO (2 comandos)

### 1. Autenticarte en Google Cloud
```bash
gcloud auth login
```
Esto abrirá tu navegador para autenticarte.

### 2. Ejecutar el script de deploy
```bash
./deploy_cloud_run.sh
```

**¡Eso es todo!** El script hará:
- ✅ Configurar proyecto
- ✅ Habilitar APIs necesarias
- ✅ Construir imagen Docker
- ✅ Desplegar en Cloud Run
- ✅ Configurar variables de entorno
- ✅ Probar el endpoint

---

## 📋 QUÉ HACE EL SCRIPT

El script `deploy_cloud_run.sh` ejecuta:

1. **Verifica autenticación**
2. **Configura proyecto:** `stvaldiviacl`
3. **Habilita APIs:** Cloud Run, Cloud Build, Container Registry
4. **Configura variables de entorno:**
   - `FLASK_ENV=production`
   - `FLASK_SECRET_KEY` (ya configurado)
   - `DATABASE_URL` (ya configurado)
5. **Construye y despliega** el servicio `bimba`
6. **Obtiene URL** del servicio desplegado
7. **Prueba endpoint** para verificar que funciona

---

## ⏱️ TIEMPO ESTIMADO

- **Autenticación:** 1-2 minutos
- **Deploy:** 5-10 minutos (construcción de imagen Docker)
- **Total:** ~10-15 minutos

---

## 🔍 SI HAY ERRORES

### Error: "No hay cuenta autenticada"
```bash
gcloud auth login
```

### Error: "Permission denied"
- Verifica que tienes permisos de **Cloud Run Admin** o **Editor** en el proyecto `stvaldiviacl`
- O usa el proyecto `pelagic-river-479014-a3` si tienes permisos ahí

### Error: "API not enabled"
El script intenta habilitar las APIs automáticamente. Si falla:
```bash
gcloud services enable run.googleapis.com cloudbuild.googleapis.com containerregistry.googleapis.com --project=stvaldiviacl
```

### Error: "Build failed"
- Verifica que Dockerfile está en la raíz
- Verifica que requirements.txt tiene todas las dependencias
- Revisa logs: `gcloud builds list --limit=1`

---

## 📊 DESPUÉS DEL DEPLOY

El script mostrará:
- ✅ URL del servicio Cloud Run
- ✅ Resultado del test del endpoint
- ✅ Comandos útiles para ver logs

**Ejemplo de URL:**
```
https://bimba-xxxxx-xx.a.run.app
```

---

## 🎯 PRÓXIMOS PASOS DESPUÉS DEL DEPLOY

1. ✅ Servicio Cloud Run funcionando
2. ⏳ Crear Load Balancer con IP estática
3. ⏳ Configurar DNS para apuntar al Load Balancer
4. ⏳ SSL automático con Load Balancer

---

**¿Listo?** Ejecuta los 2 comandos arriba y el deploy se hará automáticamente.


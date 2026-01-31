# 🚨 SOLUCIÓN TEMPORAL: Error de Seguridad CSRF

## Problema
Error: "Error de seguridad. Por favor, recarga la página e intenta nuevamente."

Este error ocurre cuando CSRF está habilitado pero los tokens no se están enviando correctamente.

---

## ✅ SOLUCIÓN 1: Desactivar CSRF temporalmente (RÁPIDO)

### Opción A: Variable de entorno (RECOMENDADO)

En Cloud Run, agrega esta variable de entorno:

```bash
WTF_CSRF_ENABLED=false
```

### Opción B: Actualizar código y redeploy

1. **Los cambios ya están hechos en el código:**
   - ✅ CSRF deshabilitado en desarrollo
   - ✅ Login eximido de CSRF
   - ✅ Blueprint admin eximido de CSRF
   - ✅ Token CSRF agregado a JavaScript

2. **Desplegar a producción:**
   ```bash
   # Si ya estás autenticado:
   bash deploy_cloud_run.sh
   
   # Si no estás autenticado:
   # Primero autentícate (ver ACTUALIZAR_CLOUD_RUN.md)
   ```

---

## ✅ SOLUCIÓN 2: Verificar que login está eximido

El login debería estar eximido de CSRF, pero si el error persiste, verifica:

1. **Ver logs del servidor:**
   ```bash
   gcloud run services logs read bimba --region=southamerica-west1 --limit=50
   ```

2. **Buscar mensajes:**
   - `⚠️ Error CSRF:` - indica que CSRF está bloqueando
   - `🔓 CSRF deshabilitado en modo desarrollo` - indica que CSRF está deshabilitado

---

## 🔍 DIAGNÓSTICO

### Verificar configuración actual:

```bash
# Ver variables de entorno del servicio
gcloud run services describe bimba \
  --region=southamerica-west1 \
  --format="value(spec.template.spec.containers[0].env)"
```

### Verificar si CSRF está habilitado:

Busca la variable `WTF_CSRF_ENABLED` en las variables de entorno.

---

## 📋 CAMBIOS REALIZADOS EN EL CÓDIGO

1. ✅ **CSRF deshabilitado en desarrollo** (`app/__init__.py`)
2. ✅ **Blueprint admin eximido de CSRF** (`app/__init__.py`)
3. ✅ **Login eximido de CSRF** (`app/__init__.py`)
4. ✅ **Token CSRF agregado a JavaScript** (`app/templates/admin/payment_machines/list.html`)
5. ✅ **Context processor mejorado** para solo generar tokens cuando CSRF está habilitado

---

## 🎯 RECOMENDACIÓN

**Para resolver rápido:**
1. Agrega `WTF_CSRF_ENABLED=false` como variable de entorno en Cloud Run
2. O despliega los cambios actualizados (recomendado a largo plazo)

**Para mantener seguridad a largo plazo:**
1. Despliega los cambios actualizados que incluyen:
   - CSRF habilitado solo en producción
   - Blueprints de API eximidos de CSRF
   - Tokens CSRF en JavaScript cuando es necesario








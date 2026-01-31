# ✅ Checklist para Poner en Producción

## Pasos para Desplegar y Configurar GetNet

### 1. Desplegar Código a Cloud Run

```bash
# Opción A: Desde script (recomendado)
./deploy_cloud_run.sh

# Opción B: Desde consola web
# Ve a: https://console.cloud.google.com/run?project=stvaldiviacl
# Selecciona servicio 'bimba' → EDIT & DEPLOY NEW REVISION
```

### 2. Configurar Variables de Entorno en Cloud Run

**Variables Obligatorias para Pagos Reales:**

```bash
GETNET_LOGIN=tu_login_getnet
GETNET_TRANKEY=tu_trankey_getnet
PUBLIC_BASE_URL=https://stvaldivia.cl  # O la URL de tu Cloud Run
GETNET_API_BASE_URL=https://checkout.test.getnet.cl  # Sandbox
GETNET_DEMO_MODE=false
```

**Cómo configurarlas:**

1. Ve a [Cloud Run Console](https://console.cloud.google.com/run?project=stvaldiviacl)
2. Selecciona el servicio `bimba`
3. Click en **"EDIT & DEPLOY NEW REVISION"**
4. Expande **"Variables & Secrets"**
5. Agrega cada variable con **"ADD VARIABLE"**
6. Click en **"DEPLOY"**

### 3. Verificar que Funciona

```bash
# Ejecutar script de verificación
./verificar_produccion.sh

# O manualmente:
# 1. Obtener URL del servicio
gcloud run services describe bimba \
    --region=southamerica-west1 \
    --format="value(status.url)" \
    --project=stvaldiviacl

# 2. Probar endpoint de ecommerce
curl https://tu-url-cloud-run.run.app/ecommerce/
```

### 4. Verificar Base de Datos

Las tablas se crean automáticamente al iniciar el servicio. Para verificar:

```bash
# Ver logs del servicio
gcloud run services logs read bimba \
    --region=southamerica-west1 \
    --limit=50 \
    --project=stvaldiviacl

# Buscar: "✅ Base de datos inicializada (todas las tablas)"
```

### 5. Probar Checkout

1. Ve a `https://tu-url/ecommerce/`
2. Selecciona el evento "Preventa Año Nuevo BIMBA"
3. Completa el formulario
4. Verifica que:
   - Si `PUBLIC_BASE_URL` está configurado → redirige a GetNet (pago real)
   - Si no está configurado → usa modo demo (simulación)

## Checklist Final

- [ ] Código desplegado en Cloud Run
- [ ] `GETNET_LOGIN` configurado
- [ ] `GETNET_TRANKEY` configurado
- [ ] `PUBLIC_BASE_URL` configurado con URL pública
- [ ] `GETNET_API_BASE_URL` configurado
- [ ] `GETNET_DEMO_MODE=false` (o no configurado)
- [ ] Servicio responde correctamente
- [ ] Endpoint `/ecommerce/` funciona
- [ ] Base de datos inicializada (ver logs)
- [ ] Checkout probado y funcionando

## Documentación

- **Configuración completa:** `docs/CONFIGURACION_PRODUCCION_GETNET.md`
- **Funcionamiento GetNet:** `docs/GETNET_ONLINE_PAYMENT.md`
- **Script de deploy:** `deploy_cloud_run.sh`
- **Script de verificación:** `verificar_produccion.sh`

## Solución Rápida de Problemas

**Problema:** "Sesión no encontrada"
- **Solución:** Verifica que las tablas de base de datos estén creadas

**Problema:** "Se requiere PUBLIC_BASE_URL"
- **Solución:** Configura `PUBLIC_BASE_URL` con la URL pública de Cloud Run

**Problema:** "Credenciales de GetNet no configuradas"
- **Solución:** Configura `GETNET_LOGIN` y `GETNET_TRANKEY`

**Problema:** Modo demo activado cuando debería ser producción
- **Solución:** Verifica que `PUBLIC_BASE_URL` esté configurado y `GETNET_DEMO_MODE=false`

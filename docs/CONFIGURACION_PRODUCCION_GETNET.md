# Configuración de GetNet en Producción

Esta guía explica cómo configurar GetNet para pagos online en el entorno de producción (Cloud Run).

## Variables de Entorno Requeridas

### Variables Obligatorias para Pagos Reales

```bash
# Credenciales de GetNet (obligatorias para pagos reales)
GETNET_LOGIN=tu_login_getnet
GETNET_TRANKEY=tu_trankey_getnet

# URL pública para callbacks (obligatoria)
# Esta debe ser la URL pública de tu servicio Cloud Run o dominio personalizado
PUBLIC_BASE_URL=https://stvaldivia.cl

# API Base URL de GetNet
GETNET_API_BASE_URL=https://checkout.test.getnet.cl  # Sandbox
# GETNET_API_BASE_URL=https://checkout.getnet.cl  # Producción

# Desactivar modo demo
GETNET_DEMO_MODE=false
```

### Variables Opcionales

```bash
# Si no configuras GETNET_LOGIN y GETNET_TRANKEY, el sistema usará modo demo automáticamente
# El modo demo también se activa si PUBLIC_BASE_URL no está configurado
```

## Configuración en Cloud Run

### Opción 1: Desde la Consola Web

1. Ve a [Cloud Run Console](https://console.cloud.google.com/run?project=stvaldiviacl)
2. Selecciona el servicio `bimba`
3. Click en **"EDIT & DEPLOY NEW REVISION"**
4. Expande la sección **"Variables & Secrets"**
5. Agrega las variables de entorno:
   - `GETNET_LOGIN`
   - `GETNET_TRANKEY`
   - `PUBLIC_BASE_URL`
   - `GETNET_API_BASE_URL`
   - `GETNET_DEMO_MODE=false`
6. Click en **"DEPLOY"**

### Opción 2: Desde el Script de Deploy

Edita el archivo `deploy_cloud_run.sh` y configura las variables:

```bash
# Variables de GetNet
export GETNET_LOGIN="tu_login_getnet"
export GETNET_TRANKEY="tu_trankey_getnet"
export PUBLIC_BASE_URL="https://stvaldivia.cl"
export GETNET_API_BASE_URL="https://checkout.test.getnet.cl"
export GETNET_DEMO_MODE="false"
```

Luego ejecuta:
```bash
./deploy_cloud_run.sh
```

### Opción 3: Desde gcloud CLI

```bash
gcloud run services update bimba \
    --region=southamerica-west1 \
    --set-env-vars="GETNET_LOGIN=tu_login,GETNET_TRANKEY=tu_trankey,PUBLIC_BASE_URL=https://stvaldivia.cl,GETNET_API_BASE_URL=https://checkout.test.getnet.cl,GETNET_DEMO_MODE=false" \
    --project=stvaldiviacl
```

## Verificación

### 1. Verificar Variables Configuradas

```bash
gcloud run services describe bimba \
    --region=southamerica-west1 \
    --format="value(spec.template.spec.containers[0].env)" \
    --project=stvaldiviacl
```

### 2. Verificar que el Servicio Funciona

```bash
./verificar_produccion.sh
```

### 3. Probar Checkout

1. Ve a `https://stvaldivia.cl/ecommerce/`
2. Selecciona un evento
3. Completa el formulario de checkout
4. Verifica que se redirige a GetNet (no a modo demo)

## Modo Demo vs Producción

El sistema detecta automáticamente el modo:

- **Modo Demo** se activa cuando:
  - `GETNET_DEMO_MODE=true` está configurado
  - O cuando `PUBLIC_BASE_URL` no está configurado
  - O cuando las credenciales no están configuradas

- **Modo Producción** se activa cuando:
  - `PUBLIC_BASE_URL` está configurado con una URL pública
  - Y `GETNET_LOGIN` y `GETNET_TRANKEY` están configurados
  - Y `GETNET_DEMO_MODE` no está en `true`

## Solución de Problemas

### Error: "Se requiere PUBLIC_BASE_URL configurado"

**Solución:** Configura `PUBLIC_BASE_URL` con la URL pública de tu servicio Cloud Run.

Para obtener la URL:
```bash
gcloud run services describe bimba \
    --region=southamerica-west1 \
    --format="value(status.url)" \
    --project=stvaldiviacl
```

### Error: "Credenciales de GetNet no configuradas"

**Solución:** Configura `GETNET_LOGIN` y `GETNET_TRANKEY` con tus credenciales de GetNet.

### Error: "403 Forbidden" desde GetNet

**Posibles causas:**
1. Credenciales incorrectas
2. URL de callback no accesible desde internet
3. Endpoint incorrecto

**Solución:**
1. Verifica que las credenciales sean correctas
2. Verifica que `PUBLIC_BASE_URL` sea accesible desde internet
3. Revisa los logs para ver qué endpoint está fallando

### Ver Logs

```bash
gcloud run services logs read bimba \
    --region=southamerica-west1 \
    --limit=100 \
    --project=stvaldiviacl
```

Busca en los logs:
- `🔧 MODO DEMO` - Indica que está en modo demo
- `Creando pago PlaceToPay/GetNet` - Indica intento de pago real
- `Respuesta PlaceToPay/GetNet: status=` - Muestra el código de respuesta

## Checklist de Producción

- [ ] `GETNET_LOGIN` configurado
- [ ] `GETNET_TRANKEY` configurado
- [ ] `PUBLIC_BASE_URL` configurado con URL pública
- [ ] `GETNET_API_BASE_URL` configurado (sandbox o producción)
- [ ] `GETNET_DEMO_MODE=false` (o no configurado)
- [ ] Servicio Cloud Run desplegado
- [ ] URL del servicio accesible desde internet
- [ ] Probar checkout y verificar que redirige a GetNet

## Notas Importantes

1. **Sandbox vs Producción**: Usa credenciales de sandbox para pruebas, producción para pagos reales
2. **URLs Públicas**: GetNet necesita poder acceder a las URLs de callback desde internet
3. **SSL/TLS**: Las URLs deben usar HTTPS
4. **Callbacks**: Los callbacks pueden tardar algunos segundos en llegar




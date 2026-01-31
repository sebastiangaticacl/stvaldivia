# Configuración de Pagos Online con GetNet

Este documento explica cómo configurar el sistema de pagos online con GetNet para que funcione en producción.

## Requisitos para Pagos Online Reales

Para que el sistema procese pagos reales con GetNet (no modo demo), se requieren las siguientes configuraciones:

### 1. Variables de Entorno Requeridas

```bash
# Credenciales de GetNet (obligatorias)
GETNET_LOGIN=tu_login_getnet
GETNET_TRANKEY=tu_trankey_getnet

# URL pública para callbacks (obligatoria para producción)
# GetNet necesita poder acceder a esta URL desde internet para enviar callbacks
PUBLIC_BASE_URL=https://stvaldivia.cl

# API Base URL de GetNet (opcional, por defecto usa sandbox)
GETNET_API_BASE_URL=https://checkout.test.getnet.cl  # Sandbox
# GETNET_API_BASE_URL=https://checkout.getnet.cl  # Producción

# Desactivar modo demo (opcional, se desactiva automáticamente si hay PUBLIC_BASE_URL)
GETNET_DEMO_MODE=false
```

### 2. Modo Demo vs Producción

El sistema detecta automáticamente si debe usar modo demo o producción:

- **Modo Demo se activa cuando:**
  - `GETNET_DEMO_MODE=true` está configurado explícitamente
  - O cuando la URL de callback es localhost/127.0.0.1 y no hay `PUBLIC_BASE_URL` configurado

- **Modo Producción se activa cuando:**
  - `PUBLIC_BASE_URL` está configurado con una URL pública (ej: `https://stvaldivia.cl`)
  - Y `GETNET_DEMO_MODE` no está en `true`

### 3. Configuración para Desarrollo Local con Tunneling

Si quieres probar pagos reales en desarrollo local, puedes usar herramientas como ngrok:

```bash
# Instalar ngrok
# https://ngrok.com/

# Crear túnel
ngrok http 5001

# Configurar PUBLIC_BASE_URL con la URL de ngrok
export PUBLIC_BASE_URL=https://tu-url-ngrok.ngrok.io
```

### 4. Estructura de Callbacks

El sistema genera automáticamente las URLs de callback:
- **Return URL**: `{PUBLIC_BASE_URL}/ecommerce/payment/callback/{session_id}`
- **Cancel URL**: `{PUBLIC_BASE_URL}/ecommerce/payment/cancelled/{session_id}`

Estas URLs deben ser accesibles públicamente desde internet para que GetNet pueda enviar los callbacks.

### 5. Verificación de Configuración

El sistema registra en los logs información sobre la configuración:
- Si está en modo demo o producción
- La URL pública configurada
- Si las credenciales están configuradas
- Los endpoints que se están intentando

Revisa los logs en `logs/app.log` para diagnosticar problemas.

### 6. Endpoints de GetNet

El sistema intenta múltiples endpoints posibles:
1. `/api/session` (endpoint oficial según documentación)
2. `/api/collect`
3. `/checkout/api/session`
4. `/checkout/api/collect`
5. `/api/v1/payment`
6. `/api/payment`

Si un endpoint falla, el sistema automáticamente prueba el siguiente.

### 7. Autenticación

El sistema usa autenticación PlaceToPay estándar:
- **Algoritmo**: SHA1 (según ejemplo oficial Java)
- **Formato**: `SHA1(nonce + seed + trankey)` codificado en base64
- **Seed**: Timestamp ISO 8601 formato `yyyy-MM-dd'T'HH:mmZ`
- **Nonce**: Valor aleatorio hexadecimal codificado en base64

### 8. Solución de Problemas

**Error: "Se requiere PUBLIC_BASE_URL configurado"**
- Configura `PUBLIC_BASE_URL` con una URL pública accesible desde internet

**Error: "Credenciales de GetNet no configuradas"**
- Verifica que `GETNET_LOGIN` y `GETNET_TRANKEY` estén configurados

**Error: "403 Forbidden"**
- Verifica que las credenciales sean correctas
- Verifica que la URL pública sea accesible desde internet
- Revisa los logs para ver qué endpoint está fallando

**Error: "Timeout" o "Connection Error"**
- Verifica la conectividad a internet
- Verifica que `GETNET_API_BASE_URL` sea correcto
- Revisa si hay firewall bloqueando las conexiones

### 9. Ejemplo de Configuración Completa (.env)

```bash
# GetNet Configuration
GETNET_API_BASE_URL=https://checkout.test.getnet.cl
GETNET_LOGIN=tu_login_getnet
GETNET_TRANKEY=tu_trankey_getnet
PUBLIC_BASE_URL=https://stvaldivia.cl
GETNET_DEMO_MODE=false
```

### 10. Notas Importantes

- **Sandbox vs Producción**: Asegúrate de usar las credenciales correctas según el ambiente
- **SSL/TLS**: Las URLs públicas deben usar HTTPS (GetNet requiere conexiones seguras)
- **Callbacks**: Los callbacks pueden tardar algunos segundos en llegar después del pago
- **Logs**: Revisa siempre los logs para diagnosticar problemas de integración




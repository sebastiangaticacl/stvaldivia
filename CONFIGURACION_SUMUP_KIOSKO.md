# 💳 Configuración SumUp para TPV Kiosko

## 📋 Resumen

Se ha implementado la integración de SumUp para permitir pagos sin contacto (Apple Pay, Google Pay) en los TPV Kiosko. Los clientes pueden escanear un código QR con su móvil y pagar directamente sin ir a la caja.

---

## 🔧 Configuración Requerida

### 1. Variables de Entorno

Agregar las siguientes variables de entorno:

```bash
# API Key de SumUp (obligatorio)
# Según documentación oficial: https://developer.sumup.com/api/authentication
# - Test mode: prefijo sk_test_ (para sandbox)
# - Live mode: prefijo sk_live_ (para producción)
# También disponibles: restricted API keys para permisos granulares
# Obtener desde: https://me.sumup.com/developers/api-keys
SUMUP_API_KEY=sk_test_xxxxx  # Para sandbox/testing
# SUMUP_API_KEY=sk_live_xxxxx  # Para producción

# Código del comerciante SumUp (opcional, pero recomendado)
SUMUP_MERCHANT_CODE=MH4H92C7

# URL pública para callbacks (obligatorio para producción)
PUBLIC_BASE_URL=https://stvaldivia.cl
```

### 2. Ejecutar Migración de Base de Datos

Aplicar la migración para agregar campos SumUp a la tabla `pagos`:

```bash
# MySQL
mysql -u usuario -p bimba_db < migrations/2025_01_15_add_sumup_fields_to_pagos_mysql.sql
```

O ejecutar manualmente las sentencias SQL si es necesario.

---

## 📚 Endpoints API Creados

### 1. Crear Checkout SumUp
**POST** `/kiosk/api/pagos/sumup/create`

Crea un checkout de SumUp para un pedido del kiosko.

**Body:**
```json
{
  "carrito": [
    {
      "id": "123",
      "nombre": "Producto",
      "cantidad": 2,
      "precio": 5000,
      "total": 10000
    }
  ]
}
```

**Response:**
```json
{
  "ok": true,
  "pago_id": 123,
  "checkout_id": "4e425463-3e1b-431d-83fa-1e51c2925e99",
  "checkout_url": "https://pay.sumup.com/...",
  "checkout_reference": "KIOSK-123-20250115123456"
}
```

### 2. Obtener QR del Checkout
**GET** `/kiosk/api/pagos/sumup/qr/<pago_id>`

Genera un código QR con la URL del checkout SumUp.

**Response:**
```json
{
  "ok": true,
  "qr_image": "data:image/png;base64,...",
  "checkout_url": "https://pay.sumup.com/...",
  "pago_id": 123
}
```

### 3. Callback de Pago
**GET/POST** `/kiosk/sumup/callback/<pago_id>`

Endpoint al que SumUp redirige después del pago. Verifica el estado del checkout y actualiza el pago.

### 4. Webhook SumUp
**POST** `/kiosk/api/sumup/webhook`

Endpoint para recibir notificaciones de SumUp sobre cambios en el estado de los checkouts.

**Nota:** Este endpoint debe estar configurado en el dashboard de SumUp.

---

## 🔄 Flujo de Pago

1. **Cliente selecciona productos** en el kiosko
2. **Cliente presiona "Pagar con SumUp"** en el checkout
3. **Sistema crea checkout SumUp** y redirige a pantalla con QR
4. **Cliente escanea QR** con su móvil
5. **Cliente completa pago** con Apple Pay/Google Pay en SumUp
6. **SumUp redirige al callback** o envía webhook
7. **Sistema verifica estado** y marca pago como PAID
8. **Sistema sincroniza con PHP POS** y genera ticket
9. **Cliente recibe QR/ticket** para recoger en caja

---

## 🛠️ Componentes Implementados

### 1. SumUpClient
**Archivo:** `app/infrastructure/external/sumup_client.py`

Cliente para interactuar con la API de SumUp:
- `create_checkout()` - Crea un checkout
- `get_checkout()` - Obtiene estado de un checkout
- `process_checkout()` - Procesa un checkout

### 2. Modelo Pago Actualizado
**Archivo:** `app/models/kiosk_models.py`

Nuevos campos agregados:
- `sumup_checkout_id` - ID del checkout SumUp
- `sumup_checkout_url` - URL del checkout para generar QR
- `sumup_merchant_code` - Código del comerciante

### 3. Rutas del Kiosko
**Archivo:** `app/blueprints/kiosk/routes.py`

Nuevas rutas:
- `/kiosk/sumup/payment/<pago_id>` - Pantalla con QR de pago
- `/kiosk/api/pagos/sumup/create` - API para crear checkout
- `/kiosk/api/pagos/sumup/qr/<pago_id>` - API para obtener QR
- `/kiosk/sumup/callback/<pago_id>` - Callback de SumUp
- `/kiosk/api/sumup/webhook` - Webhook de SumUp

### 4. Templates
- `app/templates/kiosk/kiosk_sumup_payment.html` - Pantalla con QR de pago
- `app/templates/kiosk/kiosk_checkout.html` - Actualizado con botón SumUp

---

## ⚙️ Configuración del Webhook en SumUp

1. Acceder al dashboard de SumUp
2. Ir a Configuración → Webhooks
3. Agregar webhook con URL:
   ```
   https://stvaldivia.cl/kiosk/api/sumup/webhook
   ```
4. Seleccionar eventos:
   - `checkout.succeeded`
   - `checkout.failed`
   - `checkout.expired`

---

## 🔍 Verificación y Testing

### Testing en Sandbox

1. Usar API key de sandbox (`sk_test_...`)
2. Probar flujo completo con checkout de prueba
3. Verificar que los pagos se crean correctamente
4. Verificar sincronización con PHP POS

### Verificación en Producción

1. Configurar API key de producción (`sk_live_...`)
2. Verificar que `PUBLIC_BASE_URL` está configurado
3. Probar con un pago real pequeño
4. Verificar logs para errores

---

## 📝 Notas Importantes

1. **CSRF:** Los endpoints de webhook y callback están exentos de CSRF
2. **URLs Públicas:** El callback requiere que `PUBLIC_BASE_URL` esté configurado
3. **Sincronización PHP POS:** Se ejecuta automáticamente después de confirmar el pago
4. **Estados de Pago:** `PENDING` → `PAID` o `FAILED`
5. **Timeout:** Los checkouts pueden expirar si no se procesan a tiempo

---

## 🐛 Troubleshooting

### Error: "API key no configurada"
- Verificar que `SUMUP_API_KEY` esté en variables de entorno
- Verificar que la key sea válida (formatos: `sup_sk_...`, `sk_test_...`, o `sk_live_...`)
- Obtener tu API key desde el [SumUp Dashboard](https://me.sumup.com/developers/api-keys)

### Error: "No se pudo generar el código QR"
- Verificar que el checkout se haya creado correctamente
- Verificar logs para ver el error específico de SumUp

### Pago no se marca como PAID
- Verificar que el webhook esté configurado en SumUp
- Verificar que `PUBLIC_BASE_URL` esté configurado correctamente
- Revisar logs del webhook endpoint

### No sincroniza con PHP POS
- Verificar que `API_KEY` y `BASE_API_URL` estén configurados
- Verificar logs de sincronización
- El pago se marca como PAID aunque falle la sincronización

---

## 📚 Referencias

- [Documentación API SumUp](https://developer.sumup.com/api)
- [SumUp Checkouts API](https://developer.sumup.com/api#tag/Checkouts)
- Evaluación de viabilidad: `EVALUACION_SUMUP_KIOSKO.md`


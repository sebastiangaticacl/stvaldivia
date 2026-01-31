# 📝 Notas sobre la API de SumUp

Basado en la documentación oficial: https://developer.sumup.com/api

## 🔑 Autenticación

### Formato de API Keys

Según la [documentación oficial de autenticación](https://developer.sumup.com/api/authentication):

- **Test mode:** `sk_test_xxxxx` - Para sandbox/testing
- **Live mode:** `sk_live_xxxxx` - Para producción
- **Restricted API keys:** También disponibles para permisos granulares

**Obtener API keys:** [SumUp Dashboard - API Keys](https://me.sumup.com/developers/api-keys)

### Autenticación en Requests

```bash
Authorization: Bearer {API_KEY}
```

**Requisitos:**
- Todos los requests deben incluir el header `Authorization: Bearer {api_key}`
- Todos los requests deben ser **HTTPS** (no HTTP)
- Las API keys deben mantenerse secretas y no exponerse en código cliente
- No compartir API keys públicamente (GitHub, etc.)

**Referencia:** [SumUp Authentication Documentation](https://developer.sumup.com/api/authentication)

## 🌐 Base URL

```
https://api.sumup.com
```

Versión de API: `v0.1`

## 💳 Checkouts API

### Crear Checkout

**Endpoint:** `POST /v0.1/checkouts`

**Body Parameters:**
- `amount` (number, required) - Monto del pago
- `currency` (string, required) - Código ISO4217 (ej: "CLP", "EUR")
- `checkout_reference` (string, optional) - ID único especificado por la app
- `description` (string, optional) - Descripción visible en dashboard
- `return_url` (string, optional) - URL a la que redirigir después del pago
- `customer_id` (string, optional) - ID del cliente
- `merchant_code` (string, optional) - Código del comerciante

**Response:**
```json
{
  "id": "4e425463-3e1b-431d-83fa-1e51c2925e99",
  "status": "PENDING",
  "amount": 10.1,
  "currency": "EUR",
  "checkout_reference": "ref-123",
  "date": "2020-02-29T10:56:56+00:00",
  "return_url": "https://example.com/return",
  ...
}
```

### Estados de Checkout

- `PENDING` - Pendiente de pago
- `PAID` - Pagado exitosamente
- `FAILED` - Pago fallido
- `EXPIRED` - Checkout expirado

### Obtener Checkout

**Endpoint:** `GET /v0.1/checkouts/{checkout_id}`

Retorna información completa del checkout incluyendo su estado actual.

### Procesar Checkout

**Endpoint:** `POST /v0.1/checkouts/{checkout_id}/process`

Inicia el flujo de pago del checkout. Generalmente se usa cuando se quiere procesar el pago directamente, aunque el flujo más común es usar `return_url` para redirección.

## 🔄 Flujo de Pago Recomendado

1. **Crear checkout** con `return_url`
2. **Obtener URL de pago** desde la respuesta (puede estar en `redirect_url` o `href`)
3. **Redirigir al usuario** a la URL de SumUp
4. **Usuario completa pago** (Apple Pay, Google Pay, tarjeta)
5. **SumUp redirige a `return_url`** con información del checkout
6. **Verificar estado** del checkout usando el ID recibido
7. **Actualizar sistema** según el estado (PAID, FAILED, etc.)

## 📡 Webhooks

SumUp soporta webhooks para recibir notificaciones sobre cambios en el estado de los checkouts.

**Eventos disponibles:**
- `checkout.succeeded` / `checkout.paid` - Pago exitoso
- `checkout.failed` - Pago fallido
- `checkout.expired` - Checkout expirado

**Configuración:**
1. Ir a SumUp Dashboard
2. Configuración → Webhooks
3. Agregar URL del webhook endpoint
4. Seleccionar eventos a escuchar

## 🧪 Sandbox

SumUp ofrece un sandbox para pruebas sin procesar transacciones reales:

1. Crear cuenta de sandbox en el dashboard
2. Generar API key de sandbox (`sk_test_...`)
3. Usar la misma API pero con keys de test

## 📚 Recursos Adicionales

- **SDKs oficiales:** PHP, Node.js, Python, Go, Rust
- **Documentación:** https://developer.sumup.com/api
- **Dashboard:** https://me.sumup.com/developers
- **Postman Collection:** Disponible en la documentación

## ⚠️ Notas de Implementación

1. **URLs Públicas:** Los `return_url` y webhooks deben ser accesibles desde internet
2. **HTTPS:** Todas las requests deben ser HTTPS
3. **Seguridad:** Nunca exponer API keys en código del cliente
4. **Idempotencia:** Usar `checkout_reference` único para evitar duplicados
5. **Verificación:** Siempre verificar el estado del checkout después de recibir callback/webhook

## 🔍 Ejemplo de Integración

```python
from sumup_client import SumUpClient

# Inicializar cliente
client = SumUpClient(api_key="sup_sk_xxxxx")

# Crear checkout
result = client.create_checkout(
    amount=10000.0,
    currency="CLP",
    checkout_reference="pedido-123",
    description="Pedido desde kiosko",
    return_url="https://example.com/callback",
    merchant_code="MH4H92C7"
)

if result['success']:
    checkout_data = result['data']
    checkout_id = checkout_data['id']
    checkout_url = checkout_data.get('redirect_url') or checkout_data.get('href')
    
    # Redirigir usuario a checkout_url o generar QR
    # Usuario completa pago en SumUp
    # SumUp redirige a return_url
    # Verificar estado con get_checkout(checkout_id)
```


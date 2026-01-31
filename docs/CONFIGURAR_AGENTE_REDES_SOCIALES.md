# 🤖 Configurar Agente Unificado para Redes Sociales

## 📋 Resumen

El sistema ahora incluye un **agente unificado** que responde automáticamente en:
- ✅ **WhatsApp**
- ✅ **Instagram**
- ✅ **Facebook Messenger**

Todos usan el mismo **cerebro de análisis del sitio** para generar respuestas inteligentes basadas en el conocimiento real del negocio.

## 🧠 Arquitectura

```
┌─────────────────────────────────────────┐
│   Cerebro de Análisis (SiteAnalyzer)   │
│   - Analiza el sitio web                │
│   - Extrae: productos, eventos, horarios │
│   - Genera contexto relevante           │
└─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────┐
│  Agente Unificado (UnifiedSocialAgent)  │
│  - Usa conocimiento del sitio           │
│  - Genera respuestas con OpenAI         │
│  - Adapta tono según plataforma         │
└─────────────────────────────────────────┘
                    │
        ┌───────────┼───────────┐
        ▼           ▼           ▼
    WhatsApp    Instagram    Facebook
```

## 🔧 Configuración

### Variables de Entorno

Agregar a `/etc/stvaldivia/stvaldivia.env`:

```bash
# OpenAI (requerido para todas las plataformas)
OPENAI_API_KEY=tu_openai_api_key

# WhatsApp - Opción 1: Twilio
WHATSAPP_PROVIDER=twilio
TWILIO_ACCOUNT_SID=tu_account_sid
TWILIO_AUTH_TOKEN=tu_auth_token
WHATSAPP_FROM_NUMBER=whatsapp:+14155238886

# WhatsApp - Opción 2: WhatsApp Cloud API
WHATSAPP_PROVIDER=whatsapp_cloud
WHATSAPP_TOKEN=tu_access_token
WHATSAPP_PHONE_NUMBER_ID=tu_phone_number_id
WHATSAPP_VERIFY_TOKEN=tu_verify_token

# Instagram (Meta)
INSTAGRAM_VERIFY_TOKEN=tu_verify_token
INSTAGRAM_PAGE_ACCESS_TOKEN=tu_page_access_token
INSTAGRAM_BUSINESS_ACCOUNT_ID=tu_business_account_id
META_APP_ID=tu_app_id
META_APP_SECRET=tu_app_secret

# Facebook Messenger (Meta)
FACEBOOK_VERIFY_TOKEN=tu_verify_token  # Puede ser el mismo que Instagram
FACEBOOK_PAGE_ACCESS_TOKEN=tu_page_access_token
FACEBOOK_PAGE_ID=tu_page_id
FACEBOOK_APP_SECRET=tu_app_secret  # Puede ser META_APP_SECRET
```

## 📱 Configuración por Plataforma

### 1. WhatsApp

#### Opción A: Twilio

1. Crear cuenta en [Twilio](https://www.twilio.com/)
2. Obtener credenciales:
   - Account SID
   - Auth Token
   - Número de WhatsApp
3. Configurar webhook:
   - URL: `https://stvaldivia.cl/api/whatsapp/webhook`
   - Método: POST

#### Opción B: WhatsApp Cloud API (Meta)

1. Crear app en [Meta for Developers](https://developers.facebook.com/)
2. Configurar WhatsApp Business API
3. Configurar webhook:
   - URL: `https://stvaldivia.cl/api/whatsapp/webhook`
   - Verify Token: (el que configuraste)
   - Suscribirse a: `messages`

### 2. Instagram

1. En [Meta for Developers](https://developers.facebook.com/):
   - Crear app o usar la misma de WhatsApp
   - Configurar Instagram Basic Display API
   - Obtener Page Access Token
   - Obtener Business Account ID
2. Configurar webhook:
   - URL: `https://stvaldivia.cl/webhook/instagram`
   - Verify Token: (el que configuraste)
   - Suscribirse a: `messages`

### 3. Facebook Messenger

1. En [Meta for Developers](https://developers.facebook.com/):
   - Usar la misma app de Instagram/WhatsApp
   - Configurar Messenger Product
   - Obtener Page Access Token
   - Obtener Page ID
2. Configurar webhook:
   - URL: `https://stvaldivia.cl/webhook/facebook`
   - Verify Token: (el que configuraste)
   - Suscribirse a: `messages`, `messaging_postbacks`

## 🌐 Endpoints Disponibles

### WhatsApp
- `POST /api/whatsapp/webhook` - Recibir mensajes
- `GET /api/whatsapp/webhook` - Verificación
- `POST /api/whatsapp/refresh-knowledge` - Actualizar conocimiento
- `POST /api/whatsapp/test` - Probar envío

### Instagram
- `POST /webhook/instagram` - Recibir mensajes
- `GET /webhook/instagram` - Verificación
- `POST /webhook/instagram/test` - Probar

### Facebook
- `POST /webhook/facebook` - Recibir mensajes
- `GET /webhook/facebook` - Verificación
- `POST /webhook/facebook/test` - Probar

## 🎯 Características del Agente

### ✅ Conocimiento del Sitio
- Analiza automáticamente el sitio web
- Extrae: productos, eventos, horarios, contacto, FAQs
- Genera contexto relevante para cada consulta
- Se actualiza automáticamente cada 24 horas

### ✅ Respuestas Inteligentes
- Usa OpenAI (gpt-4o-mini) para generar respuestas
- Adapta el tono según la plataforma:
  - **WhatsApp**: Más casual, emojis ocasionales
  - **Instagram**: Conciso (menos de 200 caracteres)
  - **Facebook**: Puede ser más detallado
- Mantiene historial de conversación
- Fallback inteligente si OpenAI falla

### ✅ Logs Completos
- Todas las conversaciones se guardan en `bot_logs`
- Filtrable por plataforma: `canal='whatsapp'`, `'instagram'`, `'facebook'`
- Ver en: `/admin/bot/logs?canal=whatsapp`

## 🧪 Pruebas

### Probar WhatsApp
```bash
curl -X POST https://stvaldivia.cl/api/whatsapp/test \
  -H "Content-Type: application/json" \
  -d '{
    "to": "+56912345678",
    "message": "Hola! Este es un mensaje de prueba"
  }'
```

### Probar Instagram
```bash
curl -X POST https://stvaldivia.cl/webhook/instagram/test \
  -H "Content-Type: application/json" \
  -d '{
    "sender_id": "test_user_123",
    "message": "Hola, ¿cuáles son los horarios?"
  }'
```

### Probar Facebook
```bash
curl -X POST https://stvaldivia.cl/webhook/facebook/test \
  -H "Content-Type: application/json" \
  -d '{
    "sender_id": "test_user_123",
    "message": "Hola, ¿qué eventos tienen?"
  }'
```

(Requiere autenticación admin)

## 🔄 Actualizar Conocimiento

Para forzar actualización del conocimiento del sitio:

```bash
curl -X POST https://stvaldivia.cl/api/whatsapp/refresh-knowledge
```

(Requiere autenticación admin)

## 📊 Monitoreo

### Ver Logs de Conversaciones

```sql
-- Ver últimas conversaciones de WhatsApp
SELECT * FROM bot_logs 
WHERE canal = 'whatsapp' 
ORDER BY timestamp DESC 
LIMIT 20;

-- Ver últimas conversaciones de Instagram
SELECT * FROM bot_logs 
WHERE canal = 'instagram' 
ORDER BY timestamp DESC 
LIMIT 20;

-- Ver últimas conversaciones de Facebook
SELECT * FROM bot_logs 
WHERE canal = 'facebook' 
ORDER BY timestamp DESC 
LIMIT 20;
```

### Panel Admin

```
/admin/bot/logs?canal=whatsapp
/admin/bot/logs?canal=instagram
/admin/bot/logs?canal=facebook
```

## 🎨 Personalización

### Ajustar Tono por Plataforma

Editar `app/application/services/unified_social_agent_service.py`:

```python
platform_instructions = {
    'whatsapp': 'Tu instrucción personalizada para WhatsApp',
    'instagram': 'Tu instrucción personalizada para Instagram',
    'facebook': 'Tu instrucción personalizada para Facebook'
}
```

### Ajustar Longitud de Respuestas

```python
max_tokens_map = {
    'whatsapp': 200,    # Ajustar según necesidad
    'instagram': 150,   # Ajustar según necesidad
    'facebook': 250      # Ajustar según necesidad
}
```

## 🐛 Troubleshooting

### El agente no responde en una plataforma
1. Verificar que las credenciales estén configuradas
2. Verificar que el webhook esté correctamente configurado
3. Revisar logs: `journalctl -u stvaldivia -f`
4. Probar con el endpoint de test

### Las respuestas no usan el conocimiento del sitio
1. Forzar actualización: `POST /api/whatsapp/refresh-knowledge`
2. Verificar que el sitio sea accesible
3. Revisar logs del `SiteAnalyzer`

### OpenAI no responde
1. Verificar que `OPENAI_API_KEY` esté configurada
2. Verificar que la API key sea válida
3. El agente usará respuestas de fallback automáticamente

## 📚 Archivos Clave

- `app/helpers/site_analyzer.py` - Cerebro de análisis
- `app/application/services/unified_social_agent_service.py` - Agente unificado
- `app/routes/whatsapp_routes.py` - Webhooks de WhatsApp
- `app/routes_instagram.py` - Webhooks de Instagram
- `app/routes/facebook_routes.py` - Webhooks de Facebook

---

**✅ El agente está listo para responder en las 3 plataformas usando el conocimiento del sitio.**


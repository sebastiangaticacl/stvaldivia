# 🤖 Guía: Agente de WhatsApp con Cerebro de Análisis del Sitio

## 📋 Resumen

Se ha implementado un sistema completo que incluye:

1. **Cerebro de Análisis del Sitio** (`SiteAnalyzer`): Analiza el sitio web para extraer conocimiento sobre el negocio
2. **Agente de WhatsApp** (`WhatsAppAgentService`): Responde mensajes usando el conocimiento del sitio y OpenAI

## 🧠 Componente 1: Cerebro de Análisis del Sitio

### Ubicación
- `app/helpers/site_analyzer.py`

### Funcionalidad
- Analiza el sitio web completo (página principal, menú, eventos, etc.)
- Extrae información estructurada:
  - Información del negocio (nombre, descripción)
  - Productos y precios
  - Eventos
  - Horarios
  - Información de contacto
  - Redes sociales
  - FAQs
- Genera contexto relevante para consultas específicas
- Cache de 24 horas para optimizar rendimiento

### Uso

```python
from app.helpers.site_analyzer import SiteAnalyzer

analyzer = SiteAnalyzer(base_url="https://stvaldivia.cl")
knowledge = analyzer.analyze_site()

# Obtener resumen del conocimiento
summary = analyzer.get_knowledge_summary()

# Obtener contexto para una consulta específica
context = analyzer.get_context_for_query("¿Cuáles son los horarios?")
```

## 📱 Componente 2: Agente de WhatsApp

### Ubicación
- `app/application/services/whatsapp_agent_service.py`
- `app/infrastructure/external/whatsapp_client.py`
- `app/routes/whatsapp_routes.py`

### Funcionalidad
- Recibe mensajes de WhatsApp vía webhooks
- Usa el conocimiento del sitio para generar respuestas contextuales
- Integra con OpenAI para respuestas inteligentes
- Mantiene historial de conversación
- Guarda logs de todas las conversaciones

### Endpoints

#### 1. Webhook de WhatsApp
```
POST /api/whatsapp/webhook
GET /api/whatsapp/webhook (verificación)
```

Recibe mensajes de WhatsApp y responde automáticamente.

#### 2. Refrescar conocimiento
```
POST /api/whatsapp/refresh-knowledge
```

Fuerza una actualización del conocimiento del sitio (requiere autenticación admin).

#### 3. Test de envío
```
POST /api/whatsapp/test
```

Envía un mensaje de prueba (requiere autenticación admin).

## 🔧 Configuración

### Variables de Entorno

Agregar a `/etc/stvaldivia/stvaldivia.env`:

```bash
# WhatsApp Configuration
WHATSAPP_PROVIDER=twilio  # o 'whatsapp_cloud'

# Opción 1: Twilio
TWILIO_ACCOUNT_SID=tu_account_sid
TWILIO_AUTH_TOKEN=tu_auth_token
WHATSAPP_FROM_NUMBER=whatsapp:+14155238886

# Opción 2: WhatsApp Cloud API
WHATSAPP_BUSINESS_ID=tu_business_id
WHATSAPP_TOKEN=tu_access_token
WHATSAPP_PHONE_NUMBER_ID=tu_phone_number_id
WHATSAPP_VERIFY_TOKEN=tu_verify_token_secreto

# OpenAI (ya debería estar configurado)
OPENAI_API_KEY=tu_openai_api_key
```

### Dependencias

Agregar a `requirements.txt` (ya agregado):
```
beautifulsoup4==4.12.2
```

## 🚀 Configuración de WhatsApp

### Opción A: Twilio

1. **Crear cuenta en Twilio**: https://www.twilio.com/
2. **Obtener credenciales**:
   - Account SID
   - Auth Token
   - Número de WhatsApp (formato: whatsapp:+14155238886)
3. **Configurar webhook**:
   - En Twilio Console → WhatsApp → Sandbox
   - Webhook URL: `https://stvaldivia.cl/api/whatsapp/webhook`

### Opción B: WhatsApp Cloud API (Meta)

1. **Crear app en Meta for Developers**: https://developers.facebook.com/
2. **Configurar WhatsApp Business API**:
   - Obtener Business ID
   - Obtener Phone Number ID
   - Generar Access Token
   - Configurar Verify Token
3. **Configurar webhook**:
   - Webhook URL: `https://stvaldivia.cl/api/whatsapp/webhook`
   - Verify Token: (el que configuraste)
   - Suscribirse a eventos: `messages`

## 📝 Flujo de Funcionamiento

1. **Usuario envía mensaje a WhatsApp**
   → Webhook recibe el mensaje en `/api/whatsapp/webhook`

2. **Agente procesa el mensaje**:
   - Obtiene conocimiento del sitio (con cache)
   - Obtiene contexto relevante para la consulta
   - Recupera historial de conversación
   - Genera respuesta usando OpenAI con contexto

3. **Respuesta generada**:
   - Se envía automáticamente por WhatsApp
   - Se guarda en logs para historial

## 🧪 Pruebas

### Probar el análisis del sitio

```python
from app.helpers.site_analyzer import SiteAnalyzer

analyzer = SiteAnalyzer()
knowledge = analyzer.analyze_site()
print(analyzer.get_knowledge_summary())
```

### Probar envío de mensaje

```bash
curl -X POST https://stvaldivia.cl/api/whatsapp/test \
  -H "Content-Type: application/json" \
  -d '{
    "to": "+56912345678",
    "message": "Hola! Este es un mensaje de prueba"
  }'
```

(Requiere estar autenticado como admin)

## 🔍 Monitoreo

### Ver logs de conversaciones

Las conversaciones se guardan en la tabla `bot_logs` con:
- `canal='whatsapp'`
- `user_identifier` = número de teléfono
- `user_message` = mensaje del usuario
- `bot_response` = respuesta del bot

### Ver en el panel admin

```
/admin/bot/logs?canal=whatsapp
```

## 🎯 Características

✅ **Análisis automático del sitio**: Extrae conocimiento sin configuración manual
✅ **Respuestas contextuales**: Usa información real del sitio para responder
✅ **Historial de conversación**: Mantiene contexto entre mensajes
✅ **Fallback inteligente**: Si OpenAI falla, usa respuestas basadas en reglas
✅ **Múltiples proveedores**: Soporta Twilio y WhatsApp Cloud API
✅ **Logs completos**: Todas las conversaciones se guardan para análisis

## 🔄 Actualización del Conocimiento

El conocimiento del sitio se actualiza automáticamente cada 24 horas. Para forzar actualización:

```bash
curl -X POST https://stvaldivia.cl/api/whatsapp/refresh-knowledge
```

(Requiere autenticación admin)

## 📚 Próximos Pasos

1. **Configurar credenciales de WhatsApp** en variables de entorno
2. **Configurar webhook** en tu proveedor de WhatsApp
3. **Probar** enviando un mensaje a tu número de WhatsApp
4. **Monitorear logs** para ver cómo responde el agente
5. **Ajustar prompts** si es necesario en `whatsapp_agent_service.py`

## 🐛 Troubleshooting

### El webhook no recibe mensajes
- Verificar que la URL del webhook esté correctamente configurada
- Verificar que el servidor sea accesible desde internet
- Revisar logs: `journalctl -u stvaldivia -f`

### El agente no responde
- Verificar que `OPENAI_API_KEY` esté configurada
- Verificar logs de errores
- Probar el endpoint de test

### El conocimiento no se actualiza
- Forzar actualización: `POST /api/whatsapp/refresh-knowledge`
- Verificar que el sitio sea accesible
- Revisar logs del `SiteAnalyzer`

---

**¿Necesitas ayuda?** Revisa los logs o pregunta por casos específicos.


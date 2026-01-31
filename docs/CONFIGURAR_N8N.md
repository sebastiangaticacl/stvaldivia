# 🔗 Configurar Integración con n8n

## 📋 Resumen

Esta guía explica cómo conectar n8n (herramienta de automatización de flujos de trabajo) con el sistema BIMBA/stvaldivia.

## 🎯 Opciones de Integración

### Opción 1: n8n → BIMBA (Webhooks desde n8n hacia la app)

n8n puede enviar datos a la aplicación mediante webhooks HTTP.

### Opción 2: BIMBA → n8n (Webhooks desde la app hacia n8n)

La aplicación puede enviar eventos a n8n cuando ocurren acciones específicas.

### Opción 3: n8n como intermediario

n8n puede actuar como orquestador entre múltiples sistemas.

---

## 🔧 Opción 1: n8n → BIMBA (Recomendado para automatizaciones)

### Paso 1: Crear endpoint de webhook en la aplicación

Ya existe infraestructura de webhooks. Puedes crear un nuevo endpoint:

**Archivo:** `app/routes.py` o crear `app/routes/n8n_routes.py`

```python
from flask import Blueprint, request, jsonify, current_app
from app.helpers.exception_handler import handle_exceptions

n8n_bp = Blueprint('n8n', __name__, url_prefix='/api/n8n')

@n8n_bp.route('/webhook', methods=['POST'])
@handle_exceptions(json_response=True)
def n8n_webhook():
    """
    Endpoint para recibir webhooks de n8n
    
    Headers esperados:
    - X-n8n-Signature: (opcional) Firma para validar el webhook
    
    Body: JSON con los datos que n8n envía
    """
    data = request.get_json()
    
    # Validar firma si está configurada
    signature = request.headers.get('X-n8n-Signature')
    if signature:
        # Implementar validación de firma si es necesario
        pass
    
    current_app.logger.info(f"Webhook recibido de n8n: {data}")
    
    # Procesar los datos según tu lógica
    # Ejemplo: crear una entrega, actualizar inventario, etc.
    
    return jsonify({
        'success': True,
        'message': 'Webhook procesado correctamente',
        'data': data
    }), 200

@n8n_bp.route('/webhook/<string:workflow_id>', methods=['POST'])
@handle_exceptions(json_response=True)
def n8n_webhook_specific(workflow_id):
    """
    Endpoint específico para un workflow de n8n
    Útil para tener múltiples workflows apuntando a diferentes endpoints
    """
    data = request.get_json()
    
    current_app.logger.info(f"Webhook recibido de n8n workflow {workflow_id}: {data}")
    
    # Procesar según el workflow_id
    # Ejemplo: workflow_id = "nueva-entrega", "actualizar-inventario", etc.
    
    return jsonify({
        'success': True,
        'workflow_id': workflow_id,
        'message': 'Webhook procesado correctamente'
    }), 200
```

**Registrar el blueprint en `app/__init__.py`:**

```python
from app.routes.n8n_routes import n8n_bp
app.register_blueprint(n8n_bp)
```

### Paso 2: Configurar n8n para enviar webhooks

1. **En n8n, crea un nuevo workflow**
2. **Agrega un nodo "HTTP Request"**
3. **Configura:**
   - **Method:** POST
   - **URL:** `https://stvaldivia.cl/api/n8n/webhook`
   - **Authentication:** (opcional) Basic Auth o Header Auth
   - **Headers:**
     ```
     Content-Type: application/json
     X-n8n-Signature: <tu-secret-key>
     ```
   - **Body:** JSON con los datos que quieres enviar

### Paso 3: Ejemplos de uso

#### Ejemplo 1: Crear una entrega desde n8n

```json
{
  "action": "create_delivery",
  "data": {
    "item_name": "Cerveza Artesanal",
    "quantity": 2,
    "bartender": "Juan",
    "barra": "barra_principal"
  }
}
```

#### Ejemplo 2: Actualizar inventario

```json
{
  "action": "update_inventory",
  "data": {
    "ingredient_id": 123,
    "quantity": 50,
    "location": "barra_principal"
  }
}
```

---

## 🔧 Opción 2: BIMBA → n8n (Enviar eventos a n8n)

### Paso 1: Configurar webhook de n8n

1. **En n8n, crea un workflow con un nodo "Webhook"**
2. **Configura el webhook:**
   - **HTTP Method:** POST
   - **Path:** `/webhook/bimba` (o el que prefieras)
   - **Response Mode:** Respond When Last Node Finishes
3. **Copia la URL del webhook** (ej: `https://tu-n8n-instance.com/webhook/bimba`)

### Paso 2: Agregar variable de entorno

En `/etc/stvaldivia/stvaldivia.env`:

```bash
N8N_WEBHOOK_URL=https://tu-n8n-instance.com/webhook/bimba
N8N_WEBHOOK_SECRET=tu-secret-key-aqui
```

### Paso 3: Crear helper para enviar a n8n

**Archivo:** `app/helpers/n8n_client.py`

```python
import requests
import logging
from flask import current_app

logger = logging.getLogger(__name__)

def send_to_n8n(event_type: str, data: dict):
    """
    Envía un evento a n8n
    
    Args:
        event_type: Tipo de evento (ej: 'delivery_created', 'inventory_updated')
        data: Datos del evento
    """
    webhook_url = current_app.config.get('N8N_WEBHOOK_URL')
    if not webhook_url:
        logger.warning("N8N_WEBHOOK_URL no configurada, no se enviará evento a n8n")
        return False
    
    payload = {
        'event_type': event_type,
        'timestamp': datetime.utcnow().isoformat(),
        'data': data
    }
    
    headers = {
        'Content-Type': 'application/json'
    }
    
    # Agregar autenticación si está configurada
    secret = current_app.config.get('N8N_WEBHOOK_SECRET')
    if secret:
        headers['X-Webhook-Secret'] = secret
    
    try:
        response = requests.post(
            webhook_url,
            json=payload,
            headers=headers,
            timeout=5
        )
        response.raise_for_status()
        logger.info(f"Evento enviado a n8n: {event_type}")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Error enviando evento a n8n: {e}")
        return False
```

### Paso 4: Usar en el código

**Ejemplo en `app/routes/delivery_routes.py`:**

```python
from app.helpers.n8n_client import send_to_n8n

@bp.route('/delivery/create', methods=['POST'])
def create_delivery():
    # ... código para crear entrega ...
    
    # Enviar evento a n8n
    send_to_n8n('delivery_created', {
        'delivery_id': delivery.id,
        'item_name': delivery.item_name,
        'quantity': delivery.quantity,
        'bartender': delivery.bartender
    })
    
    return jsonify({'success': True})
```

---

## 🔧 Opción 3: n8n como intermediario (Orquestación)

n8n puede:
1. Escuchar eventos de múltiples fuentes
2. Procesar y transformar datos
3. Enviar a múltiples destinos (incluyendo BIMBA)

**Ejemplo de workflow:**
```
Instagram Webhook → n8n → Procesar → Enviar a BIMBA API
```

---

## 🔐 Seguridad

### Validación de Webhooks

Para webhooks entrantes desde n8n:

```python
import hmac
import hashlib

def validate_n8n_signature(payload, signature, secret):
    """Valida la firma del webhook de n8n"""
    expected_signature = hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected_signature, signature)
```

### Autenticación

**Opción A: API Key en Header**
```python
API_KEY = request.headers.get('X-API-Key')
if API_KEY != current_app.config.get('N8N_API_KEY'):
    return jsonify({'error': 'Unauthorized'}), 401
```

**Opción B: Basic Auth**
```python
from flask_httpauth import HTTPBasicAuth
auth = HTTPBasicAuth()

@auth.verify_password
def verify_password(username, password):
    return (username == current_app.config.get('N8N_USERNAME') and
            password == current_app.config.get('N8N_PASSWORD'))
```

---

## 📝 Variables de Entorno

Agregar a `/etc/stvaldivia/stvaldivia.env`:

```bash
# n8n Integration
N8N_WEBHOOK_URL=https://tu-n8n-instance.com/webhook/bimba
N8N_WEBHOOK_SECRET=tu-secret-key-segura
N8N_API_KEY=tu-api-key-para-webhooks-entrantes
```

---

## 🚀 Ejemplos de Casos de Uso

### 1. Automatizar creación de entregas desde Google Sheets
- n8n lee Google Sheets cada hora
- Si hay nuevas filas, envía webhook a BIMBA
- BIMBA crea las entregas automáticamente

### 2. Notificaciones cuando se cierra un turno
- BIMBA envía evento a n8n cuando se cierra un turno
- n8n envía email, mensaje a Slack, o actualiza dashboard

### 3. Sincronización de inventario
- n8n monitorea sistema externo de inventario
- Cuando hay cambios, actualiza inventario en BIMBA vía API

### 4. Reportes automáticos
- n8n consulta API de BIMBA cada día
- Genera reporte y lo envía por email

---

## 🔍 Endpoints de API Disponibles

La aplicación ya tiene varios endpoints que n8n puede usar:

- `GET /api/health` - Health check
- `POST /api/delivery/create` - Crear entrega
- `GET /api/delivery/list` - Listar entregas
- `POST /api/inventory/update` - Actualizar inventario
- `GET /api/shift/current` - Obtener turno actual

(Revisa `app/routes/api_routes.py` para ver todos los endpoints disponibles)

---

## 📚 Recursos

- [Documentación de n8n](https://docs.n8n.io/)
- [n8n HTTP Request Node](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.httprequest/)
- [n8n Webhook Node](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.webhook/)

---

## ✅ Checklist de Implementación

- [ ] Decidir dirección de integración (n8n→BIMBA, BIMBA→n8n, o ambas)
- [ ] Crear endpoints de webhook si es necesario
- [ ] Configurar variables de entorno
- [ ] Implementar validación de seguridad
- [ ] Probar con n8n local o instancia de prueba
- [ ] Documentar workflows específicos
- [ ] Monitorear logs para debugging

---

**¿Necesitas ayuda con algún caso de uso específico?** Pregúntame y te ayudo a implementarlo.


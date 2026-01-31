"""
Rutas para integración con n8n
Endpoints para recibir webhooks de n8n y enviar eventos a n8n
"""
from flask import Blueprint, request, jsonify, current_app
import hmac
import hashlib
import logging
from datetime import datetime
from app.infrastructure.rate_limiter.decorators import rate_limit
from app.helpers.logger import get_logger

logger = get_logger(__name__)

n8n_bp = Blueprint('n8n', __name__, url_prefix='/api/n8n')


def verify_n8n_signature(payload, signature, secret):
    """
    Valida la firma del webhook de n8n usando HMAC SHA256.
    
    Args:
        payload: El cuerpo del request en bytes o string
        signature: La firma recibida en el header
        secret: El secreto compartido configurado
        
    Returns:
        bool: True si la firma es válida
    """
    try:
        if not secret:
            # Si no hay secret configurado, permitir (para desarrollo)
            return True
        
        if isinstance(payload, str):
            payload = payload.encode('utf-8')
        
        expected_signature = hmac.new(
            secret.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        # Comparar firmas de forma segura
        return hmac.compare_digest(f'sha256={expected_signature}', signature)
    except Exception as e:
        logger.error(f"Error validando firma n8n: {e}")
        return False


@n8n_bp.route('/webhook', methods=['POST'])
@rate_limit(max_requests=60, per_seconds=60)
def n8n_webhook():
    """
    Endpoint para recibir webhooks de n8n
    
    Headers esperados:
    - X-n8n-Signature: (opcional) Firma para validar el webhook
    - X-API-Key: (opcional) API Key para autenticación
    
    Body: JSON con los datos que n8n envía
    
    Ejemplo de payload:
    {
        "action": "create_delivery",
        "data": {
            "item_name": "Cerveza Artesanal",
            "quantity": 2,
            "bartender": "Juan",
            "barra": "barra_principal"
        }
    }
    """
    try:
        # Obtener datos del request
        data = request.get_json()
        
        if not data:
            logger.warning("Webhook n8n recibido sin datos")
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        # Validar autenticación por API Key si está configurada (leer desde SystemConfig primero)
        try:
            from app.models.system_config_models import SystemConfig
            expected_api_key = SystemConfig.get('n8n_api_key') or current_app.config.get('N8N_API_KEY')
            secret = SystemConfig.get('n8n_webhook_secret') or current_app.config.get('N8N_WEBHOOK_SECRET')
        except:
            expected_api_key = current_app.config.get('N8N_API_KEY')
            secret = current_app.config.get('N8N_WEBHOOK_SECRET')
        
        api_key = request.headers.get('X-API-Key')
        if expected_api_key:
            if not api_key or api_key != expected_api_key:
                logger.warning("Webhook n8n rechazado: API Key inválida")
                return jsonify({
                    'success': False,
                    'error': 'Unauthorized'
                }), 401
        
        # Validar firma si está configurada
        signature = request.headers.get('X-n8n-Signature')
        
        if signature and secret:
            payload_str = request.get_data(as_text=True)
            if not verify_n8n_signature(payload_str, signature, secret):
                logger.warning("Webhook n8n rechazado: Firma inválida")
                return jsonify({
                    'success': False,
                    'error': 'Invalid signature'
                }), 403
        
        logger.info(f"Webhook recibido de n8n: {data}")
        
        # Procesar según el tipo de acción
        action = data.get('action')
        
        if action == 'create_delivery':
            return _handle_create_delivery(data.get('data', {}))
        elif action == 'update_inventory':
            return _handle_update_inventory(data.get('data', {}))
        elif action == 'get_shift_status':
            return _handle_get_shift_status()
        elif action == 'test':
            return jsonify({
                'success': True,
                'message': 'Webhook de prueba procesado correctamente',
                'timestamp': datetime.utcnow().isoformat()
            }), 200
        else:
            # Acción no reconocida, pero procesar igual
            logger.info(f"Acción no reconocida: {action}, procesando como genérico")
            return jsonify({
                'success': True,
                'message': 'Webhook procesado correctamente',
                'action': action,
                'data': data
            }), 200
            
    except Exception as e:
        logger.error(f"Error procesando webhook n8n: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@n8n_bp.route('/webhook/<string:workflow_id>', methods=['POST'])
@rate_limit(max_requests=60, per_seconds=60)
def n8n_webhook_specific(workflow_id):
    """
    Endpoint específico para un workflow de n8n
    Útil para tener múltiples workflows apuntando a diferentes endpoints
    
    Args:
        workflow_id: Identificador del workflow (ej: "nueva-entrega", "actualizar-inventario")
    """
    try:
        data = request.get_json()
        
        if not data:
            logger.warning(f"Webhook n8n workflow {workflow_id} recibido sin datos")
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        # Validar autenticación (leer desde SystemConfig primero)
        try:
            from app.models.system_config_models import SystemConfig
            expected_api_key = SystemConfig.get('n8n_api_key') or current_app.config.get('N8N_API_KEY')
        except:
            expected_api_key = current_app.config.get('N8N_API_KEY')
        
        api_key = request.headers.get('X-API-Key')
        if expected_api_key:
            if not api_key or api_key != expected_api_key:
                logger.warning(f"Webhook n8n workflow {workflow_id} rechazado: API Key inválida")
                return jsonify({
                    'success': False,
                    'error': 'Unauthorized'
                }), 401
        
        logger.info(f"Webhook recibido de n8n workflow {workflow_id}: {data}")
        
        # Procesar según el workflow_id
        # Aquí puedes agregar lógica específica para cada workflow
        
        return jsonify({
            'success': True,
            'workflow_id': workflow_id,
            'message': 'Webhook procesado correctamente',
            'data': data
        }), 200
        
    except Exception as e:
        logger.error(f"Error procesando webhook n8n workflow {workflow_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def _handle_create_delivery(data):
    """Maneja la creación de una entrega desde n8n"""
    try:
        from app.models.delivery_models import Delivery
        from app.models import db
        
        # Validar datos requeridos
        required_fields = ['item_name', 'quantity']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'Campo requerido faltante: {field}'
                }), 400
        
        # Crear entrega
        delivery = Delivery(
            item_name=data['item_name'],
            quantity=data.get('quantity', 1),
            bartender=data.get('bartender', 'n8n'),
            barra=data.get('barra', 'barra_principal'),
            timestamp=datetime.utcnow()
        )
        
        db.session.add(delivery)
        db.session.commit()
        
        logger.info(f"Entrega creada desde n8n: {delivery.id}")
        
        return jsonify({
            'success': True,
            'message': 'Entrega creada correctamente',
            'delivery_id': delivery.id
        }), 200
        
    except Exception as e:
        logger.error(f"Error creando entrega desde n8n: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def _handle_update_inventory(data):
    """Maneja la actualización de inventario desde n8n"""
    try:
        from app.models.inventory_models import Inventory
        from app.models import db
        
        # Validar datos requeridos
        if 'ingredient_id' not in data and 'ingredient_name' not in data:
            return jsonify({
                'success': False,
                'error': 'Se requiere ingredient_id o ingredient_name'
            }), 400
        
        # Buscar ingrediente
        if 'ingredient_id' in data:
            inventory = Inventory.query.filter_by(ingredient_id=data['ingredient_id']).first()
        else:
            # Buscar por nombre (requiere modelo de ingrediente)
            from app.models.ingredient_models import Ingredient
            ingredient = Ingredient.query.filter_by(name=data['ingredient_name']).first()
            if not ingredient:
                return jsonify({
                    'success': False,
                    'error': f'Ingrediente no encontrado: {data["ingredient_name"]}'
                }), 404
            inventory = Inventory.query.filter_by(ingredient_id=ingredient.id).first()
        
        if not inventory:
            return jsonify({
                'success': False,
                'error': 'Inventario no encontrado'
            }), 404
        
        # Actualizar cantidad
        if 'quantity' in data:
            inventory.quantity = data['quantity']
        
        if 'location' in data:
            inventory.location = data['location']
        
        db.session.commit()
        
        logger.info(f"Inventario actualizado desde n8n: {inventory.id}")
        
        return jsonify({
            'success': True,
            'message': 'Inventario actualizado correctamente',
            'inventory_id': inventory.id
        }), 200
        
    except Exception as e:
        logger.error(f"Error actualizando inventario desde n8n: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def _handle_get_shift_status():
    """Obtiene el estado del turno actual"""
    try:
        from app.helpers.shift_manager_compat import get_shift_status
        
        shift_status = get_shift_status()
        
        return jsonify({
            'success': True,
            'shift_status': shift_status
        }), 200
        
    except Exception as e:
        logger.error(f"Error obteniendo estado de turno: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@n8n_bp.route('/health', methods=['GET'])
@rate_limit(max_requests=10, per_seconds=60)
def n8n_health():
    """Health check para verificar que el endpoint de n8n está disponible"""
    return jsonify({
        'status': 'ok',
        'service': 'n8n-integration',
        'timestamp': datetime.utcnow().isoformat()
    }), 200


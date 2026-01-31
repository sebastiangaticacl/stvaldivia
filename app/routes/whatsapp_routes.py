"""
Rutas para recibir y procesar webhooks de WhatsApp
"""
from flask import Blueprint, request, jsonify, current_app
from app.helpers.exception_handler import handle_exceptions
from app.application.services.unified_social_agent_service import UnifiedSocialAgentService
import logging

logger = logging.getLogger(__name__)

whatsapp_bp = Blueprint('whatsapp', __name__, url_prefix='/api/whatsapp')


@whatsapp_bp.route('/webhook', methods=['GET', 'POST'])
@handle_exceptions(json_response=True)
def whatsapp_webhook():
    """
    Endpoint para recibir webhooks de WhatsApp
    
    GET: Verificación del webhook (para WhatsApp Cloud API)
    POST: Recibir mensajes
    """
    if request.method == 'GET':
        # Verificación del webhook (WhatsApp Cloud API)
        mode = request.args.get('hub.mode')
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')
        
        verify_token = current_app.config.get('WHATSAPP_VERIFY_TOKEN')
        
        if mode == 'subscribe' and token == verify_token:
            logger.info("Webhook de WhatsApp verificado exitosamente")
            return challenge, 200
        else:
            logger.warning("Verificación de webhook de WhatsApp fallida")
            return jsonify({'error': 'Verification failed'}), 403
    
    # POST: Recibir mensajes
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data received'}), 400
        
        # WhatsApp Cloud API format
        if 'entry' in data:
            return _handle_whatsapp_cloud_webhook(data)
        
        # Twilio format
        elif 'MessageSid' in data or 'Body' in data:
            return _handle_twilio_webhook(data)
        
        # Formato genérico
        else:
            return _handle_generic_webhook(data)
            
    except Exception as e:
        logger.error(f"Error procesando webhook de WhatsApp: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


def _handle_whatsapp_cloud_webhook(data: dict) -> tuple:
    """Procesa webhook de WhatsApp Cloud API"""
    agent_service = UnifiedSocialAgentService()
    
    for entry in data.get('entry', []):
        for change in entry.get('changes', []):
            value = change.get('value', {})
            
            # Mensajes
            if 'messages' in value:
                for message in value['messages']:
                    if message.get('type') == 'text':
                        from_number = message.get('from')
                        message_text = message.get('text', {}).get('body', '')
                        message_id = message.get('id')
                        
                        if from_number and message_text:
                            # Agregar código de país si no lo tiene
                            if not from_number.startswith('+'):
                                from_number = f"+{from_number}"
                            
                            logger.info(f"Mensaje recibido de WhatsApp: {from_number} - {message_text[:50]}")
                            
                            result = agent_service.process_message(
                                platform='whatsapp',
                                sender_id=from_number,
                                message=message_text,
                                message_id=message_id
                            )
                            
                            if result.get('success'):
                                return jsonify({'status': 'success'}), 200
                            else:
                                return jsonify({'status': 'error', 'error': result.get('error')}), 500
            
            # Status updates (mensajes leídos, entregados, etc.)
            elif 'statuses' in value:
                for status in value['statuses']:
                    logger.debug(f"Status update: {status.get('status')} for {status.get('id')}")
    
    return jsonify({'status': 'ok'}), 200


def _handle_twilio_webhook(data: dict) -> tuple:
    """Procesa webhook de Twilio"""
    agent_service = UnifiedSocialAgentService()
    
    from_number = data.get('From', '').replace('whatsapp:', '')
    message_text = data.get('Body', '')
    message_sid = data.get('MessageSid')
    
    if from_number and message_text:
        logger.info(f"Mensaje recibido de WhatsApp (Twilio): {from_number} - {message_text[:50]}")
        
        result = agent_service.process_message(
            platform='whatsapp',
            sender_id=from_number,
            message=message_text,
            message_id=message_sid
        )
        
        if result.get('success'):
            return jsonify({'status': 'success'}), 200
        else:
            return jsonify({'status': 'error', 'error': result.get('error')}), 500
    
    return jsonify({'status': 'ok'}), 200


def _handle_generic_webhook(data: dict) -> tuple:
    """Procesa webhook en formato genérico"""
    agent_service = UnifiedSocialAgentService()
    
    from_number = data.get('from') or data.get('from_number') or data.get('phone')
    message_text = data.get('message') or data.get('text') or data.get('body')
    message_id = data.get('message_id') or data.get('id')
    
    if from_number and message_text:
        logger.info(f"Mensaje recibido de WhatsApp (genérico): {from_number} - {message_text[:50]}")
        
        result = agent_service.process_message(
            platform='whatsapp',
            sender_id=from_number,
            message=message_text,
            message_id=message_id
        )
        
        if result.get('success'):
            return jsonify({'status': 'success'}), 200
        else:
            return jsonify({'status': 'error', 'error': result.get('error')}), 500
    
    return jsonify({'status': 'ok', 'message': 'No message data found'}), 200


@whatsapp_bp.route('/refresh-knowledge', methods=['POST'])
@handle_exceptions(json_response=True)
def refresh_knowledge():
    """
    Endpoint para forzar actualización del conocimiento del sitio
    Solo accesible con autenticación
    """
    # Verificar autenticación (puedes usar session o API key)
    from flask import session
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        agent_service = UnifiedSocialAgentService()
        agent_service.refresh_knowledge_base()
        
        return jsonify({
            'success': True,
            'message': 'Conocimiento del sitio actualizado exitosamente'
        }), 200
    except Exception as e:
        logger.error(f"Error refrescando conocimiento: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@whatsapp_bp.route('/test', methods=['POST'])
@handle_exceptions(json_response=True)
def test_whatsapp():
    """
    Endpoint de prueba para enviar un mensaje de prueba
    """
    from flask import session
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        to_number = data.get('to')
        test_message = data.get('message', 'Hola! Este es un mensaje de prueba de BIMBA 💜')
        
        if not to_number:
            return jsonify({'error': 'Número de destino requerido'}), 400
        
        from app.infrastructure.external.whatsapp_client import WhatsAppClient
        client = WhatsAppClient()
        
        result = client.send_message(to=to_number, message=test_message)
        
        return jsonify(result), 200 if result.get('success') else 500
        
    except Exception as e:
        logger.error(f"Error en test de WhatsApp: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


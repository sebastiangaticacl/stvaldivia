"""
Rutas para integración con Facebook Messenger Webhooks
"""
from flask import Blueprint, request, jsonify, current_app
from app.helpers.exception_handler import handle_exceptions
from app.application.services.unified_social_agent_service import UnifiedSocialAgentService
import logging
import hmac
import hashlib

logger = logging.getLogger(__name__)

facebook_bp = Blueprint('facebook', __name__, url_prefix='/webhook')


def verify_facebook_signature(payload, signature):
    """Verifica la firma de un webhook de Facebook"""
    try:
        app_secret = current_app.config.get('META_APP_SECRET') or current_app.config.get('FACEBOOK_APP_SECRET')
        if not app_secret:
            return True  # Si no hay secret configurado, permitir (para desarrollo)
        
        expected_signature = hmac.new(
            app_secret.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(f'sha256={expected_signature}', signature)
    except Exception:
        return False


@facebook_bp.route('/facebook', methods=['GET'])
@handle_exceptions(json_response=True)
def facebook_webhook_verify():
    """
    Endpoint de verificación de webhook de Facebook Messenger.
    Facebook envía un GET request para verificar el webhook.
    """
    verify_token = current_app.config.get('FACEBOOK_VERIFY_TOKEN') or current_app.config.get('META_VERIFY_TOKEN')
    
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')
    
    if mode == 'subscribe' and token == verify_token:
        logger.info("Facebook webhook verificado exitosamente")
        return challenge, 200
    else:
        logger.warning(f"Intento de verificación fallido: mode={mode}")
        return jsonify({'error': 'Verification failed'}), 403


@facebook_bp.route('/facebook', methods=['POST'])
@handle_exceptions(json_response=True)
def facebook_webhook():
    """
    Endpoint para recibir webhooks de Facebook Messenger.
    Procesa mensajes entrantes y genera respuestas automáticas.
    """
    try:
        # Verificar firma si está disponible
        signature = request.headers.get('X-Hub-Signature-256')
        if signature:
            if not verify_facebook_signature(request.data, signature):
                logger.warning("Firma de webhook de Facebook inválida")
                return jsonify({'error': 'Invalid signature'}), 403
        
        data = request.get_json()
        
        # Facebook envía un objeto 'object' y 'entry'
        if data.get('object') != 'page':
            return jsonify({'error': 'Invalid object type'}), 400
        
        entries = data.get('entry', [])
        
        # Procesar cada entrada
        for entry in entries:
            messaging = entry.get('messaging', [])
            
            for event in messaging:
                # Verificar que sea un mensaje
                if 'message' not in event:
                    continue
                
                # Obtener información del mensaje
                sender_id = event.get('sender', {}).get('id')
                message = event.get('message', {})
                message_text = message.get('text', '')
                message_id = message.get('mid')
                
                # Ignorar mensajes sin texto
                if not message_text:
                    logger.info(f"Mensaje sin texto recibido de Facebook {sender_id}")
                    continue
                
                # Procesar mensaje con el agente unificado
                agent_service = UnifiedSocialAgentService()
                result = agent_service.process_message(
                    platform='facebook',
                    sender_id=sender_id,
                    message=message_text,
                    message_id=message_id,
                    metadata={
                        'facebook_sender_id': sender_id,
                        'facebook_message_id': message_id,
                        'page_id': entry.get('id')
                    }
                )
                
                if result.get('success'):
                    logger.info(f"Respuesta enviada a Facebook user {sender_id}")
                else:
                    logger.warning(f"No se pudo enviar respuesta para {sender_id}: {result.get('error')}")
        
        # Facebook espera un 200 OK
        return jsonify({'status': 'ok'}), 200
        
    except Exception as e:
        logger.error(f"Error procesando webhook de Facebook: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@facebook_bp.route('/facebook/test', methods=['POST'])
@handle_exceptions(json_response=True)
def facebook_test():
    """
    Endpoint de prueba para simular un webhook de Facebook.
    """
    from flask import session
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        sender_id = data.get('sender_id', 'test_user_123')
        message_text = data.get('message', 'Hola, ¿cómo están?')
        
        # Procesar mensaje con el agente unificado
        agent_service = UnifiedSocialAgentService()
        result = agent_service.process_message(
            platform='facebook',
            sender_id=sender_id,
            message=message_text
        )
        
        if result.get('success'):
            return jsonify({
                'status': 'success',
                'original_message': message_text,
                'response': result.get('response'),
                'sender_id': sender_id
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'message': result.get('error', 'No se pudo generar la respuesta')
            }), 500
            
    except Exception as e:
        logger.error(f"Error en test de Facebook: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


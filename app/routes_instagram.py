"""
Rutas para integración con Instagram/Meta Webhooks
"""
from flask import Blueprint, request, jsonify, current_app
import hmac
import hashlib
import json
from datetime import datetime

from app.application.services.unified_social_agent_service import UnifiedSocialAgentService

instagram_bp = Blueprint('instagram', __name__, url_prefix='/webhook')


def verify_instagram_signature(payload, signature):
    """
    Verifica la firma de un webhook de Instagram/Meta.
    
    Args:
        payload: El cuerpo del request en bytes
        signature: La firma recibida en el header
        
    Returns:
        bool: True si la firma es válida
    """
    try:
        app_secret = current_app.config.get('META_APP_SECRET')
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


@instagram_bp.route('/instagram', methods=['GET'])
def instagram_webhook_verify():
    """
    Endpoint de verificación de webhook de Instagram.
    Meta envía un GET request para verificar el webhook.
    """
    verify_token = current_app.config.get('INSTAGRAM_VERIFY_TOKEN')
    
    # Obtener parámetros del request
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')
    
    # Verificar que el modo sea 'subscribe' y el token coincida
    if mode == 'subscribe' and token == verify_token:
        current_app.logger.info("Instagram webhook verificado exitosamente")
        return challenge, 200
    else:
        current_app.logger.warning(f"Intento de verificación fallido: mode={mode}, token={token[:10] if token else None}...")
        return jsonify({'error': 'Verification failed'}), 403


@instagram_bp.route('/instagram', methods=['POST'])
def instagram_webhook():
    """
    Endpoint para recibir webhooks de Instagram/Meta.
    Procesa mensajes entrantes y genera respuestas automáticas.
    """
    try:
        # Obtener la firma del header (si está disponible)
        signature = request.headers.get('X-Hub-Signature-256')
        if signature:
            # Verificar firma si está configurada
            if not verify_instagram_signature(request.data, signature):
                current_app.logger.warning("Firma de webhook inválida")
                return jsonify({'error': 'Invalid signature'}), 403
        
        # Parsear el JSON
        data = request.get_json()
        
        # Meta envía un objeto 'object' y 'entry'
        if data.get('object') != 'instagram':
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
                message_id = message.get('mid') or f"ig_{sender_id}_{int(datetime.now().timestamp())}"
                
                # Ignorar mensajes sin texto (fotos, stickers, etc.)
                if not message_text:
                    current_app.logger.info(f"Mensaje sin texto recibido de {sender_id}")
                    continue
                
                # Crear objeto de mensaje
                instagram_message = SocialMediaMessage(
                    message_id=message_id,
                    platform='instagram',
                    sender=sender_id,
                    content=message_text,
                    timestamp=datetime.now(),
                    metadata={
                        'instagram_sender_id': sender_id,
                        'instagram_message_id': message.get('mid'),
                        'webhook_entry': entry.get('id')
                    }
                )
                
                # Procesar mensaje con el agente unificado
                agent_service = UnifiedSocialAgentService()
                result = agent_service.process_message(
                    platform='instagram',
                    sender_id=sender_id,
                    message=message_text,
                    message_id=message_id,
                    metadata={
                        'instagram_sender_id': sender_id,
                        'instagram_message_id': message.get('mid'),
                        'webhook_entry': entry.get('id')
                    }
                )
                
                if result.get('success'):
                    current_app.logger.info(f"Respuesta enviada a Instagram user {sender_id}")
                else:
                    current_app.logger.warning(f"No se pudo enviar respuesta para {sender_id}: {result.get('error')}")
        
        # Meta espera un 200 OK
        return jsonify({'status': 'ok'}), 200
        
    except Exception as e:
        current_app.logger.error(f"Error procesando webhook de Instagram: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


def send_instagram_message(recipient_id, message_text):
    """
    Envía un mensaje a un usuario de Instagram usando la Graph API.
    
    Args:
        recipient_id: ID del usuario de Instagram
        message_text: Texto del mensaje a enviar
    """
    try:
        import requests
        
        page_access_token = current_app.config.get('INSTAGRAM_PAGE_ACCESS_TOKEN')
        if not page_access_token:
            current_app.logger.error("INSTAGRAM_PAGE_ACCESS_TOKEN no configurada")
            return False
        
        instagram_account_id = current_app.config.get('INSTAGRAM_BUSINESS_ACCOUNT_ID')
        if not instagram_account_id:
            current_app.logger.error("INSTAGRAM_BUSINESS_ACCOUNT_ID no configurada")
            return False
        
        # URL de la Graph API de Instagram
        url = f"https://graph.facebook.com/v18.0/{instagram_account_id}/messages"
        
        payload = {
            'recipient': {'id': recipient_id},
            'message': {'text': message_text},
            'messaging_type': 'RESPONSE'
        }
        
        params = {
            'access_token': page_access_token
        }
        
        response = requests.post(url, json=payload, params=params, timeout=10)
        response.raise_for_status()
        
        return True
        
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Error enviando mensaje a Instagram: {e}")
        return False
    except Exception as e:
        current_app.logger.error(f"Error inesperado enviando mensaje a Instagram: {e}")
        return False


@instagram_bp.route('/instagram/test', methods=['POST'])
def instagram_test():
    """
    Endpoint de prueba para simular un webhook de Instagram.
    Útil para desarrollo y testing.
    """
    try:
        data = request.get_json()
        
        sender_id = data.get('sender_id', 'test_user_123')
        message_text = data.get('message', 'Hola, ¿cómo están?')
        
        # Crear mensaje de prueba
        test_message = SocialMediaMessage(
            message_id=f"test_{int(datetime.now().timestamp())}",
            platform='instagram',
            sender=sender_id,
            content=message_text,
            timestamp=datetime.now()
        )
        
        # Procesar mensaje con el agente unificado
        agent_service = UnifiedSocialAgentService()
        result = agent_service.process_message(
            platform='instagram',
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
        current_app.logger.error(f"Error en test de Instagram: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500










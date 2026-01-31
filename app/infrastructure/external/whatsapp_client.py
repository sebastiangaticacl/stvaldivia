"""
Cliente para WhatsApp Business API
Soporta múltiples proveedores: Twilio, WhatsApp Cloud API, etc.
"""
import logging
import requests
from typing import Dict, Optional, List
from flask import current_app

logger = logging.getLogger(__name__)


class WhatsAppClient:
    """
    Cliente para enviar mensajes a través de WhatsApp Business API
    """
    
    def __init__(self):
        self.provider = current_app.config.get('WHATSAPP_PROVIDER', 'twilio')
        self.api_key = current_app.config.get('WHATSAPP_API_KEY')
        self.api_secret = current_app.config.get('WHATSAPP_API_SECRET')
        self.from_number = current_app.config.get('WHATSAPP_FROM_NUMBER')
        self.account_sid = current_app.config.get('TWILIO_ACCOUNT_SID')
        self.auth_token = current_app.config.get('TWILIO_AUTH_TOKEN')
        self.whatsapp_business_id = current_app.config.get('WHATSAPP_BUSINESS_ID')
        self.whatsapp_token = current_app.config.get('WHATSAPP_TOKEN')
        self.whatsapp_phone_number_id = current_app.config.get('WHATSAPP_PHONE_NUMBER_ID')
    
    def send_message(self, to: str, message: str, media_url: Optional[str] = None) -> Dict:
        """
        Envía un mensaje de WhatsApp
        
        Args:
            to: Número de teléfono destino (formato: +56912345678)
            message: Texto del mensaje
            media_url: (opcional) URL de imagen/video/documento
        
        Returns:
            Dict con resultado del envío
        """
        # MODO SOLO LOCAL: no conectar a proveedores externos
        try:
            if current_app and current_app.config.get('LOCAL_ONLY', True):
                logger.info(f"LOCAL_ONLY activo: WhatsApp no enviado (to={to})")
                return {'success': True, 'status': 'skipped_local_only'}
        except Exception:
            pass

        if self.provider == 'twilio':
            return self._send_via_twilio(to, message, media_url)
        elif self.provider == 'whatsapp_cloud':
            return self._send_via_whatsapp_cloud(to, message, media_url)
        else:
            logger.error(f"Proveedor de WhatsApp no soportado: {self.provider}")
            return {'success': False, 'error': 'provider_not_supported'}
    
    def _send_via_twilio(self, to: str, message: str, media_url: Optional[str] = None) -> Dict:
        """Envía mensaje usando Twilio"""
        if not self.account_sid or not self.auth_token:
            logger.error("Twilio credentials no configuradas")
            return {'success': False, 'error': 'credentials_not_configured'}
        
        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"
        
        data = {
            'From': f'whatsapp:{self.from_number}',
            'To': f'whatsapp:{to}',
            'Body': message
        }
        
        if media_url:
            data['MediaUrl'] = media_url
        
        try:
            response = requests.post(
                url,
                data=data,
                auth=(self.account_sid, self.auth_token),
                timeout=10
            )
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"Mensaje enviado vía Twilio a {to}: {result.get('sid')}")
            
            return {
                'success': True,
                'message_sid': result.get('sid'),
                'status': result.get('status')
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Error enviando mensaje vía Twilio: {e}")
            return {'success': False, 'error': str(e)}
    
    def _send_via_whatsapp_cloud(self, to: str, message: str, media_url: Optional[str] = None) -> Dict:
        """Envía mensaje usando WhatsApp Cloud API"""
        if not self.whatsapp_token or not self.whatsapp_phone_number_id:
            logger.error("WhatsApp Cloud API credentials no configuradas")
            return {'success': False, 'error': 'credentials_not_configured'}
        
        url = f"https://graph.facebook.com/v18.0/{self.whatsapp_phone_number_id}/messages"
        
        headers = {
            'Authorization': f'Bearer {self.whatsapp_token}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'messaging_product': 'whatsapp',
            'to': to.replace('+', ''),  # WhatsApp Cloud API no usa el +
            'type': 'text',
            'text': {'body': message}
        }
        
        if media_url:
            # Determinar tipo de media
            if media_url.endswith(('.jpg', '.jpeg', '.png', '.gif')):
                payload['type'] = 'image'
                payload['image'] = {'link': media_url}
            elif media_url.endswith(('.mp4', '.mov', '.avi')):
                payload['type'] = 'video'
                payload['video'] = {'link': media_url}
            elif media_url.endswith(('.pdf', '.doc', '.docx')):
                payload['type'] = 'document'
                payload['document'] = {'link': media_url}
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"Mensaje enviado vía WhatsApp Cloud API a {to}: {result.get('messages', [{}])[0].get('id')}")
            
            return {
                'success': True,
                'message_id': result.get('messages', [{}])[0].get('id'),
                'status': 'sent'
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Error enviando mensaje vía WhatsApp Cloud API: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            return {'success': False, 'error': str(e)}
    
    def mark_as_read(self, message_id: str) -> bool:
        """Marca un mensaje como leído (solo WhatsApp Cloud API)"""
        if self.provider != 'whatsapp_cloud':
            return False
        
        if not self.whatsapp_token or not self.whatsapp_phone_number_id:
            return False
        
        url = f"https://graph.facebook.com/v18.0/{self.whatsapp_phone_number_id}/messages"
        
        headers = {
            'Authorization': f'Bearer {self.whatsapp_token}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'messaging_product': 'whatsapp',
            'status': 'read',
            'message_id': message_id
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=5)
            response.raise_for_status()
            return True
        except Exception as e:
            logger.warning(f"Error marcando mensaje como leído: {e}")
            return False


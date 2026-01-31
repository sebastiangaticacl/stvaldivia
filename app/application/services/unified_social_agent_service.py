"""
Servicio unificado de agente para redes sociales
Usa el cerebro de análisis del sitio para responder en WhatsApp, Instagram y Facebook
"""
import logging
from typing import Dict, Optional, List
from datetime import datetime
from flask import current_app

from app.helpers.site_analyzer import SiteAnalyzer
from app.infrastructure.external.openai_client import OpenAIAPIClient
from app.infrastructure.external.whatsapp_client import WhatsAppClient
from app.models import db
from app.application.services.bot_log_service import BotLogService

logger = logging.getLogger(__name__)


class UnifiedSocialAgentService:
    """
    Servicio unificado que maneja respuestas automáticas en todas las redes sociales
    usando el conocimiento del sitio web
    """
    
    # Clientes para cada plataforma
    _whatsapp_client: Optional[WhatsAppClient] = None
    _instagram_client: Optional[object] = None  # Se implementará
    _facebook_client: Optional[object] = None  # Se implementará
    
    def __init__(self):
        self.site_analyzer = SiteAnalyzer()
        self.openai_client = OpenAIAPIClient()
        self.bot_log_service = BotLogService()
        self.knowledge_base = None
    
    @property
    def whatsapp_client(self):
        """Lazy loading del cliente de WhatsApp"""
        if self._whatsapp_client is None:
            self._whatsapp_client = WhatsAppClient()
        return self._whatsapp_client
    
    def process_message(
        self,
        platform: str,
        sender_id: str,
        message: str,
        message_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Procesa un mensaje entrante de cualquier plataforma y genera respuesta
        
        Args:
            platform: 'whatsapp', 'instagram', 'facebook'
            sender_id: ID del remitente (número de teléfono, user ID, etc.)
            message: Texto del mensaje
            message_id: ID del mensaje (opcional)
            metadata: Metadatos adicionales (opcional)
        
        Returns:
            Dict con la respuesta generada y estado
        """
        try:
            # Validar plataforma
            if platform not in ['whatsapp', 'instagram', 'facebook']:
                return {
                    'success': False,
                    'error': f'Plataforma no soportada: {platform}'
                }
            
            # Obtener conocimiento del sitio (con cache)
            if not self.knowledge_base:
                self.knowledge_base = self.site_analyzer.analyze_site()
            
            # Obtener contexto relevante para la consulta
            context = self.site_analyzer.get_context_for_query(message)
            
            # Obtener historial de conversación
            conversation_history = self._get_conversation_history(platform, sender_id, limit=5)
            
            # Generar respuesta usando OpenAI con el contexto del sitio
            response = self._generate_response(
                user_message=message,
                context=context,
                conversation_history=conversation_history,
                platform=platform,
                sender_id=sender_id
            )
            
            # Enviar respuesta según la plataforma
            send_result = self._send_response(platform, sender_id, response, message_id)
            
            # Guardar en logs
            self._save_conversation_log(
                platform=platform,
                sender_id=sender_id,
                user_message=message,
                bot_response=response,
                success=send_result.get('success', False),
                metadata=metadata
            )
            
            return {
                'success': send_result.get('success', False),
                'response': response,
                'message_id': send_result.get('message_id') or send_result.get('message_sid')
            }
            
        except Exception as e:
            logger.error(f"Error procesando mensaje de {platform}: {e}", exc_info=True)
            
            # Enviar mensaje de error amigable
            error_message = self._get_error_message(platform)
            try:
                self._send_response(platform, sender_id, error_message, message_id)
            except:
                pass
            
            return {
                'success': False,
                'error': str(e),
                'response': error_message
            }
    
    def _generate_response(
        self,
        user_message: str,
        context: str,
        conversation_history: List[Dict],
        platform: str,
        sender_id: str
    ) -> str:
        """
        Genera una respuesta usando OpenAI con el contexto del sitio
        """
        # Construir prompt del sistema con conocimiento del sitio
        knowledge_summary = self.site_analyzer.get_knowledge_summary()
        
        # Tono y estilo según plataforma
        platform_instructions = {
            'whatsapp': 'Eres BIMBA respondiendo en WhatsApp. Puedes ser más casual y usar emojis ocasionalmente (máximo 2-3 por mensaje).',
            'instagram': 'Eres BIMBA respondiendo en Instagram. Mantén las respuestas concisas (idealmente menos de 200 caracteres). Usa emojis ocasionalmente.',
            'facebook': 'Eres BIMBA respondiendo en Facebook. Puedes ser un poco más detallado. Usa emojis ocasionalmente.'
        }
        
        system_prompt = f"""Eres BIMBA, el asistente virtual de Valdivia es Bimba. Eres amigable, profesional y conoces todo sobre el negocio.

INFORMACIÓN DEL NEGOCIO:
{knowledge_summary}

CONTEXTO RELEVANTE PARA ESTA CONSULTA:
{context}

{platform_instructions.get(platform, '')}

INSTRUCCIONES:
- Responde de manera amigable y profesional
- Usa emojis ocasionalmente pero no exageres (máximo 2-3 por mensaje)
- Si no sabes algo, admítelo y ofrece contactar con el equipo
- Mantén las respuestas concisas (máximo 2-3 oraciones)
- Si preguntan por horarios, productos, eventos, usa la información del contexto
- Siempre termina con 💜 si es apropiado
- Responde en español chileno"""

        # Construir mensajes para OpenAI
        messages = [{"role": "system", "content": system_prompt}]
        
        # Agregar historial de conversación
        for msg in conversation_history[-4:]:  # Últimos 4 mensajes del historial
            if msg.get('user_message'):
                messages.append({"role": "user", "content": msg['user_message']})
            if msg.get('bot_response'):
                messages.append({"role": "assistant", "content": msg['bot_response']})
        
        # Agregar mensaje actual
        messages.append({"role": "user", "content": user_message})
        
        # Ajustar max_tokens según plataforma
        max_tokens_map = {
            'whatsapp': 200,
            'instagram': 150,
            'facebook': 250
        }
        max_tokens = max_tokens_map.get(platform, 200)
        
        # Generar respuesta
        try:
            response = self.openai_client.generate_response(
                messages=messages,
                system_prompt=system_prompt,
                model="gpt-4o-mini",
                temperature=0.7,
                max_tokens=max_tokens
            )
            
            if response:
                return response.strip()
            else:
                # Fallback si OpenAI falla
                return self._generate_fallback_response(user_message, context, platform)
                
        except Exception as e:
            logger.error(f"Error generando respuesta con OpenAI: {e}")
            return self._generate_fallback_response(user_message, context, platform)
    
    def _generate_fallback_response(self, user_message: str, context: str, platform: str) -> str:
        """Genera una respuesta de fallback sin OpenAI"""
        message_lower = user_message.lower()
        
        # Respuestas básicas basadas en palabras clave
        if any(word in message_lower for word in ['hola', 'buenos días', 'buenas tardes', 'buenas noches']):
            return "¡Hola! 💜 Soy BIMBA, el asistente virtual de Valdivia es Bimba. ¿En qué puedo ayudarte?"
        
        if any(word in message_lower for word in ['horario', 'hora', 'abierto', 'cierra']):
            schedules = self.knowledge_base.get('schedules', {}) if self.knowledge_base else {}
            if schedules:
                schedules_str = ', '.join([f"{k}: {v}" for k, v in schedules.items()])
                return f"Horarios: {schedules_str} 💜"
            return "Para conocer nuestros horarios, puedes visitar nuestro sitio web o contactarnos directamente. 💜"
        
        if any(word in message_lower for word in ['producto', 'menu', 'comida', 'bebida']):
            return "Tenemos una gran variedad de productos. Te recomiendo visitar nuestro sitio web para ver el menú completo. 💜"
        
        if any(word in message_lower for word in ['evento', 'show', 'concierto']):
            events = self.knowledge_base.get('events', []) if self.knowledge_base else []
            if events:
                event_titles = [e['title'] for e in events[:3] if e.get('title')]
                return f"Próximos eventos: {', '.join(event_titles)}. Para más información visita nuestro sitio web. 💜"
            return "Tenemos eventos regulares. Visita nuestro sitio web o redes sociales para conocer los próximos eventos. 💜"
        
        if any(word in message_lower for word in ['contacto', 'teléfono', 'email', 'dirección']):
            contact = self.knowledge_base.get('contact_info', {}) if self.knowledge_base else {}
            contact_info = []
            if contact.get('phone'):
                contact_info.append(f"Teléfono: {contact['phone']}")
            if contact.get('email'):
                contact_info.append(f"Email: {contact['email']}")
            if contact_info:
                return f"Información de contacto: {' | '.join(contact_info)} 💜"
            return "Puedes contactarnos a través de nuestro sitio web o redes sociales. 💜"
        
        return "Gracias por contactarnos. Para más información, visita nuestro sitio web o redes sociales @valdiviaesbimba. 💜"
    
    def _send_response(self, platform: str, sender_id: str, message: str, message_id: Optional[str] = None) -> Dict:
        """Envía respuesta según la plataforma"""
        if platform == 'whatsapp':
            # Marcar como leído si es WhatsApp Cloud API
            if message_id:
                self.whatsapp_client.mark_as_read(message_id)
            
            return self.whatsapp_client.send_message(
                to=sender_id,
                message=message
            )
        
        elif platform == 'instagram':
            return self._send_instagram_message(sender_id, message)
        
        elif platform == 'facebook':
            return self._send_facebook_message(sender_id, message)
        
        else:
            return {'success': False, 'error': 'Plataforma no soportada'}
    
    def _send_instagram_message(self, recipient_id: str, message: str) -> Dict:
        """Envía mensaje a Instagram usando Graph API"""
        try:
            import requests
            
            page_access_token = current_app.config.get('INSTAGRAM_PAGE_ACCESS_TOKEN')
            instagram_account_id = current_app.config.get('INSTAGRAM_BUSINESS_ACCOUNT_ID')
            
            if not page_access_token or not instagram_account_id:
                logger.error("Credenciales de Instagram no configuradas")
                return {'success': False, 'error': 'credentials_not_configured'}
            
            url = f"https://graph.facebook.com/v18.0/{instagram_account_id}/messages"
            
            payload = {
                'recipient': {'id': recipient_id},
                'message': {'text': message},
                'messaging_type': 'RESPONSE'
            }
            
            params = {'access_token': page_access_token}
            
            response = requests.post(url, json=payload, params=params, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"Mensaje enviado a Instagram: {recipient_id}")
            
            return {
                'success': True,
                'message_id': result.get('message_id'),
                'status': 'sent'
            }
            
        except Exception as e:
            logger.error(f"Error enviando mensaje a Instagram: {e}")
            return {'success': False, 'error': str(e)}
    
    def _send_facebook_message(self, recipient_id: str, message: str) -> Dict:
        """Envía mensaje a Facebook usando Graph API"""
        try:
            import requests
            
            page_access_token = current_app.config.get('FACEBOOK_PAGE_ACCESS_TOKEN')
            page_id = current_app.config.get('FACEBOOK_PAGE_ID')
            
            if not page_access_token or not page_id:
                logger.error("Credenciales de Facebook no configuradas")
                return {'success': False, 'error': 'credentials_not_configured'}
            
            url = f"https://graph.facebook.com/v18.0/{page_id}/messages"
            
            payload = {
                'recipient': {'id': recipient_id},
                'message': {'text': message},
                'messaging_type': 'RESPONSE'
            }
            
            params = {'access_token': page_access_token}
            
            response = requests.post(url, json=payload, params=params, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"Mensaje enviado a Facebook: {recipient_id}")
            
            return {
                'success': True,
                'message_id': result.get('message_id'),
                'status': 'sent'
            }
            
        except Exception as e:
            logger.error(f"Error enviando mensaje a Facebook: {e}")
            return {'success': False, 'error': str(e)}
    
    def _get_conversation_history(self, platform: str, sender_id: str, limit: int = 5) -> List[Dict]:
        """Obtiene el historial de conversación"""
        try:
            conversation_id = f"{platform}_{sender_id}"
            
            logs = db.session.query(BotLog).filter_by(
                canal=platform,
                conversation_id=conversation_id
            ).order_by(BotLog.timestamp.desc()).limit(limit * 2).all()
            
            history = []
            for log in reversed(logs):
                if log.direction == 'user':
                    history.append({
                        'user_message': log.message,
                        'bot_response': None,
                        'timestamp': log.timestamp.isoformat() if log.timestamp else None
                    })
                elif log.direction == 'bot':
                    if history and history[-1].get('bot_response') is None:
                        history[-1]['bot_response'] = log.message
                    else:
                        history.append({
                            'user_message': None,
                            'bot_response': log.message,
                            'timestamp': log.timestamp.isoformat() if log.timestamp else None
                        })
            
            complete_history = [h for h in history if h.get('user_message') and h.get('bot_response')]
            return complete_history[-limit:] if len(complete_history) > limit else complete_history
            
        except Exception as e:
            logger.warning(f"Error obteniendo historial de conversación: {e}")
            return []
    
    def _save_conversation_log(
        self,
        platform: str,
        sender_id: str,
        user_message: str,
        bot_response: str,
        success: bool,
        metadata: Optional[Dict] = None
    ):
        """Guarda la conversación en los logs"""
        try:
            conversation_id = f"{platform}_{sender_id}"
            
            # Guardar mensaje del usuario
            self.bot_log_service.log_user_message(
                canal=platform,
                conversation_id=conversation_id,
                message=user_message,
                meta={'sender_id': sender_id, **(metadata or {})}
            )
            
            # Guardar respuesta del bot
            self.bot_log_service.log_bot_response(
                canal=platform,
                conversation_id=conversation_id,
                message=bot_response,
                model='gpt-4o-mini',
                status='success' if success else 'error',
                meta={
                    'sender_id': sender_id,
                    'success': success,
                    **(metadata or {})
                }
            )
            
        except Exception as e:
            logger.error(f"Error guardando log de conversación: {e}")
            db.session.rollback()
    
    def _get_error_message(self, platform: str) -> str:
        """Obtiene mensaje de error según la plataforma"""
        messages = {
            'whatsapp': "Lo siento, estoy teniendo problemas técnicos. Por favor intenta más tarde. 💜",
            'instagram': "Lo siento, estoy teniendo problemas técnicos. Por favor intenta más tarde. 💜",
            'facebook': "Lo siento, estoy teniendo problemas técnicos. Por favor intenta más tarde. 💜"
        }
        return messages.get(platform, "Lo siento, estoy teniendo problemas técnicos. Por favor intenta más tarde. 💜")
    
    def refresh_knowledge_base(self):
        """Fuerza una actualización del conocimiento del sitio"""
        logger.info("Refrescando conocimiento del sitio web...")
        self.knowledge_base = self.site_analyzer.analyze_site(force_refresh=True)
        logger.info("Conocimiento refrescado exitosamente")


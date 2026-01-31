"""
Servicio del agente de WhatsApp que usa el conocimiento del sitio
para responder mensajes de manera inteligente
"""
import logging
from typing import Dict, Optional, List
from datetime import datetime
from flask import current_app

from app.helpers.site_analyzer import SiteAnalyzer
from app.infrastructure.external.whatsapp_client import WhatsAppClient
from app.infrastructure.external.openai_client import OpenAIAPIClient
from app.models import db
from app.models.bot_log_models import BotLog

logger = logging.getLogger(__name__)


class WhatsAppAgentService:
    """
    Servicio que maneja las conversaciones de WhatsApp usando
    el conocimiento del sitio web y OpenAI
    """
    
    def __init__(self):
        self.site_analyzer = SiteAnalyzer()
        self.whatsapp_client = WhatsAppClient()
        self.openai_client = OpenAIAPIClient()
        self.knowledge_base = None
    
    def process_incoming_message(self, from_number: str, message: str, message_id: Optional[str] = None) -> Dict:
        """
        Procesa un mensaje entrante de WhatsApp y genera una respuesta
        
        Args:
            from_number: Número de teléfono del remitente
            message: Texto del mensaje
            message_id: ID del mensaje (para marcarlo como leído)
        
        Returns:
            Dict con la respuesta generada y estado
        """
        try:
            # Marcar mensaje como leído si es WhatsApp Cloud API
            if message_id:
                self.whatsapp_client.mark_as_read(message_id)
            
            # Obtener conocimiento del sitio (con cache)
            if not self.knowledge_base:
                self.knowledge_base = self.site_analyzer.analyze_site()
            
            # Obtener contexto relevante para la consulta
            context = self.site_analyzer.get_context_for_query(message)
            
            # Obtener historial de conversación (últimos 5 mensajes)
            conversation_history = self._get_conversation_history(from_number, limit=5)
            
            # Generar respuesta usando OpenAI con el contexto del sitio
            response = self._generate_response(
                user_message=message,
                context=context,
                conversation_history=conversation_history,
                from_number=from_number
            )
            
            # Enviar respuesta
            send_result = self.whatsapp_client.send_message(
                to=from_number,
                message=response
            )
            
            # Guardar en logs
            self._save_conversation_log(
                from_number=from_number,
                user_message=message,
                bot_response=response,
                success=send_result.get('success', False)
            )
            
            return {
                'success': send_result.get('success', False),
                'response': response,
                'message_id': send_result.get('message_id') or send_result.get('message_sid')
            }
            
        except Exception as e:
            logger.error(f"Error procesando mensaje de WhatsApp: {e}", exc_info=True)
            
            # Enviar mensaje de error amigable
            error_message = "Lo siento, estoy teniendo problemas técnicos. Por favor intenta más tarde. 💜"
            try:
                self.whatsapp_client.send_message(to=from_number, message=error_message)
            except:
                pass
            
            return {
                'success': False,
                'error': str(e),
                'response': error_message
            }
    
    def _generate_response(self, user_message: str, context: str, conversation_history: List[Dict], from_number: str) -> str:
        """
        Genera una respuesta usando OpenAI con el contexto del sitio
        """
        # Construir prompt del sistema con conocimiento del sitio
        knowledge_summary = self.site_analyzer.get_knowledge_summary()
        
        system_prompt = f"""Eres BIMBA, el asistente virtual de Valdivia es Bimba. Eres amigable, profesional y conoces todo sobre el negocio.

INFORMACIÓN DEL NEGOCIO:
{knowledge_summary}

CONTEXTO RELEVANTE PARA ESTA CONSULTA:
{context}

INSTRUCCIONES:
- Responde de manera amigable y profesional
- Usa emojis ocasionalmente pero no exageres (máximo 2-3 por mensaje)
- Si no sabes algo, admítelo y ofrece contactar con el equipo
- Mantén las respuestas concisas (máximo 2-3 oraciones)
- Si preguntan por horarios, productos, eventos, usa la información del contexto
- Siempre termina con 💜 si es apropiado

CANAL: WhatsApp (puedes ser más casual que en otros canales)"""

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
        
        # Generar respuesta
        try:
            response = self.openai_client.generate_response(
                messages=messages,
                system_prompt=system_prompt,
                model="gpt-4o-mini",
                temperature=0.7,
                max_tokens=200
            )
            
            if response:
                return response.strip()
            else:
                # Fallback si OpenAI falla
                return self._generate_fallback_response(user_message, context)
                
        except Exception as e:
            logger.error(f"Error generando respuesta con OpenAI: {e}")
            return self._generate_fallback_response(user_message, context)
    
    def _generate_fallback_response(self, user_message: str, context: str) -> str:
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
    
    def _get_conversation_history(self, from_number: str, limit: int = 5) -> List[Dict]:
        """Obtiene el historial de conversación de un número"""
        try:
            # Usar conversation_id basado en el número de teléfono
            conversation_id = f"whatsapp_{from_number}"
            
            logs = BotLog.query.filter_by(
                canal='whatsapp',
                conversation_id=conversation_id
            ).order_by(BotLog.timestamp.desc()).limit(limit * 2).all()  # Obtener más para filtrar
            
            history = []
            for log in reversed(logs):  # Invertir para orden cronológico
                if log.direction == 'user':
                    history.append({
                        'user_message': log.message,
                        'bot_response': None,
                        'timestamp': log.timestamp.isoformat() if log.timestamp else None
                    })
                elif log.direction == 'bot':
                    # Si el último mensaje fue del bot, agregar la respuesta
                    if history and history[-1].get('bot_response') is None:
                        history[-1]['bot_response'] = log.message
                    else:
                        # Si no hay mensaje de usuario previo, crear entrada
                        history.append({
                            'user_message': None,
                            'bot_response': log.message,
                            'timestamp': log.timestamp.isoformat() if log.timestamp else None
                        })
            
            # Filtrar solo las entradas con ambos mensajes y limitar
            complete_history = [h for h in history if h.get('user_message') and h.get('bot_response')]
            return complete_history[-limit:] if len(complete_history) > limit else complete_history
            
        except Exception as e:
            logger.warning(f"Error obteniendo historial de conversación: {e}")
            return []
    
    def _save_conversation_log(self, from_number: str, user_message: str, bot_response: str, success: bool):
        """Guarda la conversación en los logs"""
        try:
            from app.application.services.bot_log_service import BotLogService
            bot_log_service = BotLogService()
            
            conversation_id = f"whatsapp_{from_number}"
            
            # Guardar mensaje del usuario
            user_log = bot_log_service.log_user_message(
                canal='whatsapp',
                conversation_id=conversation_id,
                message=user_message,
                meta={'from_number': from_number}
            )
            
            # Guardar respuesta del bot
            bot_log_service.log_bot_response(
                canal='whatsapp',
                conversation_id=conversation_id,
                message=bot_response,
                model='gpt-4o-mini',
                status='success' if success else 'error',
                meta={
                    'from_number': from_number,
                    'success': success
                }
            )
            
        except Exception as e:
            logger.error(f"Error guardando log de conversación: {e}")
            db.session.rollback()
    
    def refresh_knowledge_base(self):
        """Fuerza una actualización del conocimiento del sitio"""
        logger.info("Refrescando conocimiento del sitio web...")
        self.knowledge_base = self.site_analyzer.analyze_site(force_refresh=True)
        logger.info("Conocimiento refrescado exitosamente")


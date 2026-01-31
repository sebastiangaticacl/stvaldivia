"""
Servicio de Aplicación: Logs del Bot de IA (BimbaBot)
Gestiona el registro de conversaciones entre usuarios y el bot
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from flask import current_app
import uuid

from app.models import db
from app.helpers.timezone_utils import CHILE_TZ
from app.models.bot_log_models import BotLog


class BotLogService:
    """
    Servicio para gestión de logs del Bot de IA.
    Registra mensajes de usuarios y respuestas del bot para trazabilidad.
    """
    
    def __init__(self):
        """Inicializa el servicio de logs del bot"""
        pass
    
    def log_user_message(
        self, 
        canal: str, 
        conversation_id: str, 
        message: str, 
        meta: Optional[Dict[str, Any]] = None
    ) -> BotLog:
        """
        Registra un mensaje del usuario.
        
        Args:
            canal: Canal de comunicación ('instagram', 'whatsapp', 'web', 'interno', etc.)
            conversation_id: ID de la conversación (agrupa mensajes)
            message: Texto del mensaje del usuario
            meta: Metadatos adicionales (opcional)
            
        Returns:
            BotLog creado
        """
        try:
            # Asegurar que message nunca sea None (requerido por la base de datos)
            if message is None:
                message = ''
            elif not isinstance(message, str):
                message = str(message)
            
            bot_log = BotLog(
                timestamp=datetime.now(CHILE_TZ),
                canal=canal,
                direction='user',
                message=message,
                conversation_id=conversation_id,
                status='received',
                meta=None
            )
            
            if meta:
                bot_log.set_meta(meta)
            
            db.session.add(bot_log)
            db.session.commit()
            
            current_app.logger.info(f"📝 Log de usuario registrado: {canal} - {conversation_id[:8]}...")
            return bot_log
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error al registrar mensaje de usuario: {e}", exc_info=True)
            raise
    
    def log_bot_response(
        self,
        canal: str,
        conversation_id: str,
        message: str,
        model: Optional[str] = None,
        status: str = 'success',
        meta: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None
    ) -> BotLog:
        """
        Registra una respuesta del bot.
        
        Args:
            canal: Canal de comunicación
            conversation_id: ID de la conversación
            message: Texto de la respuesta del bot
            model: Nombre del modelo usado (opcional)
            status: Estado de la respuesta ('success', 'error', 'timeout', etc.)
            meta: Metadatos adicionales (opcional)
            request_id: ID de la llamada al modelo (opcional)
            
        Returns:
            BotLog creado
        """
        try:
            # Asegurar que message nunca sea None (requerido por la base de datos)
            if message is None:
                message = ''
            elif not isinstance(message, str):
                message = str(message)
            
            bot_log = BotLog(
                timestamp=datetime.now(CHILE_TZ),
                canal=canal,
                direction='bot',
                message=message,
                conversation_id=conversation_id,
                request_id=request_id,
                model=model,
                status=status,
                meta=None
            )
            
            if meta:
                bot_log.set_meta(meta)
            
            db.session.add(bot_log)
            db.session.commit()
            
            current_app.logger.info(f"🤖 Log de bot registrado: {canal} - {conversation_id[:8]}... - {status}")
            return bot_log
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error al registrar respuesta del bot: {e}", exc_info=True)
            raise
    
    def get_recent_logs(
        self,
        limit: int = 100,
        canal: Optional[str] = None,
        direction: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[BotLog]:
        """
        Obtiene los logs más recientes con filtros opcionales.
        
        Args:
            limit: Número máximo de logs a devolver (default: 100)
            canal: Filtrar por canal (opcional)
            direction: Filtrar por dirección ('user' o 'bot') (opcional)
            status: Filtrar por estado (opcional)
            
        Returns:
            Lista de BotLog ordenados por timestamp descendente
        """
        try:
            query = BotLog.query
            
            # Aplicar filtros
            if canal:
                query = query.filter(BotLog.canal == canal)
            if direction:
                query = query.filter(BotLog.direction == direction)
            if status:
                query = query.filter(BotLog.status == status)
            
            # Ordenar por timestamp descendente y limitar
            logs = query.order_by(BotLog.timestamp.desc()).limit(limit).all()
            
            return logs
            
        except Exception as e:
            current_app.logger.error(f"Error al obtener logs recientes: {e}", exc_info=True)
            return []
    
    def get_conversation_logs(self, conversation_id: str) -> List[BotLog]:
        """
        Obtiene todos los logs de una conversación específica.
        
        Args:
            conversation_id: ID de la conversación
            
        Returns:
            Lista de BotLog de la conversación ordenados por timestamp ascendente
        """
        try:
            logs = BotLog.query.filter_by(
                conversation_id=conversation_id
            ).order_by(BotLog.timestamp.asc()).all()
            
            return logs
            
        except Exception as e:
            current_app.logger.error(f"Error al obtener logs de conversación: {e}", exc_info=True)
            return []
    
    def generate_conversation_id(self) -> str:
        """
        Genera un nuevo ID de conversación único.
        
        Returns:
            String con UUID único
        """
        return str(uuid.uuid4())
    
    def generate_request_id(self) -> str:
        """
        Genera un nuevo ID de request único.
        
        Returns:
            String con UUID único
        """
        return str(uuid.uuid4())



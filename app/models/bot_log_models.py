"""
Modelo para registro de logs del Bot de IA (BimbaBot)
Registra conversaciones entre usuarios y el bot para trazabilidad
"""
from datetime import datetime
from . import db
from sqlalchemy import Index, Text
import json
import uuid
from app.helpers.timezone_utils import CHILE_TZ


class BotLog(db.Model):
    """
    Registro de logs del Bot de IA (BimbaBot).
    Registra mensajes del usuario y respuestas del bot para trazabilidad completa.
    """
    __tablename__ = 'bot_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Timestamp del log
    timestamp = db.Column(
        db.DateTime,
        default=lambda: datetime.now(CHILE_TZ),
        nullable=False,
        index=True
    )
    
    # Canal de comunicación
    canal = db.Column(db.String(50), nullable=False, index=True)  # 'instagram', 'whatsapp', 'web', 'interno', etc.
    
    # Dirección del mensaje
    direction = db.Column(db.String(10), nullable=False, index=True)  # 'user' o 'bot'
    
    # Contenido del mensaje
    message = db.Column(Text, nullable=False)  # Texto del usuario o respuesta del bot
    
    # Identificadores de conversación
    conversation_id = db.Column(db.String(100), nullable=False, index=True)  # Agrupa mensajes de una misma conversación
    request_id = db.Column(db.String(100), nullable=True)  # ID de la llamada al modelo (para debug)
    
    # Información del modelo
    model = db.Column(db.String(100), nullable=True)  # Nombre del modelo usado para la respuesta del bot
    
    # Estado del mensaje/respuesta
    status = db.Column(
        db.String(50), 
        default='received', 
        nullable=False,
        index=True
    )  # 'received', 'success', 'error', 'timeout', etc.
    
    # Metadatos adicionales (JSON)
    meta = db.Column(Text, nullable=True)  # Datos adicionales (ids externos, error_detail, etc.)
    
    # Índices para mejor rendimiento en consultas
    __table_args__ = (
        Index('idx_bot_logs_timestamp', 'timestamp'),
        Index('idx_bot_logs_canal', 'canal'),
        Index('idx_bot_logs_direction', 'direction'),
        Index('idx_bot_logs_conversation', 'conversation_id'),
        Index('idx_bot_logs_status', 'status'),
        Index('idx_bot_logs_timestamp_canal', 'timestamp', 'canal'),
    )
    
    def get_meta(self):
        """Obtiene los metadatos como diccionario"""
        if not self.meta:
            return {}
        try:
            return json.loads(self.meta)
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def set_meta(self, meta_dict):
        """Establece los metadatos desde un diccionario"""
        if meta_dict:
            self.meta = json.dumps(meta_dict, ensure_ascii=False)
        else:
            self.meta = None
    
    def to_dict(self):
        """Convierte el modelo a diccionario"""
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'canal': self.canal,
            'direction': self.direction,
            'message': self.message,
            'conversation_id': self.conversation_id,
            'request_id': self.request_id,
            'model': self.model,
            'status': self.status,
            'meta': self.get_meta()
        }
    
    def get_message_preview(self, max_length=100):
        """Obtiene una vista previa del mensaje truncado"""
        if not self.message:
            return ''
        if len(self.message) <= max_length:
            return self.message
        return self.message[:max_length] + '...'
    
    def get_conversation_id_short(self):
        """Obtiene una versión abreviada del conversation_id"""
        if not self.conversation_id:
            return ''
        if len(self.conversation_id) <= 12:
            return self.conversation_id
        return self.conversation_id[:8] + '...' + self.conversation_id[-4:]



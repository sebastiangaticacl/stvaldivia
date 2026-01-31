"""
Modelos de base de datos para redes sociales
Migración de social_media_messages.csv y social_media_responses.csv a tablas SQL
"""
from datetime import datetime
from . import db
from sqlalchemy import Index, ForeignKey
from sqlalchemy.orm import relationship


class SocialMediaMessage(db.Model):
    """Modelo para mensajes de redes sociales"""
    __tablename__ = 'social_media_messages'
    
    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.String(100), nullable=False, unique=True, index=True)
    platform = db.Column(db.String(50), nullable=False, index=True)
    sender = db.Column(db.String(200))
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, index=True)
    metadata_json = db.Column(db.Text)  # JSON string (renombrado de 'metadata' porque es reservado)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relación con respuestas
    responses = relationship("SocialMediaResponse", back_populates="message", cascade="all, delete-orphan")
    
    def to_dict(self):
        """Convierte a diccionario"""
        import json
        return {
            'id': self.id,
            'message_id': self.message_id,
            'platform': self.platform,
            'sender': self.sender,
            'content': self.content,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'metadata': json.loads(self.metadata_json) if self.metadata_json else {},
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<SocialMediaMessage {self.id}: {self.platform} - {self.message_id}>'


class SocialMediaResponse(db.Model):
    """Modelo para respuestas de redes sociales"""
    __tablename__ = 'social_media_responses'
    
    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.String(100), db.ForeignKey('social_media_messages.message_id'), nullable=False, index=True)
    response_text = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, index=True)
    model_used = db.Column(db.String(50))
    tokens_used = db.Column(db.Integer)
    metadata_json = db.Column(db.Text)  # JSON string (renombrado de 'metadata' porque es reservado)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relación con mensaje
    message = relationship("SocialMediaMessage", back_populates="responses")
    
    def to_dict(self):
        """Convierte a diccionario"""
        import json
        return {
            'id': self.id,
            'message_id': self.message_id,
            'response_text': self.response_text,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'model_used': self.model_used,
            'tokens_used': self.tokens_used,
            'metadata': json.loads(self.metadata_json) if self.metadata_json else {},
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<SocialMediaResponse {self.id}: {self.message_id}>'


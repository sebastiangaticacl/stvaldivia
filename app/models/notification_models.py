"""
Modelos para el sistema de notificaciones en tiempo real
"""
from datetime import datetime
from app.models import db
from app.helpers.timezone_utils import CHILE_TZ
import pytz


class Notification(db.Model):
    """Modelo para notificaciones del sistema"""
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Tipo de notificación
    type = db.Column(db.String(50), nullable=False)  # 'cierre_pendiente', 'diferencia_grande', 'fraude', 'info', 'success', 'warning', 'error'
    
    # Contenido
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    
    # Destinatario (None = todos los admins)
    target_user = db.Column(db.String(100), nullable=True)
    
    # Estado
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    is_dismissed = db.Column(db.Boolean, default=False, nullable=False)
    
    # Prioridad (1=baja, 2=normal, 3=alta, 4=crítica)
    priority = db.Column(db.Integer, default=2, nullable=False)
    
    # Datos adicionales (JSON)
    data = db.Column(db.Text, nullable=True)  # JSON string con datos adicionales
    
    # Acción (URL a la que redirigir al hacer click)
    action_url = db.Column(db.String(500), nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(CHILE_TZ), nullable=False)
    read_at = db.Column(db.DateTime, nullable=True)
    
    def __repr__(self):
        return f'<Notification {self.id}: {self.type} - {self.title}>'
    
    def to_dict(self):
        """Convierte la notificación a diccionario"""
        return {
            'id': self.id,
            'type': self.type,
            'title': self.title,
            'message': self.message,
            'target_user': self.target_user,
            'is_read': self.is_read,
            'is_dismissed': self.is_dismissed,
            'priority': self.priority,
            'data': self.data,
            'action_url': self.action_url,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'read_at': self.read_at.strftime('%Y-%m-%d %H:%M:%S') if self.read_at else None,
            'created_at_timestamp': self.created_at.timestamp() if self.created_at else None
        }
    
    def mark_as_read(self):
        """Marca la notificación como leída"""
        if not self.is_read:
            self.is_read = True
            self.read_at = datetime.now(CHILE_TZ)
            db.session.commit()
    
    def dismiss(self):
        """Descarta la notificación"""
        self.is_dismissed = True
        db.session.commit()
    
    @staticmethod
    def create_notification(type, title, message, target_user=None, priority=2, data=None, action_url=None):
        """
        Crea una nueva notificación
        
        Args:
            type: Tipo de notificación
            title: Título
            message: Mensaje
            target_user: Usuario destinatario (None = todos los admins)
            priority: Prioridad (1-4)
            data: Datos adicionales (dict o JSON string)
            action_url: URL de acción
        
        Returns:
            Notification: La notificación creada
        """
        import json
        
        notification = Notification(
            type=type,
            title=title,
            message=message,
            target_user=target_user,
            priority=priority,
            data=json.dumps(data) if isinstance(data, dict) else data,
            action_url=action_url
        )
        
        db.session.add(notification)
        db.session.commit()
        
        return notification
    
    @staticmethod
    def get_unread_count(user=None):
        """Obtiene el número de notificaciones no leídas"""
        query = Notification.query.filter_by(is_read=False, is_dismissed=False)
        
        if user:
            query = query.filter((Notification.target_user == user) | (Notification.target_user == None))
        else:
            query = query.filter(Notification.target_user == None)
        
        return query.count()
    
    @staticmethod
    def get_recent(user=None, limit=20, include_read=False):
        """Obtiene las notificaciones recientes"""
        query = Notification.query.filter_by(is_dismissed=False)
        
        if not include_read:
            query = query.filter_by(is_read=False)
        
        if user:
            query = query.filter((Notification.target_user == user) | (Notification.target_user == None))
        else:
            query = query.filter(Notification.target_user == None)
        
        return query.order_by(Notification.created_at.desc()).limit(limit).all()
    
    @staticmethod
    def mark_all_as_read(user=None):
        """Marca todas las notificaciones como leídas"""
        query = Notification.query.filter_by(is_read=False, is_dismissed=False)
        
        if user:
            query = query.filter((Notification.target_user == user) | (Notification.target_user == None))
        else:
            query = query.filter(Notification.target_user == None)
        
        now = datetime.now(CHILE_TZ)
        query.update({
            'is_read': True,
            'read_at': now
        })
        db.session.commit()

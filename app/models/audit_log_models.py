"""
Modelo para registro de auditoría de acciones críticas
"""
from datetime import datetime
from app.models import db
from sqlalchemy import Index, Text
import pytz
from app.helpers.timezone_utils import CHILE_TZ


class AuditLog(db.Model):
    """
    Registro de auditoría para acciones críticas del sistema.
    Registra quién, qué, cuándo y desde dónde se realizaron acciones importantes.
    """
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Usuario que realizó la acción
    user_id = db.Column(db.String(200), nullable=True, index=True)
    username = db.Column(db.String(200), nullable=True)
    
    # Acción realizada
    action = db.Column(db.String(100), nullable=False, index=True)  # 'mark_payment', 'update_salary', 'close_shift', etc.
    entity_type = db.Column(db.String(50), nullable=True)  # 'EmployeeShift', 'Employee', 'Jornada', etc.
    entity_id = db.Column(db.String(100), nullable=True, index=True)
    
    # Valores antes y después (JSON)
    old_value = db.Column(Text, nullable=True)
    new_value = db.Column(Text, nullable=True)
    
    # Información de la solicitud
    ip_address = db.Column(db.String(100), nullable=True)
    user_agent = db.Column(db.String(500), nullable=True)
    request_method = db.Column(db.String(10), nullable=True)  # 'GET', 'POST', etc.
    request_path = db.Column(db.String(500), nullable=True)
    
    # Resultado
    success = db.Column(db.Boolean, default=True, nullable=False)
    error_message = db.Column(Text, nullable=True)
    
    # Timestamp
    timestamp = db.Column(
        db.DateTime,
        default=lambda: datetime.now(CHILE_TZ).astimezone(pytz.UTC).replace(tzinfo=None),
        nullable=False,
        index=True
    )
    
    __table_args__ = (
        Index('idx_audit_log_user_action', 'user_id', 'action'),
        Index('idx_audit_log_entity', 'entity_type', 'entity_id'),
        Index('idx_audit_log_timestamp', 'timestamp'),
    )
    
    def to_dict(self):
        """Convierte el modelo a diccionario"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'username': self.username,
            'action': self.action,
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'old_value': self.old_value,
            'new_value': self.new_value,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'request_method': self.request_method,
            'request_path': self.request_path,
            'success': self.success,
            'error_message': self.error_message,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }




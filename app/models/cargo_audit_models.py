"""
Modelo de auditoría para cambios en cargos y sueldos
"""
from datetime import datetime
from . import db
from sqlalchemy import Text, Index
import pytz
from app.helpers.timezone_utils import CHILE_TZ
import json


class CargoSalaryAuditLog(db.Model):
    """
    Registro de auditoría para cambios en cargos y configuraciones de sueldos
    """
    __tablename__ = 'cargo_salary_audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Tipo de cambio
    action = db.Column(db.String(50), nullable=False)  # 'create', 'update', 'delete'
    entity_type = db.Column(db.String(50), nullable=False)  # 'cargo', 'salary_config'
    
    # Entidad afectada
    cargo_nombre = db.Column(db.String(100), nullable=True, index=True)
    
    # Valores anteriores (JSON)
    old_values = db.Column(Text, nullable=True)
    
    # Valores nuevos (JSON)
    new_values = db.Column(Text, nullable=True)
    
    # Usuario que hizo el cambio
    changed_by = db.Column(db.String(100), nullable=False, index=True)
    changed_by_username = db.Column(db.String(100), nullable=False)
    
    # Información adicional
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(500), nullable=True)
    
    # Timestamp
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(CHILE_TZ).astimezone(pytz.UTC).replace(tzinfo=None), nullable=False, index=True)
    
    # Índices
    __table_args__ = (
        Index('idx_cargo_audit_cargo', 'cargo_nombre'),
        Index('idx_cargo_audit_user', 'changed_by'),
        Index('idx_cargo_audit_date', 'created_at'),
        Index('idx_cargo_audit_action', 'action'),
    )
    
    def to_dict(self):
        """Convierte el modelo a diccionario"""
        return {
            'id': self.id,
            'action': self.action,
            'entity_type': self.entity_type,
            'cargo_nombre': self.cargo_nombre,
            'old_values': json.loads(self.old_values) if self.old_values else None,
            'new_values': json.loads(self.new_values) if self.new_values else None,
            'changed_by': self.changed_by,
            'changed_by_username': self.changed_by_username,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }






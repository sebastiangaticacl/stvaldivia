"""
Modelos para Tickets QR de Guardarropía
FASE 3: Sistema de tickets QR para guardarropía con anti-reuso
"""
from datetime import datetime
from . import db
from sqlalchemy import Index, Text
import uuid
import hashlib
from flask import current_app
from app.helpers.timezone_utils import CHILE_TZ


class GuardarropiaTicket(db.Model):
    """
    Ticket QR de Guardarropía
    Cada depósito genera un ticket único con QR token para retiro seguro
    """
    __tablename__ = 'guardarropia_tickets'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Código visible (ej: "GR 11725" o el ticket_code del GuardarropiaItem)
    display_code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    
    # Token QR (UUIDv4) - NO predecible
    qr_token = db.Column(db.String(64), unique=True, nullable=False, index=True)
    
    # Asociación con item de guardarropía
    item_id = db.Column(db.Integer, db.ForeignKey('guardarropia_items.id'), nullable=False, unique=True, index=True)
    
    # Asociación con turno/jornada
    jornada_id = db.Column(db.Integer, db.ForeignKey('jornadas.id'), nullable=True, index=True)
    shift_date = db.Column(db.String(50), nullable=True, index=True)
    
    # Estado del ticket
    status = db.Column(db.String(20), nullable=False, default='open', index=True)
    # Estados: 'open', 'paid', 'checked_in', 'checked_out', 'void'
    
    # Información de creación
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    created_by_user_id = db.Column(db.String(100), nullable=False, index=True)
    created_by_user_name = db.Column(db.String(200), nullable=False)
    
    # Información de pago (si aplica)
    paid_at = db.Column(db.DateTime, nullable=True)
    paid_by = db.Column(db.String(200), nullable=True)
    price = db.Column(db.Numeric(10, 2), nullable=True)
    payment_type = db.Column(db.String(20), nullable=True)
    
    # Información de retiro
    checked_out_at = db.Column(db.DateTime, nullable=True, index=True)
    checked_out_by = db.Column(db.String(200), nullable=True)
    
    # Hash de integridad (opcional)
    hash_integridad = db.Column(db.String(64), nullable=True, index=True)
    
    # Relaciones
    item = db.relationship('GuardarropiaItem', backref='ticket_qr', lazy=True, uselist=False)
    jornada = db.relationship('Jornada', backref='guardarropia_tickets', lazy=True)
    logs = db.relationship('GuardarropiaTicketLog', backref='ticket', lazy=True, cascade='all, delete-orphan')
    
    # Índices (se crean en migración manual para evitar conflictos)
    # __table_args__ = (
    #     Index('idx_guardarropia_ticket_status', 'status', 'created_at'),
    #     Index('idx_guardarropia_ticket_qr_token', 'qr_token'),
    #     Index('idx_guardarropia_ticket_item', 'item_id'),
    # )
    
    def to_dict(self):
        """Convierte a diccionario"""
        return {
            'id': self.id,
            'display_code': self.display_code,
            'qr_token': self.qr_token,
            'item_id': self.item_id,
            'jornada_id': self.jornada_id,
            'shift_date': self.shift_date,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'created_by_user_id': self.created_by_user_id,
            'created_by_user_name': self.created_by_user_name,
            'paid_at': self.paid_at.isoformat() if self.paid_at else None,
            'paid_by': self.paid_by,
            'price': float(self.price) if self.price else None,
            'payment_type': self.payment_type,
            'checked_out_at': self.checked_out_at.isoformat() if self.checked_out_at else None,
            'checked_out_by': self.checked_out_by,
            'item': self.item.to_dict() if self.item else None
        }
    
    def is_checked_out(self) -> bool:
        """Verifica si el ticket ya fue retirado"""
        return self.status == 'checked_out'
    
    def is_void(self) -> bool:
        """Verifica si el ticket está anulado"""
        return self.status == 'void'
    
    def can_check_out(self) -> bool:
        """Verifica si se puede retirar el item"""
        return self.status in ['open', 'paid', 'checked_in'] and not self.is_void()
    
    @staticmethod
    def generate_qr_token() -> str:
        """
        Genera token QR seguro (UUIDv4)
        Este token es lo que va en el QR, no el display_code
        """
        return str(uuid.uuid4())
    
    @staticmethod
    def generate_hash_integridad(item_id: int, qr_token: str) -> str:
        """
        Genera hash de integridad para validación
        """
        secret = current_app.config.get('SECRET_KEY', 'default-secret')
        data = f"{item_id}:{qr_token}:{secret}"
        return hashlib.sha256(data.encode()).hexdigest()
    
    def __repr__(self):
        return f'<GuardarropiaTicket {self.display_code}: {self.status}>'


class GuardarropiaTicketLog(db.Model):
    """
    Log de auditoría para todas las acciones de tickets de guardarropía
    Registra emisión, pago, check-in, check-out, anulaciones
    """
    __tablename__ = 'guardarropia_ticket_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Referencia al ticket
    ticket_id = db.Column(db.Integer, db.ForeignKey('guardarropia_tickets.id'), nullable=False, index=True)
    
    # Acción realizada
    action = db.Column(db.String(20), nullable=False, index=True)
    # Acciones: 'issued', 'paid', 'check_in', 'check_out', 'void'
    
    # Actor (quién hizo la acción)
    actor_user_id = db.Column(db.String(100), nullable=True, index=True)
    actor_name = db.Column(db.String(200), nullable=True)
    
    # Detalles adicionales
    notes = db.Column(Text, nullable=True)
    
    # Información de red
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(500), nullable=True)
    
    # Timestamp
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Índices (se crean en migración manual para evitar conflictos)
    # __table_args__ = (
    #     Index('idx_guardarropia_log_action_date', 'action', 'created_at'),
    #     Index('idx_guardarropia_log_actor_date', 'actor_user_id', 'created_at'),
    # )
    
    def to_dict(self):
        """Convierte a diccionario"""
        return {
            'id': self.id,
            'ticket_id': self.ticket_id,
            'action': self.action,
            'actor_user_id': self.actor_user_id,
            'actor_name': self.actor_name,
            'notes': self.notes,
            'ip_address': self.ip_address,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<GuardarropiaTicketLog {self.action}: ticket={self.ticket_id}>'


"""
Modelos para Tickets de Entrega con QR
Sistema de tickets QR para entregas en barra y guardarropía
"""
from datetime import datetime
from . import db
from sqlalchemy import Index, Text
import uuid
import hashlib
from flask import current_app
from app.helpers.timezone_utils import CHILE_TZ


class TicketEntrega(db.Model):
    """
    Ticket de Entrega con QR para ventas POS
    Cada venta genera un ticket único con QR token para escaneo seguro
    """
    __tablename__ = 'ticket_entregas'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Código visible (ej: "BMB 11725")
    display_code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    
    # Token QR (UUIDv4 o token firmado) - NO predecible
    qr_token = db.Column(db.String(64), unique=True, nullable=False, index=True)
    
    # Asociación con venta
    sale_id = db.Column(db.Integer, db.ForeignKey('pos_sales.id'), nullable=False, unique=True, index=True)
    
    # Asociación con turno/jornada
    jornada_id = db.Column(db.Integer, db.ForeignKey('jornadas.id'), nullable=False, index=True)
    shift_date = db.Column(db.String(50), nullable=False, index=True)
    
    # Estado del ticket
    status = db.Column(db.String(20), nullable=False, default='open', index=True)
    # Estados: 'open', 'partial', 'delivered', 'void'
    
    # Información de creación
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    created_by_employee_id = db.Column(db.String(50), nullable=False, index=True)
    created_by_employee_name = db.Column(db.String(200), nullable=False)
    register_id = db.Column(db.String(50), nullable=False, index=True)
    
    # Información de entrega
    delivered_at = db.Column(db.DateTime, nullable=True, index=True)
    delivered_by = db.Column(db.String(200), nullable=True)
    
    # Hash de integridad (opcional, para validación)
    hash_integridad = db.Column(db.String(64), nullable=True, index=True)
    
    # Relaciones
    sale = db.relationship('PosSale', backref='ticket_entrega', lazy=True)
    jornada = db.relationship('Jornada', backref='ticket_entregas', lazy=True)
    items = db.relationship('TicketEntregaItem', backref='ticket', lazy=True, cascade='all, delete-orphan')
    
    # Índices
    __table_args__ = (
        Index('idx_ticket_entrega_status', 'status', 'created_at'),
        Index('idx_ticket_entrega_jornada', 'jornada_id', 'shift_date'),
        Index('idx_ticket_entrega_qr_token', 'qr_token'),
    )
    
    def to_dict(self):
        """Convierte a diccionario"""
        return {
            'id': self.id,
            'display_code': self.display_code,
            'qr_token': self.qr_token,
            'sale_id': self.sale_id,
            'jornada_id': self.jornada_id,
            'shift_date': self.shift_date,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'created_by_employee_id': self.created_by_employee_id,
            'created_by_employee_name': self.created_by_employee_name,
            'register_id': self.register_id,
            'delivered_at': self.delivered_at.isoformat() if self.delivered_at else None,
            'delivered_by': self.delivered_by,
            'items': [item.to_dict() for item in self.items] if self.items else []
        }
    
    def is_delivered(self) -> bool:
        """Verifica si el ticket está completamente entregado"""
        return self.status == 'delivered'
    
    def is_void(self) -> bool:
        """Verifica si el ticket está anulado"""
        return self.status == 'void'
    
    def can_deliver(self) -> bool:
        """Verifica si se pueden hacer entregas en este ticket"""
        return self.status in ['open', 'partial'] and not self.is_void()
    
    def update_status(self):
        """Actualiza el estado basado en items entregados"""
        if not self.items:
            return
        
        total_qty = sum(item.qty for item in self.items)
        delivered_qty = sum(item.delivered_qty for item in self.items)
        
        if delivered_qty == 0:
            self.status = 'open'
        elif delivered_qty < total_qty:
            self.status = 'partial'
        elif delivered_qty == total_qty:
            self.status = 'delivered'
            self.delivered_at = datetime.now(CHILE_TZ).replace(tzinfo=None)
    
    @staticmethod
    def generate_display_code() -> str:
        """
        Genera código visible incremental (ej: "BMB 11725")
        Formato: BMB + número secuencial
        """
        # Obtener último número usado
        last_ticket = TicketEntrega.query.order_by(TicketEntrega.id.desc()).first()
        if last_ticket and last_ticket.display_code:
            # Extraer número del último código
            try:
                last_num = int(last_ticket.display_code.split()[-1])
                next_num = last_num + 1
            except (ValueError, IndexError):
                next_num = 1
        else:
            next_num = 1
        
        return f"BMB {next_num:05d}"
    
    @staticmethod
    def generate_qr_token() -> str:
        """
        Genera token QR seguro (UUIDv4)
        Este token es lo que va en el QR, no el display_code
        """
        return str(uuid.uuid4())
    
    @staticmethod
    def generate_hash_integridad(sale_id: int, qr_token: str) -> str:
        """
        Genera hash de integridad para validación
        """
        secret = current_app.config.get('SECRET_KEY', 'default-secret')
        data = f"{sale_id}:{qr_token}:{secret}"
        return hashlib.sha256(data.encode()).hexdigest()
    
    def __repr__(self):
        return f'<TicketEntrega {self.display_code}: {self.status}>'


class TicketEntregaItem(db.Model):
    """
    Item individual de un ticket de entrega
    Rastrea qué productos están pendientes/entregados
    """
    __tablename__ = 'ticket_entrega_items'
    
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('ticket_entregas.id'), nullable=False, index=True)
    
    # Información del producto
    product_id = db.Column(db.String(50), nullable=False, index=True)
    product_name = db.Column(db.String(200), nullable=False)
    
    # Cantidades
    qty = db.Column(db.Integer, nullable=False)  # Cantidad vendida
    delivered_qty = db.Column(db.Integer, nullable=False, default=0)  # Cantidad entregada
    
    # Estado
    status = db.Column(db.String(20), nullable=False, default='pending', index=True)
    # Estados: 'pending', 'delivered'
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    delivered_at = db.Column(db.DateTime, nullable=True)
    
    # Índices
    __table_args__ = (
        Index('idx_ticket_item_ticket_status', 'ticket_id', 'status'),
        Index('idx_ticket_item_product', 'product_id', 'ticket_id'),
    )
    
    def to_dict(self):
        """Convierte a diccionario"""
        return {
            'id': self.id,
            'ticket_id': self.ticket_id,
            'product_id': self.product_id,
            'product_name': self.product_name,
            'qty': self.qty,
            'delivered_qty': self.delivered_qty,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'delivered_at': self.delivered_at.isoformat() if self.delivered_at else None
        }
    
    def is_delivered(self) -> bool:
        """Verifica si el item está completamente entregado"""
        return self.status == 'delivered' and self.delivered_qty >= self.qty
    
    def can_deliver(self, qty_to_deliver: int = 1) -> bool:
        """Verifica si se puede entregar la cantidad especificada"""
        return (self.status != 'delivered' and 
                self.delivered_qty + qty_to_deliver <= self.qty)
    
    def deliver(self, qty_to_deliver: int = 1):
        """Marca cantidad como entregada"""
        if not self.can_deliver(qty_to_deliver):
            raise ValueError(f"No se puede entregar {qty_to_deliver} unidades. Ya entregadas: {self.delivered_qty}, Total: {self.qty}")
        
        self.delivered_qty += qty_to_deliver
        
        if self.delivered_qty >= self.qty:
            self.status = 'delivered'
            self.delivered_at = datetime.now(CHILE_TZ).replace(tzinfo=None)
    
    def __repr__(self):
        return f'<TicketEntregaItem {self.product_name}: {self.delivered_qty}/{self.qty}>'


class DeliveryLog(db.Model):
    """
    Log de auditoría para todas las acciones de entrega
    Registra escaneos, entregas, rechazos, anulaciones
    """
    __tablename__ = 'delivery_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Referencia al ticket
    ticket_id = db.Column(db.Integer, db.ForeignKey('ticket_entregas.id'), nullable=True, index=True)
    item_id = db.Column(db.Integer, db.ForeignKey('ticket_entrega_items.id'), nullable=True, index=True)
    
    # Acción realizada
    action = db.Column(db.String(20), nullable=False, index=True)
    # Acciones: 'scan', 'deliver', 'reject', 'void', 'created'
    
    # Actor (quién hizo la acción)
    bartender_user_id = db.Column(db.String(100), nullable=True, index=True)
    bartender_name = db.Column(db.String(200), nullable=True)
    scanner_device_id = db.Column(db.String(100), nullable=True, index=True)
    
    # Detalles
    qty = db.Column(db.Integer, nullable=True)  # Cantidad (si aplica)
    product_name = db.Column(db.String(200), nullable=True)
    
    # Información de red
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(500), nullable=True)
    
    # Timestamp
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relaciones
    ticket = db.relationship('TicketEntrega', backref='delivery_logs', lazy=True)
    item = db.relationship('TicketEntregaItem', backref='delivery_logs', lazy=True)
    
    # Índices
    __table_args__ = (
        Index('idx_delivery_log_action_date', 'action', 'created_at'),
        Index('idx_delivery_log_bartender_date', 'bartender_user_id', 'created_at'),
    )
    
    def to_dict(self):
        """Convierte a diccionario"""
        return {
            'id': self.id,
            'ticket_id': self.ticket_id,
            'item_id': self.item_id,
            'action': self.action,
            'bartender_user_id': self.bartender_user_id,
            'bartender_name': self.bartender_name,
            'scanner_device_id': self.scanner_device_id,
            'qty': self.qty,
            'product_name': self.product_name,
            'ip_address': self.ip_address,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<DeliveryLog {self.action}: ticket={self.ticket_id}, item={self.item_id}>'


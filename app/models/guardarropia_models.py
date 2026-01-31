"""
Modelos de base de datos para el sistema de guardarropía
Gestiona el guardado y retiro de prendas/abrigos de clientes
"""
from datetime import datetime
from . import db
from sqlalchemy import Index


class GuardarropiaItem(db.Model):
    """Modelo para items guardados en guardarropía"""
    __tablename__ = 'guardarropia_items'
    
    id = db.Column(db.Integer, primary_key=True)
    ticket_code = db.Column(db.String(50), unique=True, nullable=False, index=True)  # Código único del ticket
    description = db.Column(db.String(500), nullable=True)  # Descripción de la prenda
    customer_name = db.Column(db.String(200), nullable=True)  # Nombre del cliente (opcional)
    customer_phone = db.Column(db.String(50), nullable=True)  # Teléfono del cliente (opcional)
    
    # Estado
    status = db.Column(db.String(20), nullable=False, default='deposited', index=True)  # deposited, retrieved, lost
    
    # Fechas
    deposited_at = db.Column(db.DateTime, nullable=False, index=True)
    retrieved_at = db.Column(db.DateTime, nullable=True)
    
    # Usuarios
    deposited_by = db.Column(db.String(100), nullable=False)  # Usuario que guardó
    retrieved_by = db.Column(db.String(100), nullable=True)  # Usuario que retiró
    
    # Asociación con turno/jornada
    shift_date = db.Column(db.String(10), nullable=True, index=True)  # YYYY-MM-DD
    
    # Información de venta (POS)
    price = db.Column(db.Numeric(10, 2), nullable=True)  # Precio total del espacio/cluster
    clusters = db.Column(db.Integer, nullable=True, default=1)  # Cantidad de clusters/espacios
    cluster_numbers = db.Column(db.String(200), nullable=True)  # Números específicos de clusters asignados (ej: "1,2,3")
    payment_type = db.Column(db.String(20), nullable=True)  # cash, debit, credit
    sale_id = db.Column(db.Integer, nullable=True, index=True)  # ID de la venta POS asociada
    
    # Notas adicionales
    notes = db.Column(db.Text, nullable=True)
    
    # Campos para prendas no retiradas (fotos y seguimiento)
    photo_path = db.Column(db.String(500), nullable=True)  # Ruta de la foto
    marked_unretrieved_at = db.Column(db.DateTime, nullable=True)  # Fecha cuando se marcó como no retirado
    marked_unretrieved_by = db.Column(db.String(100), nullable=True)  # Usuario que marcó como no retirado
    tracking_notes = db.Column(db.Text, nullable=True)  # Notas de seguimiento
    last_tracking_date = db.Column(db.DateTime, nullable=True)  # Última fecha de seguimiento
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Índices compuestos
    __table_args__ = (
        Index('idx_guardarropia_status_date', 'status', 'shift_date'),
        Index('idx_guardarropia_ticket_status', 'ticket_code', 'status'),
    )
    
    def to_dict(self):
        """Convierte a diccionario"""
        return {
            'id': self.id,
            'ticket_code': self.ticket_code,
            'description': self.description,
            'customer_name': self.customer_name,
            'customer_phone': self.customer_phone,
            'status': self.status,
            'deposited_at': self.deposited_at.isoformat() if self.deposited_at else None,
            'retrieved_at': self.retrieved_at.isoformat() if self.retrieved_at else None,
            'deposited_by': self.deposited_by,
            'retrieved_by': self.retrieved_by,
            'shift_date': self.shift_date,
            'price': float(self.price) if self.price else None,
            'clusters': self.clusters or 1,
            'cluster_numbers': self.cluster_numbers,
            'payment_type': self.payment_type,
            'sale_id': self.sale_id,
            'notes': self.notes,
            'photo_path': self.photo_path,
            'marked_unretrieved_at': self.marked_unretrieved_at.isoformat() if self.marked_unretrieved_at else None,
            'marked_unretrieved_by': self.marked_unretrieved_by,
            'tracking_notes': self.tracking_notes,
            'last_tracking_date': self.last_tracking_date.isoformat() if self.last_tracking_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def is_deposited(self) -> bool:
        """Verifica si el item está guardado"""
        return self.status == 'deposited'
    
    def is_retrieved(self) -> bool:
        """Verifica si el item fue retirado"""
        return self.status == 'retrieved'
    
    def is_lost(self) -> bool:
        """Verifica si el item está marcado como perdido"""
        return self.status == 'lost'
    
    def is_unretrieved(self) -> bool:
        """Verifica si el item está marcado como no retirado (tiene fecha de marcado)"""
        return self.marked_unretrieved_at is not None
    
    def days_since_deposited(self) -> int:
        """Calcula los días desde que fue depositado"""
        if not self.deposited_at:
            return 0
        delta = datetime.utcnow() - self.deposited_at
        return delta.days
    
    def days_since_unretrieved(self) -> int:
        """Calcula los días desde que fue marcado como no retirado"""
        if not self.marked_unretrieved_at:
            return 0
        delta = datetime.utcnow() - self.marked_unretrieved_at
        return delta.days
    
    def __repr__(self):
        return f'<GuardarropiaItem {self.id}: {self.ticket_code} - {self.status}>'


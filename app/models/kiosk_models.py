"""
Modelos de base de datos para el sistema de Kiosko
"""
from datetime import datetime
from . import db


class Pago(db.Model):
    """Modelo para pagos del kiosko"""
    __tablename__ = 'pagos'
    
    id = db.Column(db.Integer, primary_key=True)
    monto = db.Column(db.Numeric(10, 2), nullable=False)
    moneda = db.Column(db.String(3), default='CLP', nullable=False)
    estado = db.Column(db.String(20), default='PENDING', nullable=False)  # PENDING, PAID, FAILED
    metodo = db.Column(db.String(20), default='MANUAL', nullable=False)
    kiosko_id = db.Column(db.String(50), nullable=False)
    
    # PHP POS integration
    sale_id_phppos = db.Column(db.String(50), nullable=True)
    
    # Transaction ID genérico (para almacenar cualquier ID de transacción)
    transaction_id = db.Column(db.String(100), nullable=True)
    
    # SumUp integration
    sumup_checkout_id = db.Column(db.String(100), nullable=True, index=True)
    sumup_checkout_url = db.Column(db.Text, nullable=True)
    sumup_merchant_code = db.Column(db.String(50), nullable=True)
    
    # Ticket code único
    ticket_code = db.Column(db.String(20), unique=True, nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relación con items
    items = db.relationship('PagoItem', backref='pago', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        """Convierte el modelo a diccionario"""
        return {
            'id': self.id,
            'monto': float(self.monto),
            'moneda': self.moneda,
            'estado': self.estado,
            'metodo': self.metodo,
            'kiosko_id': self.kiosko_id,
            'ticket_code': self.ticket_code,
            'sale_id_phppos': self.sale_id_phppos,
            'sumup_checkout_id': self.sumup_checkout_id,
            'sumup_checkout_url': self.sumup_checkout_url,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class PagoItem(db.Model):
    """Modelo para items de un pago"""
    __tablename__ = 'pagos_items'
    
    id = db.Column(db.Integer, primary_key=True)
    pago_id = db.Column(db.Integer, db.ForeignKey('pagos.id'), nullable=False)
    
    # Referencia a PHP POS
    item_id_phppos = db.Column(db.String(50), nullable=False)
    
    # Datos del item (para referencia rápida)
    nombre_item = db.Column(db.String(200), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    precio_unitario = db.Column(db.Numeric(10, 2), nullable=False)
    total_linea = db.Column(db.Numeric(10, 2), nullable=False)
    
    def to_dict(self):
        """Convierte el modelo a diccionario"""
        return {
            'id': self.id,
            'pago_id': self.pago_id,
            'item_id_phppos': self.item_id_phppos,
            'nombre_item': self.nombre_item,
            'cantidad': self.cantidad,
            'precio_unitario': float(self.precio_unitario),
            'total_linea': float(self.total_linea),
        }






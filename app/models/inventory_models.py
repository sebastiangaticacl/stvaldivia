"""
Modelos de base de datos para inventario
Migración de inventory.json a tabla SQL
"""
from datetime import datetime, date
from . import db
from sqlalchemy import Index


class InventoryItem(db.Model):
    """Modelo para items de inventario"""
    __tablename__ = 'inventory_items'
    
    id = db.Column(db.Integer, primary_key=True)
    shift_date = db.Column(db.Date, nullable=False, index=True)
    barra = db.Column(db.String(100), nullable=False, index=True)
    product_name = db.Column(db.String(200), nullable=False)
    initial_quantity = db.Column(db.Integer, nullable=False)
    delivered_quantity = db.Column(db.Integer, default=0, nullable=False)
    final_quantity = db.Column(db.Integer)
    status = db.Column(db.String(50), default='open', nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Índice compuesto para búsquedas frecuentes
    __table_args__ = (
        Index('idx_inventory_shift_barra', 'shift_date', 'barra'),
    )
    
    def to_dict(self):
        """Convierte a diccionario"""
        return {
            'id': self.id,
            'shift_date': self.shift_date.isoformat() if self.shift_date else None,
            'barra': self.barra,
            'product_name': self.product_name,
            'initial_quantity': self.initial_quantity,
            'delivered_quantity': self.delivered_quantity,
            'final_quantity': self.final_quantity,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<InventoryItem {self.id}: {self.product_name} - {self.shift_date}>'















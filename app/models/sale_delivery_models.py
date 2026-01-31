"""
Modelos para tracking completo de entregas de tickets
Sistema de estado de entrega y log detallado por bartender
"""
from datetime import datetime
from . import db
from sqlalchemy import Index, Text, JSON
from decimal import Decimal


class SaleDeliveryStatus(db.Model):
    """
    Estado de entrega de un ticket completo.
    Rastrea qué productos están pendientes, entregados o completados.
    """
    __tablename__ = 'sale_delivery_status'
    
    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.String(50), nullable=False, unique=True, index=True)
    
    # Estado general del ticket
    estado_entrega = db.Column(db.String(20), nullable=False, default='pendiente', index=True)
    # Estados: 'pendiente', 'en_proceso', 'completado', 'cancelado'
    
    # Información de la venta (snapshot)
    total_items = db.Column(db.Integer, nullable=False, default=0)
    items_entregados = db.Column(db.Integer, nullable=False, default=0)
    items_pendientes = db.Column(db.Integer, nullable=False, default=0)
    
    # Detalle de productos (JSON)
    # Estructura: [{"product_name": "Mojito", "quantity": 2, "entregado": 0, "pendiente": 2}, ...]
    items_detail = db.Column(JSON, nullable=True)
    
    # Información del escaneo
    scanned_at = db.Column(db.DateTime, nullable=True, index=True)
    scanner_id = db.Column(db.String(100), nullable=True)  # ID del escáner/bartender que escaneó
    scanner_name = db.Column(db.String(200), nullable=True)
    
    # Información de finalización
    completed_at = db.Column(db.DateTime, nullable=True)
    completed_by = db.Column(db.String(100), nullable=True)
    
    # Metadatos
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Índices
    __table_args__ = (
        Index('idx_sale_delivery_status_estado', 'estado_entrega'),
        Index('idx_sale_delivery_status_scanner', 'scanner_id'),
    )
    
    def to_dict(self):
        """Convierte a diccionario"""
        return {
            'id': self.id,
            'sale_id': self.sale_id,
            'estado_entrega': self.estado_entrega,
            'total_items': self.total_items,
            'items_entregados': self.items_entregados,
            'items_pendientes': self.items_pendientes,
            'items_detail': self.items_detail or [],
            'scanned_at': self.scanned_at.isoformat() if self.scanned_at else None,
            'scanner_id': self.scanner_id,
            'scanner_name': self.scanner_name,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'completed_by': self.completed_by
        }
    
    def is_completed(self) -> bool:
        """Verifica si el ticket está completamente entregado"""
        return self.estado_entrega == 'completado' and self.items_pendientes == 0
    
    def update_status(self):
        """Actualiza el estado basado en items entregados"""
        if self.items_pendientes == 0 and self.items_entregados > 0:
            self.estado_entrega = 'completado'
            self.completed_at = datetime.utcnow()
        elif self.items_entregados > 0:
            self.estado_entrega = 'en_proceso'
        else:
            self.estado_entrega = 'pendiente'
    
    def __repr__(self):
        return f'<SaleDeliveryStatus {self.sale_id}: {self.estado_entrega}>'


class DeliveryItem(db.Model):
    """
    Log detallado de cada entrega individual de producto.
    Registra quién entregó qué, cuándo y qué insumos se descontaron.
    """
    __tablename__ = 'delivery_items'
    
    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.String(50), nullable=False, index=True)
    
    # Producto entregado
    product_name = db.Column(db.String(200), nullable=False, index=True)
    product_id = db.Column(db.Integer, nullable=True, index=True)  # ID del producto si existe
    
    # Cantidad entregada (normalmente 1 por entrega individual)
    quantity_delivered = db.Column(db.Integer, nullable=False, default=1)
    
    # Información del bartender
    bartender_id = db.Column(db.String(100), nullable=False, index=True)  # ID del escáner/bartender
    bartender_name = db.Column(db.String(200), nullable=True)
    
    # Ubicación
    location = db.Column(db.String(100), nullable=False, index=True)  # "Barra Pista" o "Terraza"
    
    # Tipo de entrega
    delivery_type = db.Column(db.String(20), nullable=False, default='receta', index=True)
    # Tipos: 'receta' (tiene receta), 'unidad' (sin receta, descuenta 1 unidad)
    
    # Detalle de insumos descontados (JSON)
    # Estructura: [{"insumo": "Ron", "cantidad": 60, "unidad": "ml", "ingredient_id": 1}, ...]
    ingredients_consumed = db.Column(JSON, nullable=True)
    
    # Referencia a Delivery (compatibilidad con sistema existente)
    delivery_id = db.Column(db.Integer, db.ForeignKey('deliveries.id'), nullable=True, index=True)
    
    # Timestamp
    delivered_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Índices compuestos
    __table_args__ = (
        Index('idx_delivery_items_sale_product', 'sale_id', 'product_name'),
        Index('idx_delivery_items_bartender_date', 'bartender_id', 'delivered_at'),
        Index('idx_delivery_items_location_date', 'location', 'delivered_at'),
    )
    
    def to_dict(self):
        """Convierte a diccionario"""
        return {
            'id': self.id,
            'sale_id': self.sale_id,
            'product_name': self.product_name,
            'product_id': self.product_id,
            'quantity_delivered': self.quantity_delivered,
            'bartender_id': self.bartender_id,
            'bartender_name': self.bartender_name,
            'location': self.location,
            'delivery_type': self.delivery_type,
            'ingredients_consumed': self.ingredients_consumed or [],
            'delivered_at': self.delivered_at.isoformat() if self.delivered_at else None
        }
    
    def __repr__(self):
        return f'<DeliveryItem {self.id}: {self.sale_id} - {self.product_name} x{self.quantity_delivered}>'






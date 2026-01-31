"""
Modelos de base de datos para el sistema de entregas
Migración de logs.csv a tabla SQL
"""
from datetime import datetime
from . import db
from sqlalchemy import Index


class Delivery(db.Model):
    """Modelo para entregas (deliveries)"""
    __tablename__ = 'deliveries'
    
    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.String(50), nullable=False, index=True)
    item_name = db.Column(db.String(200), nullable=False)
    qty = db.Column(db.Integer, nullable=False)
    bartender = db.Column(db.String(100), nullable=False, index=True)
    barra = db.Column(db.String(100), nullable=False, index=True)
    admin_user = db.Column(db.String(100), nullable=True, index=True)  # Usuario admin que registró desde admin/logs
    timestamp = db.Column(db.DateTime, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Índices compuestos para búsquedas frecuentes
    __table_args__ = (
        Index('idx_delivery_sale_item', 'sale_id', 'item_name'),
        Index('idx_delivery_bartender_date', 'bartender', 'timestamp'),
    )
    
    def to_dict(self):
        """Convierte a diccionario"""
        return {
            'id': self.id,
            'sale_id': self.sale_id,
            'item_name': self.item_name,
            'qty': self.qty,
            'bartender': self.bartender,
            'barra': self.barra,
            'admin_user': self.admin_user,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def to_csv_row(self):
        """Convierte a formato CSV (compatibilidad)"""
        return [
            self.sale_id,
            self.item_name,
            str(self.qty),
            self.bartender,
            self.barra,
            self.timestamp.strftime('%Y-%m-%d %H:%M:%S') if self.timestamp else ''
        ]
    
    @classmethod
    def from_csv_row(cls, row):
        """Crea desde fila CSV (para migración)"""
        if len(row) < 6:
            raise ValueError("Fila CSV incompleta")
        
        from datetime import datetime
        
        try:
            timestamp = datetime.strptime(row[5], '%Y-%m-%d %H:%M:%S')
        except (ValueError, IndexError):
            timestamp = datetime.utcnow()
        
        return cls(
            sale_id=row[0] if len(row) > 0 else '',
            item_name=row[1] if len(row) > 1 else '',
            qty=int(row[2]) if len(row) > 2 and row[2] else 0,
            bartender=row[3] if len(row) > 3 else '',
            barra=row[4] if len(row) > 4 else '',
            timestamp=timestamp
        )
    
    def __repr__(self):
        return f'<Delivery {self.id}: {self.sale_id} - {self.item_name} x{self.qty}>'


class FraudAttempt(db.Model):
    """Modelo para intentos de fraude"""
    __tablename__ = 'fraud_attempts'
    
    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.String(50), nullable=False, index=True)
    timestamp = db.Column(db.DateTime, nullable=False, index=True)
    bartender = db.Column(db.String(100), nullable=False)
    barra = db.Column(db.String(100), nullable=False)
    item_name = db.Column(db.String(200))
    qty = db.Column(db.Integer)
    fraud_type = db.Column(db.String(50), nullable=False, index=True)
    authorized = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    def to_dict(self):
        """Convierte a diccionario"""
        return {
            'id': self.id,
            'sale_id': self.sale_id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'bartender': self.bartender,
            'barra': self.barra,
            'item_name': self.item_name,
            'qty': self.qty,
            'fraud_type': self.fraud_type,
            'authorized': self.authorized,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def to_csv_row(self):
        """Convierte a formato CSV (compatibilidad)"""
        return [
            self.sale_id,
            self.timestamp.strftime('%Y-%m-%d %H:%M:%S') if self.timestamp else '',
            self.bartender,
            self.barra,
            self.item_name or '',
            str(self.qty) if self.qty else '0',
            self.fraud_type,
            '1' if self.authorized else '0'
        ]
    
    @classmethod
    def from_csv_row(cls, row):
        """Crea desde fila CSV (para migración)"""
        if len(row) < 8:
            raise ValueError("Fila CSV incompleta")
        
        from datetime import datetime
        
        try:
            timestamp = datetime.strptime(row[1], '%Y-%m-%d %H:%M:%S')
        except (ValueError, IndexError):
            timestamp = datetime.utcnow()
        
        return cls(
            sale_id=row[0] if len(row) > 0 else '',
            timestamp=timestamp,
            bartender=row[2] if len(row) > 2 else '',
            barra=row[3] if len(row) > 3 else '',
            item_name=row[4] if len(row) > 4 else None,
            qty=int(row[5]) if len(row) > 5 and row[5] else None,
            fraud_type=row[6] if len(row) > 6 else 'unknown',
            authorized=row[7] == '1' if len(row) > 7 else False
        )
    
    def __repr__(self):
        return f'<FraudAttempt {self.id}: {self.sale_id} - {self.fraud_type}>'


class TicketScan(db.Model):
    """Modelo para escaneos de tickets"""
    __tablename__ = 'ticket_scans'
    
    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.String(50), nullable=False, index=True)
    items = db.Column(db.Text, nullable=False)  # JSON string
    sale_info = db.Column(db.Text)  # JSON string
    scanned_at = db.Column(db.DateTime, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Índice compuesto para búsquedas por fecha
    __table_args__ = (
        Index('idx_ticket_scans_sale_date', 'sale_id', 'scanned_at'),
    )
    
    def to_dict(self):
        """Convierte a diccionario"""
        import json
        return {
            'id': self.id,
            'sale_id': self.sale_id,
            'items': json.loads(self.items) if self.items else [],
            'sale_info': json.loads(self.sale_info) if self.sale_info else {},
            'scanned_at': self.scanned_at.isoformat() if self.scanned_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<TicketScan {self.id}: {self.sale_id}>'
    
    @classmethod
    def get_scans_since(cls, since_datetime):
        """
        Obtiene todos los escaneos desde una fecha específica (optimizado con SQL)
        
        Args:
            since_datetime: datetime - Fecha desde la cual obtener escaneos
            
        Returns:
            Query object con los escaneos filtrados
        """
        return cls.query.filter(cls.scanned_at >= since_datetime).order_by(cls.scanned_at.desc())
    
    @classmethod
    def get_scans_between(cls, start_datetime, end_datetime):
        """
        Obtiene todos los escaneos entre dos fechas (optimizado con SQL)
        
        Args:
            start_datetime: datetime - Fecha de inicio
            end_datetime: datetime - Fecha de fin
            
        Returns:
            Query object con los escaneos filtrados
        """
        return cls.query.filter(
            cls.scanned_at >= start_datetime,
            cls.scanned_at <= end_datetime
        ).order_by(cls.scanned_at.desc())
    
    def get_sale_info_dict(self):
        """Obtiene sale_info como diccionario"""
        import json
        if self.sale_info:
            try:
                return json.loads(self.sale_info)
            except:
                return {}
        return {}
    
    def get_items_list(self):
        """Obtiene items como lista"""
        import json
        if self.items:
            try:
                return json.loads(self.items)
            except:
                return []
        return []











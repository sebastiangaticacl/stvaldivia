"""
Modelos de base de datos para turnos (shifts)
Migración de shift_status.json y shift_history.json a tabla SQL
"""
from datetime import datetime, date
from . import db
from sqlalchemy import Index


class Shift(db.Model):
    """Modelo para turnos"""
    __tablename__ = 'shifts'
    
    id = db.Column(db.Integer, primary_key=True)
    shift_date = db.Column(db.String(10), nullable=False, unique=True, index=True)  # YYYY-MM-DD como string
    is_open = db.Column(db.Boolean, default=False, nullable=False, index=True)
    opened_by = db.Column(db.String(100))
    opened_at = db.Column(db.String(50))  # ISO string
    closed_by = db.Column(db.String(100))
    closed_at = db.Column(db.String(50))  # ISO string
    fiesta_nombre = db.Column(db.String(200))
    djs = db.Column(db.String(200))
    barras_disponibles = db.Column(db.Text)  # JSON array
    bartenders = db.Column(db.Text)  # JSON array
    total_deliveries = db.Column(db.Integer, default=0, nullable=False)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def to_dict(self):
        """Convierte a diccionario"""
        import json
        return {
            'id': self.id,
            'shift_date': self.shift_date,
            'is_open': self.is_open,
            'opened_by': self.opened_by,
            'opened_at': self.opened_at,
            'closed_by': self.closed_by,
            'closed_at': self.closed_at,
            'fiesta_nombre': self.fiesta_nombre,
            'djs': self.djs,
            'barras_disponibles': json.loads(self.barras_disponibles) if self.barras_disponibles else [],
            'bartenders': json.loads(self.bartenders) if self.bartenders else [],
            'total_deliveries': self.total_deliveries,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        status = "OPEN" if self.is_open else "CLOSED"
        return f'<Shift {self.id}: {self.shift_date} - {status}>'


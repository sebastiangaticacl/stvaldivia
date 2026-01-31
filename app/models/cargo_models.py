"""
Modelo para gestión de cargos
"""
from datetime import datetime
from app.models import db
from sqlalchemy import Index
import pytz
from app.helpers.timezone_utils import CHILE_TZ


class Cargo(db.Model):
    """
    Modelo para gestionar los cargos disponibles en el sistema
    """
    __tablename__ = 'cargos'
    
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False, unique=True, index=True)
    descripcion = db.Column(db.String(500), nullable=True)
    activo = db.Column(db.Boolean, default=True, nullable=False, index=True)
    orden = db.Column(db.Integer, default=0, nullable=False)  # Para ordenar los cargos
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(CHILE_TZ).astimezone(pytz.UTC).replace(tzinfo=None), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(CHILE_TZ).astimezone(pytz.UTC).replace(tzinfo=None), onupdate=lambda: datetime.now(CHILE_TZ).astimezone(pytz.UTC).replace(tzinfo=None), nullable=False)
    
    # Índices
    __table_args__ = (
        Index('idx_cargos_activo_orden', 'activo', 'orden'),
    )
    
    def to_dict(self):
        """Convierte el modelo a diccionario"""
        return {
            'id': self.id,
            'nombre': self.nombre,
            'descripcion': self.descripcion or '',
            'activo': self.activo,
            'orden': self.orden,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }




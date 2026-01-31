"""
Modelos para configuración de sueldos por cargo
"""
from datetime import datetime
from . import db
from sqlalchemy import Numeric, Index, UniqueConstraint
import pytz
from app.helpers.timezone_utils import CHILE_TZ


class CargoSalaryConfig(db.Model):
    """
    Configuración de sueldo por turno para cada cargo
    """
    __tablename__ = 'cargo_salary_configs'
    
    id = db.Column(db.Integer, primary_key=True)
    cargo = db.Column(db.String(100), nullable=False, unique=True, index=True)
    
    # Sueldo base por turno (fijo)
    sueldo_por_turno = db.Column(Numeric(10, 2), nullable=False, default=0.0)
    
    # Bonos fijos
    bono_fijo = db.Column(Numeric(10, 2), default=0.0, nullable=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(CHILE_TZ).astimezone(pytz.UTC).replace(tzinfo=None), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(CHILE_TZ).astimezone(pytz.UTC).replace(tzinfo=None), onupdate=lambda: datetime.now(CHILE_TZ).astimezone(pytz.UTC).replace(tzinfo=None), nullable=False)
    
    # Índices
    __table_args__ = (
        UniqueConstraint('cargo', name='uq_cargo_salary_cargo'),
        Index('idx_cargo_salary_cargo', 'cargo'),
    )
    
    def to_dict(self):
        """Convierte el modelo a diccionario"""
        return {
            'id': self.id,
            'cargo': self.cargo,
            'sueldo_por_turno': float(self.sueldo_por_turno),
            'bono_fijo': float(self.bono_fijo),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }




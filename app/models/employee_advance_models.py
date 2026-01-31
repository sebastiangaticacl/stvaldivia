"""
Modelos para abonos y pagos excepcionales de empleados
"""
from datetime import datetime
from app.models import db
from sqlalchemy import Numeric, Index, Text
import pytz
from app.helpers.timezone_utils import CHILE_TZ


class EmployeeAdvance(db.Model):
    """
    Abono o pago excepcional para un empleado.
    Puede ser positivo (adelanto) o negativo (descuento).
    Se descuenta automáticamente de la asignación según turnos trabajados.
    """
    __tablename__ = 'employee_advances'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.String(50), nullable=False, index=True)
    employee_name = db.Column(db.String(400), nullable=False)
    
    # Tipo de abono
    tipo = db.Column(db.String(50), nullable=False)  # 'adelanto', 'descuento', 'abono', 'pago_excepcional'
    
    # Monto (positivo para adelantos, negativo para descuentos)
    monto = db.Column(Numeric(10, 2), nullable=False)
    
    # Descripción
    descripcion = db.Column(Text, nullable=True)
    
    # Fecha del abono
    fecha_abono = db.Column(db.String(50), nullable=False, index=True)  # YYYY-MM-DD
    
    # Estado
    aplicado = db.Column(db.Boolean, default=False, nullable=False, index=True)  # Si ya se aplicó al cálculo de sueldo
    fecha_aplicacion = db.Column(db.DateTime, nullable=True)  # Cuándo se aplicó
    
    # Información adicional
    creado_por = db.Column(db.String(200), nullable=True)
    notas = db.Column(Text, nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(CHILE_TZ).astimezone(pytz.UTC).replace(tzinfo=None), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(CHILE_TZ).astimezone(pytz.UTC).replace(tzinfo=None), onupdate=lambda: datetime.now(CHILE_TZ).astimezone(pytz.UTC).replace(tzinfo=None), nullable=False)
    
    # Índices
    __table_args__ = (
        Index('idx_employee_advances_employee_id', 'employee_id'),
        Index('idx_employee_advances_fecha', 'fecha_abono'),
        Index('idx_employee_advances_aplicado', 'aplicado'),
    )
    
    def to_dict(self):
        """Convierte el modelo a diccionario"""
        return {
            'id': self.id,
            'employee_id': self.employee_id,
            'employee_name': self.employee_name,
            'tipo': self.tipo,
            'monto': float(self.monto) if self.monto else 0.0,
            'descripcion': self.descripcion,
            'fecha_abono': self.fecha_abono,
            'aplicado': self.aplicado,
            'fecha_aplicacion': self.fecha_aplicacion.isoformat() if self.fecha_aplicacion else None,
            'creado_por': self.creado_por,
            'notas': self.notas,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }




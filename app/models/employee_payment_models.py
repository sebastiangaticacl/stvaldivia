"""
Modelo para registrar instancias de pagos realizados a empleados
Cada vez que se abona o se paga completo, se crea una instancia de pago
"""
from datetime import datetime
from . import db
from sqlalchemy import Numeric, Index
import pytz
from app.helpers.timezone_utils import CHILE_TZ


class EmployeePayment(db.Model):
    """
    Instancia de pago realizada a un empleado
    Registra cada pago (abono o pago completo) realizado
    """
    __tablename__ = 'employee_payments'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Relación con empleado
    employee_id = db.Column(db.String(50), nullable=False, index=True)
    employee_name = db.Column(db.String(400), nullable=False)
    
    # Información del pago
    tipo_pago = db.Column(db.String(50), nullable=False, index=True)  # 'abono' o 'pago_completo'
    monto = db.Column(Numeric(10, 2), nullable=False)
    monto_total_deuda = db.Column(Numeric(10, 2), nullable=True)  # Deuda total al momento del pago
    monto_pendiente_antes = db.Column(Numeric(10, 2), nullable=True)  # Pendiente antes del pago
    monto_pendiente_despues = db.Column(Numeric(10, 2), nullable=True)  # Pendiente después del pago
    
    # Turnos afectados
    turnos_pagados_ids = db.Column(db.Text, nullable=True)  # JSON con IDs de EmployeeShift marcados como pagados
    
    # Información adicional
    descripcion = db.Column(db.Text, nullable=True)
    notas = db.Column(db.Text, nullable=True)
    
    # Usuario que realizó el pago
    pagado_por = db.Column(db.String(200), nullable=False)
    
    # Fecha y hora
    fecha_pago = db.Column(db.DateTime, nullable=False, index=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(CHILE_TZ).astimezone(pytz.UTC).replace(tzinfo=None), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(CHILE_TZ).astimezone(pytz.UTC).replace(tzinfo=None), onupdate=lambda: datetime.now(CHILE_TZ).astimezone(pytz.UTC).replace(tzinfo=None), nullable=False)
    
    # Índices
    __table_args__ = (
        Index('idx_employee_payments_employee_fecha', 'employee_id', 'fecha_pago'),
        Index('idx_employee_payments_tipo', 'tipo_pago'),
    )
    
    def to_dict(self):
        """Convierte el modelo a diccionario"""
        import json
        return {
            'id': self.id,
            'employee_id': self.employee_id,
            'employee_name': self.employee_name,
            'tipo_pago': self.tipo_pago,
            'monto': float(self.monto),
            'monto_total_deuda': float(self.monto_total_deuda) if self.monto_total_deuda else None,
            'monto_pendiente_antes': float(self.monto_pendiente_antes) if self.monto_pendiente_antes else None,
            'monto_pendiente_despues': float(self.monto_pendiente_despues) if self.monto_pendiente_despues else None,
            'turnos_pagados_ids': json.loads(self.turnos_pagados_ids) if self.turnos_pagados_ids else [],
            'descripcion': self.descripcion,
            'notas': self.notas,
            'pagado_por': self.pagado_por,
            'fecha_pago': self.fecha_pago.isoformat() if self.fecha_pago else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

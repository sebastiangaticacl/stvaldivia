"""
Modelos para registro de turnos de empleados y cálculo de sueldos
"""
from datetime import datetime
from . import db
from sqlalchemy import Numeric, Index
import pytz
from app.helpers.timezone_utils import CHILE_TZ


class EmployeeShift(db.Model):
    """
    Registro de turnos trabajados por cada empleado
    Se usa para calcular sueldos
    """
    __tablename__ = 'employee_shifts'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Relación con empleado
    employee_id = db.Column(db.String(50), nullable=False, index=True)
    employee_name = db.Column(db.String(400), nullable=False)
    
    # Relación con jornada (opcional, puede ser null si es un turno independiente)
    jornada_id = db.Column(db.Integer, db.ForeignKey('jornadas.id'), nullable=True, index=True)
    
    # Información del turno
    fecha_turno = db.Column(db.String(50), nullable=False, index=True)  # YYYY-MM-DD
    tipo_turno = db.Column(db.String(50), nullable=True)  # "Noche", "Día", "Especial"
    cargo = db.Column(db.String(100), nullable=True)  # Cargo del empleado en este turno
    
    # Horarios
    hora_inicio = db.Column(db.DateTime, nullable=False, index=True)
    hora_fin = db.Column(db.DateTime, nullable=True)
    
    # Cálculo de sueldo
    horas_trabajadas = db.Column(Numeric(10, 2), nullable=True)  # Horas trabajadas (información)
    sueldo_por_turno = db.Column(Numeric(10, 2), nullable=True)  # Sueldo por turno configurado (fijo)
    sueldo_turno = db.Column(Numeric(10, 2), nullable=True)  # Sueldo total para este turno (sueldo_por_turno + bonos - descuentos)
    bonos = db.Column(Numeric(10, 2), default=0.0, nullable=False)  # Bonos adicionales
    descuentos = db.Column(Numeric(10, 2), default=0.0, nullable=False)  # Descuentos
    
    # Estado
    estado = db.Column(db.String(50), default='pendiente', nullable=False)  # pendiente, completo, incompleto, no_llego, cancelado, cerrado
    pagado = db.Column(db.Boolean, default=False, nullable=False, index=True)
    fecha_pago = db.Column(db.DateTime, nullable=True)
    
    # Notas
    notas = db.Column(db.Text, nullable=True)
    
    # Campos para manejo de pagos especiales
    tiene_adelanto = db.Column(db.Boolean, default=False, nullable=False)  # Si tuvo adelanto
    tiene_pago_extra = db.Column(db.Boolean, default=False, nullable=False)  # Si tuvo pago extra programático
    monto_adelanto = db.Column(Numeric(10, 2), default=0.0, nullable=False)  # Monto del adelanto
    monto_pago_extra = db.Column(Numeric(10, 2), default=0.0, nullable=False)  # Monto del pago extra
    horas_completadas = db.Column(Numeric(10, 2), nullable=True)  # Horas realmente trabajadas (puede ser menor que programadas)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(CHILE_TZ).astimezone(pytz.UTC).replace(tzinfo=None), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(CHILE_TZ).astimezone(pytz.UTC).replace(tzinfo=None), onupdate=lambda: datetime.now(CHILE_TZ).astimezone(pytz.UTC).replace(tzinfo=None), nullable=False)
    
    # Índices
    __table_args__ = (
        Index('idx_employee_shifts_employee_fecha', 'employee_id', 'fecha_turno'),
        Index('idx_employee_shifts_estado', 'estado'),
        Index('idx_employee_shifts_pagado', 'pagado'),
    )
    
    def calcular_horas_trabajadas(self):
        """Calcula las horas trabajadas basándose en hora_inicio y hora_fin"""
        if not self.hora_fin:
            return None
        
        # Convertir a timezone-aware si es necesario
        inicio = self.hora_inicio
        fin = self.hora_fin
        
        if inicio.tzinfo is None:
            inicio = pytz.UTC.localize(inicio)
        if fin.tzinfo is None:
            fin = pytz.UTC.localize(fin)
        
        # Convertir a Chile
        inicio_chile = inicio.astimezone(CHILE_TZ)
        fin_chile = fin.astimezone(CHILE_TZ)
        
        # Calcular diferencia
        diferencia = fin_chile - inicio_chile
        horas = diferencia.total_seconds() / 3600.0
        
        return round(horas, 2)
    
    def calcular_sueldo_turno(self):
        """
        Calcula el sueldo del turno basándose en sueldo por turno (fijo) + bonos - descuentos
        
        IMPORTANTE: Este método solo calcula el valor, NO lo guarda automáticamente.
        Si el turno ya está pagado, usa siempre el sueldo_turno guardado (no recalcular).
        El sueldo_turno se congela cuando se marca como pagado y no debe cambiar.
        """
        # Si ya está pagado, devolver el valor guardado (no recalcular)
        if self.pagado and self.sueldo_turno:
            return float(self.sueldo_turno)
        
        # Si no está pagado, calcular usando valores actuales
        sueldo_base = float(self.sueldo_por_turno) if self.sueldo_por_turno else 0.0
        sueldo_total = sueldo_base + float(self.bonos) - float(self.descuentos)
        
        return round(sueldo_total, 2)
    
    def proteger_sueldo_pagado(self):
        """
        Protege el sueldo_turno de modificaciones si el turno ya está pagado.
        Retorna True si el sueldo está protegido (turno pagado).
        """
        if self.pagado and self.sueldo_turno:
            return True
        return False
    
    def to_dict(self):
        """Convierte el modelo a diccionario"""
        return {
            'id': self.id,
            'employee_id': self.employee_id,
            'employee_name': self.employee_name,
            'jornada_id': self.jornada_id,
            'fecha_turno': self.fecha_turno,
            'tipo_turno': self.tipo_turno,
            'cargo': self.cargo,
            'hora_inicio': self.hora_inicio.isoformat() if self.hora_inicio else None,
            'hora_fin': self.hora_fin.isoformat() if self.hora_fin else None,
            'horas_trabajadas': float(self.horas_trabajadas) if self.horas_trabajadas else None,
            'sueldo_por_turno': float(self.sueldo_por_turno) if self.sueldo_por_turno else None,
            'sueldo_turno': float(self.sueldo_turno) if self.sueldo_turno else None,
            'bonos': float(self.bonos),
            'descuentos': float(self.descuentos),
            'estado': self.estado,
            'pagado': self.pagado,
            'fecha_pago': self.fecha_pago.isoformat() if self.fecha_pago else None,
            'notas': self.notas,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class EmployeeSalaryConfig(db.Model):
    """
    Configuración de sueldo por turno para cada empleado
    """
    __tablename__ = 'employee_salary_configs'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.String(50), nullable=False, unique=True, index=True)
    
    # Sueldo base por turno (fijo)
    sueldo_por_turno = db.Column(Numeric(10, 2), nullable=False, default=0.0)
    
    # Bonos fijos
    bono_fijo = db.Column(Numeric(10, 2), default=0.0, nullable=False)
    
    # Configuración adicional (JSON)
    config_adicional = db.Column(db.Text, nullable=True)  # JSON con configuraciones especiales
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(CHILE_TZ).astimezone(pytz.UTC).replace(tzinfo=None), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(CHILE_TZ).astimezone(pytz.UTC).replace(tzinfo=None), onupdate=lambda: datetime.now(CHILE_TZ).astimezone(pytz.UTC).replace(tzinfo=None), nullable=False)
    
    def to_dict(self):
        """Convierte el modelo a diccionario"""
        return {
            'id': self.id,
            'employee_id': self.employee_id,
            'sueldo_por_turno': float(self.sueldo_por_turno),
            'bono_fijo': float(self.bono_fijo),
            'config_adicional': self.config_adicional,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class FichaReviewLog(db.Model):
    """
    Log de revisiones de fichas personales
    Registra quién y cuándo revisó cada ficha
    """
    __tablename__ = 'ficha_review_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Relación con empleado
    employee_id = db.Column(db.String(50), nullable=False, index=True)
    employee_name = db.Column(db.String(400), nullable=False)
    
    # Información del revisor
    reviewer_name = db.Column(db.String(200), nullable=True)  # Nombre del admin que revisó
    reviewer_session_id = db.Column(db.String(200), nullable=True)  # ID de sesión para tracking
    
    # Información adicional
    ip_address = db.Column(db.String(50), nullable=True)
    user_agent = db.Column(db.String(500), nullable=True)
    
    # Timestamp
    reviewed_at = db.Column(db.DateTime, default=lambda: datetime.now(CHILE_TZ).astimezone(pytz.UTC).replace(tzinfo=None), nullable=False, index=True)
    
    # Índices
    __table_args__ = (
        Index('idx_ficha_review_employee', 'employee_id'),
        Index('idx_ficha_review_date', 'reviewed_at'),
    )
    
    def to_dict(self):
        """Convierte el modelo a diccionario"""
        return {
            'id': self.id,
            'employee_id': self.employee_id,
            'employee_name': self.employee_name,
            'reviewer_name': self.reviewer_name,
            'reviewer_session_id': self.reviewer_session_id,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'reviewed_at': self.reviewed_at.isoformat() if self.reviewed_at else None
        }

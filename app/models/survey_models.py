"""
Modelos de base de datos para encuestas
Migración de survey_responses.csv y survey_sessions.csv a tablas SQL
"""
from datetime import datetime, date, time
from . import db
from sqlalchemy import Index
from decimal import Decimal


class SurveyResponse(db.Model):
    """Modelo para respuestas de encuestas"""
    __tablename__ = 'survey_responses'
    
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False, index=True)
    barra = db.Column(db.String(100), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text)
    fiesta_nombre = db.Column(db.String(200))
    djs = db.Column(db.String(200))
    bartender_nombre = db.Column(db.String(100))
    fecha_sesion = db.Column(db.Date, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    def to_dict(self):
        """Convierte a diccionario"""
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'barra': self.barra,
            'rating': self.rating,
            'comment': self.comment,
            'fiesta_nombre': self.fiesta_nombre,
            'djs': self.djs,
            'bartender_nombre': self.bartender_nombre,
            'fecha_sesion': self.fecha_sesion.isoformat() if self.fecha_sesion else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def to_csv_row(self):
        """Convierte a formato CSV (compatibilidad)"""
        return [
            self.timestamp.strftime('%Y-%m-%d %H:%M:%S') if self.timestamp else '',
            self.barra,
            str(self.rating),
            self.comment or '',
            self.fiesta_nombre or '',
            self.djs or '',
            self.bartender_nombre or '',
            self.fecha_sesion.isoformat() if self.fecha_sesion else ''
        ]
    
    def __repr__(self):
        return f'<SurveyResponse {self.id}: Rating {self.rating}>'


class SurveySession(db.Model):
    """Modelo para sesiones de encuestas"""
    __tablename__ = 'survey_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    fecha_sesion = db.Column(db.Date, nullable=False, unique=True, index=True)
    fiesta_nombre = db.Column(db.String(200))
    djs = db.Column(db.String(200))
    bartenders = db.Column(db.Text)  # JSON array
    hora_inicio = db.Column(db.Time)
    hora_fin = db.Column(db.Time)
    total_respuestas = db.Column(db.Integer, default=0, nullable=False)
    promedio_rating = db.Column(db.Numeric(3, 2))
    estado = db.Column(db.String(50), default='open', nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def to_dict(self):
        """Convierte a diccionario"""
        import json
        return {
            'id': self.id,
            'fecha_sesion': self.fecha_sesion.isoformat() if self.fecha_sesion else None,
            'fiesta_nombre': self.fiesta_nombre,
            'djs': self.djs,
            'bartenders': json.loads(self.bartenders) if self.bartenders else [],
            'hora_inicio': self.hora_inicio.strftime('%H:%M:%S') if self.hora_inicio else None,
            'hora_fin': self.hora_fin.strftime('%H:%M:%S') if self.hora_fin else None,
            'total_respuestas': self.total_respuestas,
            'promedio_rating': float(self.promedio_rating) if self.promedio_rating else None,
            'estado': self.estado,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<SurveySession {self.id}: {self.fecha_sesion} - {self.estado}>'















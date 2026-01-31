"""
Modelos para el log de conexiones API
"""
from app.models import db
from datetime import datetime
import pytz
from app.helpers.timezone_utils import CHILE_TZ


class ApiConnectionLog(db.Model):
    """
    Log de conexiones a la API de PHP POS
    """
    __tablename__ = 'api_connection_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(CHILE_TZ).astimezone(pytz.UTC).replace(tzinfo=None))
    status = db.Column(db.String(20), nullable=False)  # 'online', 'offline', 'error'
    response_time_ms = db.Column(db.Float, nullable=True)
    message = db.Column(db.String(255), nullable=True)
    api_url = db.Column(db.String(500), nullable=True)
    checked_by = db.Column(db.String(100), nullable=True)  # 'system', 'admin', 'manual'
    
    def __repr__(self):
        return f'<ApiConnectionLog {self.id}: {self.status} at {self.timestamp}>'
    
    def to_dict(self):
        """Convierte el log a diccionario"""
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'status': self.status,
            'response_time_ms': self.response_time_ms,
            'message': self.message,
            'api_url': self.api_url,
            'checked_by': self.checked_by
        }
    
    @property
    def timestamp_chile(self):
        """Retorna el timestamp en hora de Chile"""
        if self.timestamp:
            # Si es naive, asumir UTC
            if self.timestamp.tzinfo is None:
                utc_dt = pytz.UTC.localize(self.timestamp)
            else:
                utc_dt = self.timestamp
            return utc_dt.astimezone(CHILE_TZ)
        return None




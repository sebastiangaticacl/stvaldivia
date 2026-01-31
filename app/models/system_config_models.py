"""
Modelos para configuración del sistema
"""
from datetime import datetime
from . import db


class SystemConfig(db.Model):
    """Configuración del sistema - guarda preferencias globales"""
    __tablename__ = 'system_config'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False, index=True)
    value = db.Column(db.Text, nullable=True)
    description = db.Column(db.String(500), nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    updated_by = db.Column(db.String(200), nullable=True)
    
    def __repr__(self):
        return f'<SystemConfig {self.key}={self.value}>'
    
    @staticmethod
    def get(key, default=None):
        """Obtiene un valor de configuración"""
        config = SystemConfig.query.filter_by(key=key).first()
        return config.value if config else default
    
    @staticmethod
    def set(key, value, description=None, updated_by=None):
        """Establece un valor de configuración"""
        config = SystemConfig.query.filter_by(key=key).first()
        if config:
            config.value = value
            config.updated_at = datetime.utcnow()
            if description:
                config.description = description
            if updated_by:
                config.updated_by = updated_by
        else:
            config = SystemConfig(
                key=key,
                value=value,
                description=description,
                updated_by=updated_by
            )
            db.session.add(config)
        db.session.commit()
        return config
    
    @staticmethod
    def delete(key):
        """Elimina una configuración"""
        config = SystemConfig.query.filter_by(key=key).first()
        if config:
            db.session.delete(config)
            db.session.commit()
            return True
        return False




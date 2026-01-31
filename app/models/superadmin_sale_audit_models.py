"""
Modelo de auditoría para ventas de caja SUPERADMIN
"""
from datetime import datetime
from app.models import db
from sqlalchemy import Index, Text


class SuperadminSaleAudit(db.Model):
    """Auditoría de ventas de caja SUPERADMIN"""
    __tablename__ = 'superadmin_sale_audit'
    
    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey('pos_sales.id'), nullable=False, index=True)
    register_id = db.Column(db.String(50), nullable=False, index=True)
    admin_user_id = db.Column(db.String(200), nullable=False, index=True)
    admin_user_name = db.Column(db.String(200), nullable=False)
    tipo_operacion = db.Column(db.String(50), nullable=False, index=True)  # 'CORTESIA' o 'PRUEBA_DEPLOY'
    motivo = db.Column(Text, nullable=False)
    total = db.Column(db.Numeric(10, 2), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relación con venta
    sale = db.relationship('PosSale', backref='superadmin_audit', lazy=True)
    
    # Índices
    __table_args__ = (
        Index('idx_superadmin_audit_tipo', 'tipo_operacion'),
        Index('idx_superadmin_audit_admin', 'admin_user_id'),
        Index('idx_superadmin_audit_created', 'created_at'),
    )
    
    def to_dict(self):
        """Convierte el modelo a diccionario"""
        return {
            'id': self.id,
            'sale_id': self.sale_id,
            'register_id': self.register_id,
            'admin_user_id': self.admin_user_id,
            'admin_user_name': self.admin_user_name,
            'tipo_operacion': self.tipo_operacion,
            'motivo': self.motivo,
            'total': float(self.total) if self.total else 0.0,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }












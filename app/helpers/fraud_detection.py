import os
import csv
from datetime import datetime, timedelta
from collections import defaultdict
from flask import current_app
from .logs import load_logs
from .fraud_config import load_fraud_config
from ..models import db
from ..models.delivery_models import FraudAttempt, Delivery


def save_fraud_attempt(sale_id, bartender, barra, item_name, qty, fraud_type, authorized=False):
    """Guarda un intento de fraude en la base de datos"""
    try:
        fraud_attempt = FraudAttempt(
            sale_id=str(sale_id)[:50] if sale_id else '',
            timestamp=datetime.now(),
            bartender=str(bartender)[:100] if bartender else '',
            barra=str(barra)[:100] if barra else '',
            item_name=str(item_name)[:200] if item_name else None,
            qty=int(qty) if qty else None,
            fraud_type=str(fraud_type)[:50] if fraud_type else 'unknown',
            authorized=bool(authorized)
        )
        
        db.session.add(fraud_attempt)
        db.session.commit()
        
        return True
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error al guardar intento de fraude en BD: {e}")
        return False


def load_fraud_attempts():
    """Carga todos los intentos de fraude desde la base de datos"""
    try:
        fraud_attempts = FraudAttempt.query.order_by(FraudAttempt.timestamp.desc()).all()
        return [fraud.to_csv_row() for fraud in fraud_attempts]
    except Exception as e:
        current_app.logger.error(f"Error al cargar intentos de fraude desde BD: {e}")
        return []


def count_delivery_attempts(sale_id):
    """Cuenta cuántas veces se ha intentado entregar un ticket (incluyendo entregas exitosas y autorizadas)"""
    # CORRECCIÓN: Validar que sale_id no sea None o vacío
    if not sale_id:
        current_app.logger.warning("count_delivery_attempts llamado con sale_id vacío")
        return 0
    
    try:
        count = Delivery.query.filter_by(sale_id=str(sale_id)).count()
        return count
    except Exception as e:
        current_app.logger.error(f"Error al contar entregas desde BD para sale_id={sale_id}: {e}", exc_info=True)
        return 0


def is_ticket_old(sale_time_str, max_hours=None):
    """
    Verifica si un ticket es antiguo (más de max_hours horas)
    
    Args:
        sale_time_str: String de fecha en formato que devuelve la API
        max_hours: Número máximo de horas permitidas (None = usar config)
    
    Returns:
        tuple: (is_old: bool, days_old: float)
    """
    if max_hours is None:
        config = load_fraud_config()
        max_hours = config.get('max_hours_old_ticket', 24)
    
    if not sale_time_str or sale_time_str == "Fecha no disponible":
        return False, 0
    
    try:
        # Intentar parsear diferentes formatos de fecha
        # La API puede devolver: "2024-01-15 14:30:00" o similar
        date_formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d %H:%M:%S.%f',
            '%Y-%m-%d',
            '%d/%m/%Y %H:%M:%S',
            '%d/%m/%Y',
        ]
        
        sale_time = None
        for fmt in date_formats:
            try:
                sale_time = datetime.strptime(sale_time_str.strip(), fmt)
                break
            except ValueError:
                continue
        
        if not sale_time:
            current_app.logger.warning(f"No se pudo parsear la fecha: {sale_time_str}")
            return False, 0
        
        now = datetime.now()
        time_diff = now - sale_time
        hours_diff = time_diff.total_seconds() / 3600
        days_diff = hours_diff / 24
        
        is_old = hours_diff > max_hours
        
        return is_old, days_diff
    except Exception as e:
        current_app.logger.error(f"Error al verificar antigüedad del ticket: {e}")
        return False, 0


def detect_fraud(sale_id, sale_time_str=None):
    """
    Detecta fraudes en un ticket
    
    Returns:
        dict con keys:
            - is_fraud: bool
            - fraud_type: str | None ('old_ticket', 'multiple_attempts', None)
            - message: str
            - details: dict
    """
    fraud_info = {
        'is_fraud': False,
        'fraud_type': None,
        'message': '',
        'details': {}
    }
    
    # Obtener configuración
    config = load_fraud_config()
    max_attempts = config.get('max_delivery_attempts', 3)
    max_hours = config.get('max_hours_old_ticket', 24)
    
    # Verificar múltiples intentos
    attempts = count_delivery_attempts(sale_id)
    if attempts > max_attempts:
        fraud_info['is_fraud'] = True
        fraud_info['fraud_type'] = 'multiple_attempts'
        fraud_info['message'] = f'FRAUDE DETECTADO: Este ticket ha sido intentado entregar {attempts} veces (máximo permitido: {max_attempts})'
        fraud_info['details'] = {
            'attempts': attempts,
            'max_attempts': max_attempts
        }
        return fraud_info
    
    # Verificar si el ticket es antiguo (si se proporciona sale_time_str)
    if sale_time_str:
        is_old, days_old = is_ticket_old(sale_time_str, max_hours=max_hours)
        if is_old:
            fraud_info['is_fraud'] = True
            fraud_info['fraud_type'] = 'old_ticket'
            fraud_info['message'] = f'FRAUDE DETECTADO: Este ticket es antiguo ({days_old:.1f} días). Requiere autorización del administrador.'
            fraud_info['details'] = {
                'days_old': round(days_old, 1),
                'sale_time': sale_time_str
            }
            return fraud_info
    
    return fraud_info


def authorize_fraud(sale_id, fraud_type):
    """Marca un intento de fraude como autorizado en la base de datos"""
    try:
        # Buscar el último intento no autorizado de este ticket y tipo
        fraud_attempt = FraudAttempt.query.filter_by(
            sale_id=str(sale_id),
            fraud_type=str(fraud_type),
            authorized=False
        ).order_by(FraudAttempt.timestamp.desc()).first()
        
        if fraud_attempt:
            fraud_attempt.authorized = True
            db.session.commit()
            return True
        
        return False
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error al autorizar fraude en BD: {e}")
        return False

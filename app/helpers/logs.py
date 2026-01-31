import os
import csv
from datetime import datetime
from flask import current_app
from .. import socketio
from ..models import db
from ..models.delivery_models import Delivery

EXPECTED_LOG_HEADER = ['sale_id', 'item_name', 'qty', 'bartender', 'barra', 'timestamp']


def load_logs():
    """Carga logs desde la base de datos"""
    try:
        deliveries = Delivery.query.order_by(Delivery.timestamp.desc()).all()
        return [delivery.to_csv_row() for delivery in deliveries]
    except Exception as e:
        current_app.logger.error(f"Error al cargar logs desde BD: {e}")
        return []


def save_log(sale_id, item_name, qty, bartender, barra):
    """Guarda un log en la base de datos"""
    # Sanitizar y validar datos
    sale_id = str(sale_id)[:50] if sale_id else ''
    item_name = str(item_name)[:200] if item_name else ''
    try:
        qty_int = int(qty) if qty else 0
    except (ValueError, TypeError):
        qty_int = 0
    bartender = str(bartender)[:100] if bartender else ''
    barra = str(barra)[:100] if barra else ''

    timestamp = datetime.now()

    try:
        # Guardar en base de datos
        delivery = Delivery(
            sale_id=sale_id,
            item_name=item_name,
            qty=qty_int,
            bartender=bartender,
            barra=barra,
            timestamp=timestamp
        )
        
        db.session.add(delivery)
        db.session.commit()
        
        # Enviar evento a n8n (después de commit exitoso)
        try:
            from app.helpers.n8n_client import send_delivery_created
            send_delivery_created(
                delivery_id=delivery.id,
                item_name=item_name,
                quantity=qty_int,
                bartender=bartender,
                barra=barra
            )
        except Exception as e:
            current_app.logger.warning(f"Error enviando evento a n8n: {e}")
        
        # Preparar entrada para emitir (formato CSV para compatibilidad)
        entry = [sale_id, item_name, str(qty_int), bartender, barra, timestamp.strftime('%Y-%m-%d %H:%M:%S')]
        
        # Avisar a clientes admin conectados
        socketio.emit('new_log', {'log_entry': entry}, namespace='/admin_logs')
        
        # Calcular estadísticas rápidas y emitir para dashboard en tiempo real
        now = datetime.now()
        current_hour = now.hour
        
        socketio.emit('stats_update', {
            'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'hour': current_hour,
            'type': 'new_delivery',
            'bartender': bartender,
            'barra': barra,
            'item': item_name,
            'qty': str(qty_int)
        }, namespace='/admin_stats')
        
        return True
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error al guardar log en BD: {e}")
        raise


def delete_log_entry(entry_list):
    """Elimina una entrada de log desde la base de datos"""
    try:
        if len(entry_list) < 6:
            return False
        
        sale_id = entry_list[0] if len(entry_list) > 0 else ''
        item_name = entry_list[1] if len(entry_list) > 1 else ''
        timestamp_str = entry_list[5] if len(entry_list) > 5 else ''
        
        # Buscar la entrega por sale_id, item_name y timestamp
        try:
            timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
        except (ValueError, IndexError):
            current_app.logger.warning(f"No se pudo parsear timestamp: {timestamp_str}")
            return False
        
        delivery = Delivery.query.filter_by(
            sale_id=sale_id,
            item_name=item_name,
            timestamp=timestamp
        ).first()
        
        if delivery:
            db.session.delete(delivery)
            db.session.commit()
            
            # Notificar a clientes admin conectados sobre la eliminación
            socketio.emit('log_deleted', {'log_entry': entry_list}, namespace='/admin_logs')
            return True
        
        return False
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error al eliminar entrada de log: {e}")
        return False


def clear_all_logs():
    """Elimina todos los logs de la base de datos"""
    try:
        deleted_count = Delivery.query.delete()
        db.session.commit()
        
        # Notificar a clientes admin conectados que se borró todo
        socketio.emit('all_logs_cleared', {}, namespace='/admin_logs')
        
        current_app.logger.info(f"Se eliminaron {deleted_count} logs de la base de datos")
        return True
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error al borrar todos los logs: {e}")
        return False
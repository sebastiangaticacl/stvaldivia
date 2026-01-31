"""
Helper para guardar y consultar información de tickets escaneados
MIGRADO A BASE DE DATOS - Usa modelo TicketScan en lugar de JSON
"""
import os
import json
from flask import current_app
from datetime import datetime
from app.models import db
from app.models.delivery_models import TicketScan


def get_ticket_scans_file():
    """
    Obtiene la ruta del archivo de tickets escaneados (LEGACY - solo para migración)
    """
    from app.helpers.production_check import is_production, get_safe_instance_path, ensure_not_production
    ensure_not_production("El sistema de escaneos de tickets desde archivo")
    instance_path = get_safe_instance_path()
    if not instance_path:
        raise RuntimeError("No se puede acceder a instance_path en producción")
    return os.path.join(instance_path, 'ticket_scans.json')


def save_ticket_scan(sale_id, items, venta_info=None):
    """
    Guarda la información completa de un ticket escaneado en la base de datos
    
    Args:
        sale_id: ID del ticket
        items: Lista de productos del ticket [{'name': str, 'quantity': int}, ...]
        venta_info: Diccionario con información completa de la venta (opcional)
                   Debe contener: fecha_venta, vendedor, comprador, caja, sale_data
    """
    try:
        # Verificar si ya existe el ticket escaneado
        existing_scan = TicketScan.query.filter_by(sale_id=str(sale_id)).first()
        if existing_scan:
            current_app.logger.debug(f"Ticket {sale_id} ya existe en la base de datos, no se sobrescribe")
            return True
        
        # Preparar información completa del ticket
        ticket_data = {
            'sale_id': sale_id,
            'items': items,
            'scanned_at': datetime.now().isoformat(),
            'total_items': len(items)
        }
        
        # Agregar información adicional si está disponible
        if venta_info:
            ticket_data.update({
                'fecha_venta': venta_info.get('fecha_venta', ''),
                'vendedor': venta_info.get('vendedor', 'Desconocido'),
                'comprador': venta_info.get('comprador', 'N/A'),
                'caja': venta_info.get('caja', 'Caja desconocida'),
                'sale_data': venta_info.get('sale_data', {}),  # Guardar sale_data completo
                'employee_id': venta_info.get('sale_data', {}).get('employee_id'),
                'register_id': venta_info.get('sale_data', {}).get('register_id'),
                'customer_id': venta_info.get('sale_data', {}).get('customer_id')
            })
        
        # Crear registro en base de datos
        ticket_scan = TicketScan(
            sale_id=str(sale_id),
            items=json.dumps(items),
            sale_info=json.dumps(ticket_data),
            scanned_at=datetime.now()
        )
        
        db.session.add(ticket_scan)
        db.session.commit()
        
        current_app.logger.debug(f"Ticket {sale_id} guardado en base de datos")
        return True
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error al guardar ticket scan en BD: {e}", exc_info=True)
        return False


def get_ticket_scan(sale_id):
    """
    Obtiene la información de un ticket escaneado desde la base de datos
    
    Args:
        sale_id: ID del ticket
        
    Returns:
        dict con información del ticket o None si no existe
    """
    try:
        ticket_scan = TicketScan.query.filter_by(sale_id=str(sale_id)).first()
        if ticket_scan:
            # Convertir a formato compatible con el código existente
            sale_info = json.loads(ticket_scan.sale_info) if ticket_scan.sale_info else {}
            return sale_info
        return None
    except Exception as e:
        current_app.logger.error(f"Error al obtener ticket scan desde BD: {e}")
        return None


def get_all_ticket_scans():
    """
    Obtiene todos los tickets escaneados desde la base de datos
    
    Returns:
        dict con todos los tickets escaneados {sale_id: ticket_data}
    """
    try:
        ticket_scans = TicketScan.query.order_by(TicketScan.scanned_at.desc()).all()
        result = {}
        
        for scan in ticket_scans:
            try:
                sale_info = json.loads(scan.sale_info) if scan.sale_info else {}
                result[scan.sale_id] = sale_info
            except:
                # Si hay error parseando, crear estructura básica
                result[scan.sale_id] = {
                    'sale_id': scan.sale_id,
                    'items': json.loads(scan.items) if scan.items else [],
                    'scanned_at': scan.scanned_at.isoformat() if scan.scanned_at else None
                }
        
        return result
    except Exception as e:
        current_app.logger.error(f"Error al obtener todos los ticket scans desde BD: {e}")
        return {}


def get_ticket_scans_since(since_datetime):
    """
    Obtiene tickets escaneados desde una fecha específica (optimizado con SQL)
    
    Args:
        since_datetime: datetime - Fecha desde la cual obtener escaneos
        
    Returns:
        dict con tickets escaneados {sale_id: ticket_data}
    """
    import time
    start_time = time.time()
    
    try:
        ticket_scans = TicketScan.get_scans_since(since_datetime).all()
        query_time = time.time() - start_time
        
        # Log si la consulta es lenta (>500ms)
        if query_time > 0.5:
            current_app.logger.warning(
                f"Consulta lenta en get_ticket_scans_since: {query_time:.3f}s "
                f"(desde {since_datetime}) - {len(ticket_scans)} registros"
            )
        else:
            current_app.logger.debug(
                f"Consulta get_ticket_scans_since: {query_time:.3f}s - {len(ticket_scans)} registros"
            )
        
        result = {}
        parse_start = time.time()
        
        for scan in ticket_scans:
            try:
                sale_info = scan.get_sale_info_dict()
                result[scan.sale_id] = sale_info
            except Exception as e:
                current_app.logger.warning(f"Error al parsear sale_info para {scan.sale_id}: {e}")
                result[scan.sale_id] = {
                    'sale_id': scan.sale_id,
                    'items': scan.get_items_list(),
                    'scanned_at': scan.scanned_at.isoformat() if scan.scanned_at else None
                }
        
        total_time = time.time() - start_time
        if total_time > 1.0:
            current_app.logger.warning(
                f"Operación lenta get_ticket_scans_since: {total_time:.3f}s total "
                f"(query: {query_time:.3f}s, parse: {time.time() - parse_start:.3f}s)"
            )
        
        return result
    except Exception as e:
        elapsed = time.time() - start_time
        current_app.logger.error(
            f"Error al obtener ticket scans desde fecha después de {elapsed:.3f}s: {e}",
            exc_info=True
        )
        return {}


def get_ticket_scans_between(start_datetime, end_datetime):
    """
    Obtiene tickets escaneados entre dos fechas (optimizado con SQL)
    
    Args:
        start_datetime: datetime - Fecha de inicio
        end_datetime: datetime - Fecha de fin
        
    Returns:
        dict con tickets escaneados {sale_id: ticket_data}
    """
    import time
    start_time = time.time()
    
    try:
        ticket_scans = TicketScan.get_scans_between(start_datetime, end_datetime).all()
        query_time = time.time() - start_time
        
        # Log si la consulta es lenta (>500ms)
        if query_time > 0.5:
            current_app.logger.warning(
                f"Consulta lenta en get_ticket_scans_between: {query_time:.3f}s "
                f"({start_datetime} a {end_datetime}) - {len(ticket_scans)} registros"
            )
        else:
            current_app.logger.debug(
                f"Consulta get_ticket_scans_between: {query_time:.3f}s - {len(ticket_scans)} registros"
            )
        
        result = {}
        parse_start = time.time()
        
        for scan in ticket_scans:
            try:
                sale_info = scan.get_sale_info_dict()
                result[scan.sale_id] = sale_info
            except Exception as e:
                current_app.logger.warning(f"Error al parsear sale_info para {scan.sale_id}: {e}")
                result[scan.sale_id] = {
                    'sale_id': scan.sale_id,
                    'items': scan.get_items_list(),
                    'scanned_at': scan.scanned_at.isoformat() if scan.scanned_at else None
                }
        
        total_time = time.time() - start_time
        if total_time > 1.0:
            current_app.logger.warning(
                f"Operación lenta get_ticket_scans_between: {total_time:.3f}s total "
                f"(query: {query_time:.3f}s, parse: {time.time() - parse_start:.3f}s)"
            )
        
        return result
    except Exception as e:
        elapsed = time.time() - start_time
        current_app.logger.error(
            f"Error al obtener ticket scans entre fechas después de {elapsed:.3f}s: {e}",
            exc_info=True
        )
        return {}


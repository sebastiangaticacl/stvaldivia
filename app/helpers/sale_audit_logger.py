"""
Sistema de auditoría para ventas del POS
Registra todos los cambios y acciones críticas
"""
from typing import Dict, Any, Optional
from datetime import datetime
import logging
import json
from flask import current_app, session, request, request

logger = logging.getLogger(__name__)


class SaleAuditLogger:
    """Registra eventos de auditoría para ventas"""
    
    @staticmethod
    def log_sale_created(
        sale_id: int,
        sale_data: Dict[str, Any],
        employee_id: str,
        employee_name: str,
        register_id: str
    ) -> None:
        """Registra la creación de una venta"""
        try:
            audit_entry = {
                'event_type': 'sale_created',
                'sale_id': sale_id,
                'timestamp': datetime.utcnow().isoformat(),
                'employee_id': str(employee_id),
                'employee_name': employee_name,
                'register_id': str(register_id),
                'total_amount': float(sale_data.get('total_amount', 0)),
                'payment_type': sale_data.get('payment_type'),
                'items_count': len(sale_data.get('items', [])),
                'items': [
                    {
                        'product_id': item.get('product_id'),
                        'product_name': item.get('product_name'),
                        'quantity': item.get('quantity'),
                        'unit_price': float(item.get('unit_price', 0)),
                        'subtotal': float(item.get('subtotal', 0))
                    }
                    for item in sale_data.get('items', [])
                ],
                'ip_address': request.remote_addr if request else None,
                'session_id': session.get('session_id'),
            }
            
            logger.info(
                f"🔍 AUDITORÍA - Venta creada: ID={sale_id}, "
                f"Cajero={employee_name}, Caja={register_id}, "
                f"Total=${sale_data.get('total_amount', 0)}, "
                f"Items={len(sale_data.get('items', []))}"
            )
            
            # En producción, guardar en BD o archivo de auditoría
            # Por ahora, solo loggear
            
        except Exception as e:
            logger.error(f"Error al registrar auditoría de venta creada: {e}", exc_info=True)
    
    @staticmethod
    def log_sale_modified(
        sale_id: int,
        original_data: Dict[str, Any],
        new_data: Dict[str, Any],
        modified_by: str,
        reason: Optional[str] = None
    ) -> None:
        """Registra la modificación de una venta"""
        try:
            audit_entry = {
                'event_type': 'sale_modified',
                'sale_id': sale_id,
                'timestamp': datetime.utcnow().isoformat(),
                'modified_by': modified_by,
                'original_data': original_data,
                'new_data': new_data,
                'changes': _calculate_changes(original_data, new_data),
                'reason': reason
            }
            
            logger.warning(
                f"⚠️ AUDITORÍA - Venta modificada: ID={sale_id}, "
                f"Modificado por={modified_by}, Razón={reason or 'No especificada'}"
            )
            
        except Exception as e:
            logger.error(f"Error al registrar auditoría de venta modificada: {e}", exc_info=True)
    
    @staticmethod
    def log_register_lock(
        register_id: str,
        employee_id: str,
        employee_name: str,
        action: str,  # 'locked', 'unlocked', 'force_locked', 'force_unlocked'
        previous_lock: Optional[Dict[str, Any]] = None
    ) -> None:
        """Registra bloqueo/desbloqueo de caja"""
        try:
            audit_entry = {
                'event_type': f'register_{action}',
                'register_id': str(register_id),
                'timestamp': datetime.utcnow().isoformat(),
                'employee_id': str(employee_id),
                'employee_name': employee_name,
                'previous_lock': previous_lock
            }
            
            logger.info(
                f"🔍 AUDITORÍA - Caja {action}: ID={register_id}, "
                f"Cajero={employee_name}"
            )
            
        except Exception as e:
            logger.error(f"Error al registrar auditoría de bloqueo: {e}", exc_info=True)
    
    @staticmethod
    def log_security_event(
        event_type: str,
        employee_id: Optional[str],
        employee_name: Optional[str],
        register_id: Optional[str],
        details: Dict[str, Any],
        severity: str = 'warning'  # 'info', 'warning', 'error', 'critical'
    ) -> None:
        """Registra un evento de seguridad"""
        try:
            audit_entry = {
                'event_type': 'security_event',
                'security_event_type': event_type,
                'timestamp': datetime.utcnow().isoformat(),
                'employee_id': str(employee_id) if employee_id else None,
                'employee_name': employee_name,
                'register_id': str(register_id) if register_id else None,
                'severity': severity,
                'details': details,
                'ip_address': request.remote_addr if request else None,
            }
            
            log_message = (
                f"🚨 AUDITORÍA SEGURIDAD [{severity.upper()}] - {event_type}: "
                f"Cajero={employee_name or 'Desconocido'}, "
                f"Caja={register_id or 'N/A'}, "
                f"Detalles={json.dumps(details)}"
            )
            
            if severity == 'critical':
                logger.critical(log_message)
            elif severity == 'error':
                logger.error(log_message)
            elif severity == 'warning':
                logger.warning(log_message)
            else:
                logger.info(log_message)
            
        except Exception as e:
            logger.error(f"Error al registrar evento de seguridad: {e}", exc_info=True)


def _calculate_changes(original: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
    """Calcula los cambios entre dos diccionarios"""
    changes = {}
    
    for key in set(list(original.keys()) + list(new.keys())):
        orig_val = original.get(key)
        new_val = new.get(key)
        
        if orig_val != new_val:
            changes[key] = {
                'from': orig_val,
                'to': new_val
            }
    
    return changes


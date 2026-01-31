"""
Sistema de auditoría completa para transacciones financieras
"""
from datetime import datetime
from flask import current_app, request, session
from app.models import db
from app.models.audit_log_models import AuditLog
from app.helpers.timezone_utils import CHILE_TZ
import json
import pytz


def log_financial_transaction(
    action: str,
    entity_type: str,
    entity_id: str,
    old_value: dict,
    new_value: dict,
    amount: float = None,
    success: bool = True,
    error_message: str = None
):
    """
    Registra una transacción financiera en el log de auditoría
    
    Args:
        action: Tipo de acción ('payment', 'salary_change', 'register_close', etc.)
        entity_type: Tipo de entidad ('EmployeePayment', 'EmployeeShift', etc.)
        entity_id: ID de la entidad
        old_value: Valor anterior (dict)
        new_value: Valor nuevo (dict)
        amount: Monto de la transacción (opcional)
        success: Si la operación fue exitosa
        error_message: Mensaje de error si success=False
    """
    try:
        audit_log = AuditLog(
            user_id=session.get('admin_username', 'unknown'),
            username=session.get('admin_username', 'unknown'),
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id),
            old_value=json.dumps(old_value, default=str),
            new_value=json.dumps(new_value, default=str),
            ip_address=request.remote_addr if request else None,
            user_agent=request.headers.get('User-Agent', '') if request else '',
            request_method=request.method if request else None,
            request_path=request.path if request else None,
            success=success,
            error_message=error_message
        )
        db.session.add(audit_log)
        db.session.commit()
        
        if amount:
            current_app.logger.info(
                f"💰 {action.upper()}: ${amount:.2f} - {entity_type} {entity_id} "
                f"por {session.get('admin_username', 'unknown')}"
            )
    except Exception as e:
        current_app.logger.error(f"Error al registrar transacción financiera: {e}", exc_info=True)
        db.session.rollback()


def validate_register_close_integrity(close):
    """
    Valida la integridad de un cierre de caja
    
    Args:
        close: RegisterClose object
        
    Returns:
        tuple: (is_valid, error_message)
    """
    from app.helpers.financial_utils import to_decimal
    
    try:
        # Calcular totales esperados y actuales
        expected_total = to_decimal(close.expected_cash or 0) + \
                        to_decimal(close.expected_debit or 0) + \
                        to_decimal(close.expected_credit or 0)
        
        actual_total = to_decimal(close.actual_cash or 0) + \
                      to_decimal(close.actual_debit or 0) + \
                      to_decimal(close.actual_credit or 0)
        
        difference = abs(expected_total - actual_total)
        
        # Tolerancia de 1 centavo por redondeos
        if difference > to_decimal('0.01'):
            return False, f"Diferencia de ${float(difference):.2f} en cierre de caja. Esperado: ${float(expected_total):.2f}, Actual: ${float(actual_total):.2f}"
        
        # Validar que los totales individuales sean consistentes
        if close.total_amount and abs(float(close.total_amount) - float(expected_total)) > 0.01:
            return False, f"Inconsistencia en total_amount. Esperado: ${float(expected_total):.2f}, Registrado: ${float(close.total_amount):.2f}"
        
        return True, None
        
    except Exception as e:
        current_app.logger.error(f"Error al validar integridad de cierre: {e}", exc_info=True)
        return False, f"Error al validar: {str(e)}"






"""
Helpers para validación de entrada y datos
"""
import re
from typing import Tuple, Optional
from decimal import Decimal, InvalidOperation


# Patrones de validación
SALE_ID_PATTERN = re.compile(r'^[A-Z0-9\-]{1,50}$')
EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
RUT_PATTERN = re.compile(r'^[\d\.\-kK]{8,12}$')


def validate_sale_id(sale_id: str) -> Tuple[bool, Optional[str]]:
    """
    Valida formato de sale_id
    
    Returns:
        Tuple[bool, Optional[str]]: (es_válido, mensaje_error)
    """
    if not sale_id or not isinstance(sale_id, str):
        return False, "ID de venta inválido"
    
    sale_id = sale_id.strip()
    
    if len(sale_id) == 0:
        return False, "ID de venta no puede estar vacío"
    
    if len(sale_id) > 50:
        return False, "ID de venta no puede tener más de 50 caracteres"
    
    if not SALE_ID_PATTERN.match(sale_id):
        return False, "ID de venta contiene caracteres inválidos. Solo se permiten letras mayúsculas, números y guiones."
    
    return True, None


def validate_quantity(qty_str: str, max_qty: int = 100, min_qty: int = 1) -> Tuple[bool, Optional[int], Optional[str]]:
    """
    Valida cantidad
    
    Args:
        qty_str: String con la cantidad
        max_qty: Cantidad máxima permitida
        min_qty: Cantidad mínima permitida
    
    Returns:
        Tuple[bool, Optional[int], Optional[str]]: (es_válido, cantidad, mensaje_error)
    """
    if not qty_str:
        return False, None, "Cantidad no proporcionada"
    
    try:
        qty = int(qty_str)
    except (ValueError, TypeError):
        return False, None, "Cantidad debe ser un número entero"
    
    if qty < min_qty:
        return False, None, f"La cantidad debe ser al menos {min_qty}"
    
    if qty > max_qty:
        return False, None, f"La cantidad no puede ser mayor a {max_qty}"
    
    return True, qty, None


def validate_amount(amount_str: str, min_amount: float = 0.01, max_amount: float = 10000000.0) -> Tuple[bool, Optional[float], Optional[str]]:
    """
    Valida monto monetario
    
    Args:
        amount_str: String con el monto
        min_amount: Monto mínimo permitido
        max_amount: Monto máximo permitido
    
    Returns:
        Tuple[bool, Optional[float], Optional[str]]: (es_válido, monto, mensaje_error)
    """
    if not amount_str:
        return False, None, "Monto no proporcionado"
    
    try:
        amount = float(amount_str)
    except (ValueError, TypeError):
        return False, None, "Monto inválido"
    
    if amount < min_amount:
        return False, None, f"El monto debe ser al menos ${min_amount:,.2f}"
    
    if amount > max_amount:
        return False, None, f"El monto no puede ser mayor a ${max_amount:,.2f}"
    
    return True, amount, None


def validate_email(email: str) -> Tuple[bool, Optional[str]]:
    """
    Valida formato de email
    
    Returns:
        Tuple[bool, Optional[str]]: (es_válido, mensaje_error)
    """
    if not email or not isinstance(email, str):
        return False, "Email inválido"
    
    email = email.strip()
    
    if len(email) == 0:
        return False, "Email no puede estar vacío"
    
    if len(email) > 254:  # RFC 5321
        return False, "Email demasiado largo"
    
    if not EMAIL_PATTERN.match(email):
        return False, "Formato de email inválido"
    
    return True, None


def validate_rut(rut: str) -> Tuple[bool, Optional[str]]:
    """
    Valida formato de RUT chileno
    
    Returns:
        Tuple[bool, Optional[str]]: (es_válido, mensaje_error)
    """
    if not rut or not isinstance(rut, str):
        return False, "RUT inválido"
    
    rut = rut.strip()
    
    if len(rut) == 0:
        return False, "RUT no puede estar vacío"
    
    if not RUT_PATTERN.match(rut):
        return False, "Formato de RUT inválido"
    
    return True, None


def sanitize_for_logging(data: any) -> any:
    """
    Elimina información sensible de los datos para logging
    
    Args:
        data: Datos a sanitizar (dict, list, str, etc.)
    
    Returns:
        Datos sanitizados
    """
    if isinstance(data, dict):
        sanitized = {}
        for key, value in data.items():
            key_lower = key.lower()
            # Redactar campos sensibles
            if any(sensitive in key_lower for sensitive in ['key', 'password', 'token', 'secret', 'api_key', 'pin']):
                if isinstance(value, str) and len(value) > 0:
                    sanitized[key] = value[:10] + '***REDACTED***' if len(value) > 10 else '***REDACTED***'
                else:
                    sanitized[key] = '***REDACTED***'
            else:
                sanitized[key] = sanitize_for_logging(value)
        return sanitized
    elif isinstance(data, list):
        return [sanitize_for_logging(item) for item in data]
    elif isinstance(data, str):
        # No sanitizar strings directamente, solo en contexto de dicts
        return data
    else:
        return data


def validate_employee_id(employee_id: str) -> Tuple[bool, Optional[str]]:
    """
    Valida formato de employee_id
    
    Returns:
        Tuple[bool, Optional[str]]: (es_válido, mensaje_error)
    """
    if not employee_id:
        return False, "ID de empleado no proporcionado"
    
    employee_id = str(employee_id).strip()
    
    if len(employee_id) == 0:
        return False, "ID de empleado no puede estar vacío"
    
    if len(employee_id) > 50:
        return False, "ID de empleado demasiado largo"
    
    # Permitir UUIDs, números, y strings alfanuméricos
    if not re.match(r'^[A-Za-z0-9\-_]{1,50}$', employee_id):
        return False, "ID de empleado contiene caracteres inválidos"
    
    return True, None




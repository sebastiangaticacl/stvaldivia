"""
Helper para generar keys de idempotencia (P0-007, P0-011)
"""
import hashlib
import json
from typing import List, Dict, Any
from datetime import datetime
from app.helpers.timezone_utils import CHILE_TZ


def generate_sale_idempotency_key(
    cart_items: List[Dict[str, Any]],
    register_id: str,
    employee_id: str,
    payment_type: str,
    total: float
) -> str:
    """
    Genera key de idempotencia para una venta (P0-007)
    
    Args:
        cart_items: Items del carrito
        register_id: ID de la caja
        employee_id: ID del empleado
        payment_type: Tipo de pago
        total: Total de la venta
        
    Returns:
        str: Key de idempotencia (SHA256, 64 caracteres)
    """
    # Normalizar items (solo campos relevantes, ordenados)
    normalized_items = sorted([
        {
            'item_id': str(item.get('item_id', '')),
            'quantity': int(item.get('quantity', 0)),
            'price': float(item.get('price', 0))
        }
        for item in cart_items
    ], key=lambda x: x['item_id'])
    
    # Crear string de datos
    data_string = json.dumps({
        'items': normalized_items,
        'register_id': str(register_id),
        'employee_id': str(employee_id),
        'payment_type': str(payment_type),
        'total': round(float(total), 2),
        'minute_bucket': datetime.now(CHILE_TZ).strftime('%Y%m%d%H%M')  # Mismo minuto = misma key
    }, sort_keys=True)
    
    # Generar hash
    return hashlib.sha256(data_string.encode()).hexdigest()[:64]


def generate_close_idempotency_key(
    register_id: str,
    shift_date: str,
    employee_id: str
) -> str:
    """
    Genera key de idempotencia para un cierre de caja (P0-011)
    
    Args:
        register_id: ID de la caja
        shift_date: Fecha del turno
        employee_id: ID del empleado
        
    Returns:
        str: Key de idempotencia (SHA256, 64 caracteres)
    """
    data_string = json.dumps({
        'register_id': str(register_id),
        'shift_date': str(shift_date),
        'employee_id': str(employee_id)
    }, sort_keys=True)
    
    return hashlib.sha256(data_string.encode()).hexdigest()[:64]




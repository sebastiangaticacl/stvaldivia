"""
Utilidades para cálculos financieros usando Decimal para precisión
"""
from decimal import Decimal, ROUND_HALF_UP
from typing import Union


def to_decimal(value: Union[str, int, float, Decimal, None]) -> Decimal:
    """
    Convierte un valor a Decimal de forma segura
    
    Args:
        value: Valor a convertir (puede ser str, int, float, Decimal o None)
        
    Returns:
        Decimal: Valor convertido a Decimal, o Decimal('0') si es None o inválido
    """
    if value is None:
        return Decimal('0')
    
    if isinstance(value, Decimal):
        return value
    
    try:
        # Convertir a string primero para evitar problemas de precisión con float
        return Decimal(str(value))
    except (ValueError, TypeError):
        return Decimal('0')


def calculate_total(items: list) -> float:
    """
    Calcula el total de una lista de items usando Decimal para precisión
    
    Args:
        items: Lista de dicts con 'quantity' y 'price' o 'subtotal'
        
    Returns:
        float: Total calculado (redondeado a 2 decimales)
    """
    total = Decimal('0')
    
    for item in items:
        try:
            # Intentar usar subtotal si existe
            if 'subtotal' in item:
                subtotal = to_decimal(item.get('subtotal', 0))
                total += subtotal
            else:
                # Calcular desde quantity y price
                quantity = to_decimal(item.get('quantity', 1))
                price = to_decimal(item.get('price', 0))
                total += quantity * price
        except (ValueError, TypeError, KeyError):
            continue
    
    # Redondear a 2 decimales y convertir a float para compatibilidad
    return float(total.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))


def safe_float(value: Union[str, int, float, Decimal, None], default: float = 0.0) -> float:
    """
    Convierte un valor a float de forma segura, usando Decimal internamente
    
    Args:
        value: Valor a convertir
        default: Valor por defecto si la conversión falla
        
    Returns:
        float: Valor convertido o default si falla
    """
    try:
        decimal_value = to_decimal(value)
        return float(decimal_value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
    except (ValueError, TypeError, Exception):
        return default


def round_currency(value: Union[str, int, float, Decimal]) -> float:
    """
    Redondea un valor monetario a 2 decimales
    
    Args:
        value: Valor a redondear
        
    Returns:
        float: Valor redondeado a 2 decimales
    """
    decimal_value = to_decimal(value)
    return float(decimal_value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))














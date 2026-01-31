"""
Validador para ventas del POS
Valida datos antes de crear ventas
"""
from typing import Dict, List, Any, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class SaleValidationError(Exception):
    """Excepción para errores de validación de venta"""
    pass


def validate_sale_data(
    items: List[Dict[str, Any]],
    total: float,
    payment_type: str,
    employee_id: Optional[str] = None,
    register_id: Optional[str] = None
) -> Tuple[bool, Optional[str]]:
    """
    Valida los datos de una venta antes de crearla
    
    Args:
        items: Lista de items de la venta
        total: Total de la venta
        payment_type: Tipo de pago
        employee_id: ID del empleado
        register_id: ID de la caja
        
    Returns:
        Tuple[bool, Optional[str]]: (es_válido, mensaje_error)
    """
    try:
        # Validar items
        if not items or len(items) == 0:
            return False, "El carrito está vacío"
        
        # Validar cada item
        calculated_total = 0.0
        for item in items:
            # Validar campos requeridos
            if not item.get('item_id'):
                return False, f"Item sin ID: {item.get('name', 'Producto desconocido')}"
            
            if not item.get('name'):
                return False, f"Item sin nombre: {item.get('item_id')}"
            
            # Validar cantidad
            quantity = item.get('quantity', 0)
            if not isinstance(quantity, (int, float)) or quantity <= 0:
                return False, f"Cantidad inválida para {item.get('name')}: {quantity}"
            
            # Validar precio
            price = item.get('price', 0)
            if not isinstance(price, (int, float)) or price < 0:
                return False, f"Precio inválido para {item.get('name')}: {price}"
            
            # Validar subtotal
            subtotal = item.get('subtotal', 0)
            expected_subtotal = float(quantity) * float(price)
            
            # Permitir pequeña diferencia por redondeo (0.01)
            if abs(float(subtotal) - expected_subtotal) > 0.01:
                logger.warning(
                    f"Subtotal no coincide para {item.get('name')}: "
                    f"esperado {expected_subtotal}, recibido {subtotal}"
                )
            
            calculated_total += float(subtotal)
        
        # Validar total
        if not isinstance(total, (int, float)) or total < 0:
            return False, f"Total inválido: {total}"
        
        # Permitir pequeña diferencia por redondeo (0.10)
        if abs(float(total) - calculated_total) > 0.10:
            logger.warning(
                f"Total no coincide: esperado {calculated_total}, recibido {total}"
            )
            # No fallar, solo advertir
        
        # Validar tipo de pago
        valid_payment_types = ['Cash', 'Debit', 'Credit', 'EFECTIVO', 'DÉBITO', 'CRÉDITO']
        payment_type_upper = str(payment_type).upper()
        if payment_type_upper not in [pt.upper() for pt in valid_payment_types]:
            return False, f"Tipo de pago inválido: {payment_type}"
        
        # Validar empleado
        if not employee_id:
            return False, "ID de empleado requerido"
        
        # Validar caja
        if not register_id:
            return False, "ID de caja requerido"
        
        return True, None
        
    except Exception as e:
        logger.error(f"Error en validación de venta: {e}", exc_info=True)
        return False, f"Error de validación: {str(e)}"


def validate_cart_item(item: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Valida un item del carrito
    
    Args:
        item: Diccionario con datos del item
        
    Returns:
        Tuple[bool, Optional[str]]: (es_válido, mensaje_error)
    """
    try:
        if not item.get('item_id'):
            return False, "Item sin ID"
        
        quantity = item.get('quantity', 0)
        if not isinstance(quantity, (int, float)) or quantity <= 0:
            return False, f"Cantidad inválida: {quantity}"
        
        price = item.get('price', 0)
        if not isinstance(price, (int, float)) or price < 0:
            return False, f"Precio inválido: {price}"
        
        return True, None
        
    except Exception as e:
        return False, f"Error de validación: {str(e)}"








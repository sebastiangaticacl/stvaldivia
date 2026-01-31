"""
Validador de seguridad para ventas del POS
Incluye validaciones robustas para prevenir fraudes
"""
from typing import Dict, List, Any, Optional, Tuple
import logging
from flask import current_app, session
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Límites de seguridad
MAX_QUANTITY_PER_ITEM = 9999  # Máxima cantidad por item
MAX_TOTAL_PER_SALE = 9999999  # Máximo total por venta
MIN_PRICE = 0  # Precio mínimo
MAX_PRICE = 9999999  # Precio máximo

# Tipos de pago válidos
VALID_PAYMENT_TYPES = [
    'Efectivo', 'Débito', 'Crédito', 'Transferencia', 'QR', 'Prepago',
    'Cash', 'Debit', 'Credit', 'Transfer', 'Prepaid'
]

# Límite de tiempo para considerar sesión activa (30 minutos)
SESSION_ACTIVE_TIMEOUT_MINUTES = 30


class SaleSecurityValidationError(Exception):
    """Excepción para errores de validación de seguridad"""
    pass


def validate_inventory_availability(
    items: List[Dict[str, Any]],
    pos_service: Any
) -> Tuple[bool, Optional[str]]:
    """
    Valida que los productos existan y estén disponibles antes de crear la venta
    
    Args:
        items: Lista de items del carrito
        pos_service: Instancia de PosService
        
    Returns:
        Tuple[bool, Optional[str]]: (es_válido, mensaje_error)
    """
    try:
        for item in items:
            item_id = str(item.get('item_id', ''))
            quantity = int(item.get('quantity', 0))
            item_name = item.get('name', 'Producto desconocido')
            
            if not item_id:
                return False, f"Producto sin ID: {item_name}"
            
            # Re-validar que el producto existe y está activo
            product = pos_service.get_product(item_id)
            
            # Si no se encuentra como item normal, buscar como kit
            if not product:
                product = pos_service.get_item_kit(item_id)
            
            if not product:
                return False, f"Producto no encontrado o eliminado: {item_name} (ID: {item_id})"
            
            # Verificar que el producto está activo (si tiene campo deleted o active)
            deleted = product.get('deleted', '0')
            if deleted == '1' or str(deleted).lower() == 'true':
                return False, f"Producto no disponible: {item_name} (está eliminado)"
            
            is_active = product.get('active', True)
            if is_active is False or str(is_active).lower() == 'false':
                return False, f"Producto no disponible: {item_name} (está inactivo)"
            
            # NOTA: Validación de stock físico requeriría un sistema de inventario
            # Por ahora, solo validamos existencia y estado activo
            
            # VALIDACIÓN NUEVA: Verificar que productos kit tengan receta configurada
            try:
                from app.models.product_models import Product
                from app.helpers.product_validation_helper import can_sell_product
                
                # Buscar producto en BD
                product_db = None
                try:
                    product_id_int = int(item_id)
                    product_db = Product.query.get(product_id_int)
                except (ValueError, TypeError):
                    # Si no es numérico, buscar por nombre
                    product_db = Product.query.filter_by(name=item_name).first()
                
                if product_db:
                    puede_venderse, mensaje_error = can_sell_product(product_db)
                    if not puede_venderse:
                        return False, mensaje_error or f"Producto '{item_name}' no puede venderse: requiere receta configurada"
            except Exception as e:
                # Si falla la validación, solo loguear pero no bloquear (para no romper flujo existente)
                logger.warning(f"Error al validar receta de producto {item_name}: {e}")
            
        return True, None
        
    except Exception as e:
        logger.error(f"Error al validar disponibilidad de inventario: {e}", exc_info=True)
        return False, f"Error al validar inventario: {str(e)}"


def validate_prices_match_api(
    items: List[Dict[str, Any]],
    pos_service: Any
) -> Tuple[bool, Optional[str], Optional[List[Dict[str, Any]]]]:
    """
    Re-valida precios desde la API y compara con el carrito
    
    Args:
        items: Lista de items del carrito
        pos_service: Instancia de PosService
        
    Returns:
        Tuple[bool, Optional[str], Optional[List]]: (es_válido, mensaje_error, items_corregidos)
    """
    try:
        corrected_items = []
        price_mismatches = []
        
        for item in items:
            item_id = str(item.get('item_id', ''))
            cart_price = float(item.get('price', 0))
            cart_quantity = int(item.get('quantity', 1))
            item_name = item.get('name', 'Producto desconocido')
            
            # Obtener precio actual desde la API
            product = pos_service.get_product(item_id)
            if not product:
                product = pos_service.get_item_kit(item_id)
            
            if not product:
                return False, f"Producto no encontrado para validar precio: {item_name}", None
            
            # Obtener precio desde el producto
            api_price = float(product.get('unit_price', 0) or product.get('price', 0))
            
            # Si el precio del carrito difiere del precio de la API, rechazar
            if abs(cart_price - api_price) > 0.01:  # Tolerancia de 1 centavo
                price_mismatches.append({
                    'item': item_name,
                    'cart_price': cart_price,
                    'api_price': api_price
                })
                logger.warning(
                    f"Precio no coincide para {item_name}: "
                    f"carrito=${cart_price}, API=${api_price}"
                )
            
            # Usar precio de la API (actualizado)
            corrected_item = item.copy()
            corrected_item['price'] = api_price
            corrected_item['subtotal'] = api_price * cart_quantity
            corrected_items.append(corrected_item)
        
        if price_mismatches:
            # Formatear mensaje de error
            mismatch_messages = [
                f"{m['item']}: carrito=${m['cart_price']:.2f} vs API=${m['api_price']:.2f}"
                for m in price_mismatches
            ]
            error_msg = (
                "Los precios han cambiado. Por favor, actualiza el carrito. "
                f"Diferencias: {', '.join(mismatch_messages)}"
            )
            return False, error_msg, corrected_items
        
        return True, None, corrected_items
        
    except Exception as e:
        logger.error(f"Error al validar precios: {e}", exc_info=True)
        return False, f"Error al validar precios: {str(e)}", None


def validate_quantities_reasonable(items: List[Dict[str, Any]]) -> Tuple[bool, Optional[str]]:
    """
    Valida que las cantidades sean razonables
    
    Args:
        items: Lista de items del carrito
        
    Returns:
        Tuple[bool, Optional[str]]: (es_válido, mensaje_error)
    """
    try:
        for item in items:
            quantity = item.get('quantity', 0)
            item_name = item.get('name', 'Producto desconocido')
            
            # Validar que sea un número
            try:
                quantity = int(float(quantity))
            except (ValueError, TypeError):
                return False, f"Cantidad inválida para {item_name}: {quantity}"
            
            # Validar límites
            if quantity <= 0:
                return False, f"Cantidad debe ser mayor a 0 para {item_name}: {quantity}"
            
            if quantity > MAX_QUANTITY_PER_ITEM:
                return False, (
                    f"Cantidad excesiva para {item_name}: {quantity} "
                    f"(máximo permitido: {MAX_QUANTITY_PER_ITEM})"
                )
        
        return True, None
        
    except Exception as e:
        logger.error(f"Error al validar cantidades: {e}", exc_info=True)
        return False, f"Error al validar cantidades: {str(e)}"


def validate_payment_type(payment_type: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Valida y normaliza el tipo de pago
    
    Args:
        payment_type: Tipo de pago recibido
        
    Returns:
        Tuple[bool, Optional[str], Optional[str]]: (es_válido, mensaje_error, tipo_normalizado)
    """
    try:
        if not payment_type:
            return False, "Tipo de pago requerido", None
        
        payment_type_str = str(payment_type).strip()
        payment_type_upper = payment_type_str.upper()
        
        # Normalizar a español
        payment_type_map = {
            'CASH': 'Efectivo',
            'EFECTIVO': 'Efectivo',
            'DEBIT': 'Débito',
            'DÉBITO': 'Débito',
            'CREDIT': 'Crédito',
            'CRÉDITO': 'Crédito',
            'TRANSFER': 'Transferencia',
            'TRANSFERENCIA': 'Transferencia',
            'QR': 'QR',
            'PREPAID': 'Prepago',
            'PREPAGO': 'Prepago'
        }
        
        normalized = payment_type_map.get(payment_type_upper)
        
        if not normalized:
            return False, (
                f"Tipo de pago inválido: {payment_type}. "
                "Tipos válidos: Efectivo, Débito, Crédito, Transferencia, QR, Prepago"
            ), None
        
        return True, None, normalized
        
    except Exception as e:
        logger.error(f"Error al validar tipo de pago: {e}", exc_info=True)
        return False, f"Error al validar tipo de pago: {str(e)}", None


def validate_session_active() -> Tuple[bool, Optional[str]]:
    """
    Valida que la sesión esté activa y no haya expirado
    
    Returns:
        Tuple[bool, Optional[str]]: (es_válida, mensaje_error)
    """
    try:
        # Verificar que existe sesión
        if not session.get('pos_logged_in'):
            return False, "Sesión no válida. Por favor, inicia sesión nuevamente."
        
        # Verificar timestamp de actividad si existe
        last_activity = session.get('last_activity')
        if last_activity:
            try:
                import time
                # last_activity puede ser timestamp (float) o datetime
                if isinstance(last_activity, (int, float)):
                    # Es un timestamp Unix
                    timeout_seconds = SESSION_ACTIVE_TIMEOUT_MINUTES * 60
                    inactive_time = time.time() - last_activity
                    if inactive_time > timeout_seconds:
                        return False, "Tu sesión ha expirado. Por favor, inicia sesión nuevamente."
                elif isinstance(last_activity, str):
                    # Es un string ISO
                    last_activity_dt = datetime.fromisoformat(last_activity)
                    timeout = timedelta(minutes=SESSION_ACTIVE_TIMEOUT_MINUTES)
                    if datetime.utcnow() - last_activity_dt > timeout:
                        return False, "Tu sesión ha expirado. Por favor, inicia sesión nuevamente."
                else:
                    # Es un datetime
                    timeout = timedelta(minutes=SESSION_ACTIVE_TIMEOUT_MINUTES)
                    if datetime.utcnow() - last_activity > timeout:
                        return False, "Tu sesión ha expirado. Por favor, inicia sesión nuevamente."
            except Exception as e:
                logger.warning(f"Error al verificar timestamp de actividad: {e}")
        
        # Verificar que tiene empleado asociado
        if not session.get('pos_employee_id'):
            return False, "Sesión inválida: no hay empleado asociado. Por favor, inicia sesión nuevamente."
        
        # Verificar que tiene caja asociada
        if not session.get('pos_register_id'):
            return False, "Sesión inválida: no hay caja seleccionada. Por favor, selecciona una caja."
        
        return True, None
        
    except Exception as e:
        logger.error(f"Error al validar sesión: {e}", exc_info=True)
        return False, f"Error al validar sesión: {str(e)}"


def validate_register_lock(register_id: str, employee_id: str) -> Tuple[bool, Optional[str]]:
    """
    Valida que la caja esté bloqueada por el empleado correcto
    
    Args:
        register_id: ID de la caja
        employee_id: ID del empleado
        
    Returns:
        Tuple[bool, Optional[str]]: (es_válido, mensaje_error)
    """
    try:
        from app.helpers.register_lock_db import is_register_locked, get_register_lock
        
        # Normalizar IDs a string
        register_id = str(register_id) if register_id else ''
        employee_id = str(employee_id) if employee_id else ''
        
        if not is_register_locked(register_id):
            return False, "La caja no está bloqueada. Por favor, selecciona la caja nuevamente."
        
        lock_info = get_register_lock(register_id)
        if not lock_info:
            return False, "No se pudo verificar el bloqueo de la caja. Por favor, intenta nuevamente."
        
        lock_employee_id = str(lock_info.get('employee_id', '')) if lock_info.get('employee_id') else ''
        
        if lock_employee_id != employee_id:
            return False, (
                f"Esta caja está siendo usada por {lock_info.get('employee_name', 'otro cajero')}. "
                "Por favor, selecciona otra caja."
            )
        
        return True, None
        
    except Exception as e:
        logger.error(f"Error al validar bloqueo de caja: {e}", exc_info=True)
        return False, f"Error al validar bloqueo de caja: {str(e)}"


def validate_total_reasonable(total: float) -> Tuple[bool, Optional[str]]:
    """
    Valida que el total sea razonable
    
    Args:
        total: Total de la venta
        
    Returns:
        Tuple[bool, Optional[str]]: (es_válido, mensaje_error)
    """
    try:
        if not isinstance(total, (int, float)):
            return False, f"Total inválido: {total}"
        
        if total < 0:
            return False, f"Total no puede ser negativo: ${total}"
        
        if total > MAX_TOTAL_PER_SALE:
            return False, f"Total excesivo: ${total} (máximo permitido: ${MAX_TOTAL_PER_SALE})"
        
        return True, None
        
    except Exception as e:
        logger.error(f"Error al validar total: {e}", exc_info=True)
        return False, f"Error al validar total: {str(e)}"


def validate_no_empty_cart(items: List[Dict[str, Any]]) -> Tuple[bool, Optional[str]]:
    """
    Valida que el carrito no esté vacío
    
    Args:
        items: Lista de items del carrito
        
    Returns:
        Tuple[bool, Optional[str]]: (es_válido, mensaje_error)
    """
    if not items or len(items) == 0:
        return False, "El carrito está vacío. Agrega productos antes de procesar el pago."
    
    return True, None


def validate_cart_before_close(items: List[Dict[str, Any]]) -> Tuple[bool, Optional[str]]:
    """
    Valida que el carrito esté vacío antes de cerrar la caja
    
    Args:
        items: Lista de items del carrito
        
    Returns:
        Tuple[bool, Optional[str]]: (es_válido, mensaje_error)
    """
    if items and len(items) > 0:
        item_count = sum(item.get('quantity', 0) for item in items)
        return False, (
            f"No puedes cerrar la caja con {item_count} producto(s) en el carrito. "
            "Por favor, finaliza las ventas pendientes o limpia el carrito."
        )
    
    return True, None


def comprehensive_sale_validation(
    items: List[Dict[str, Any]],
    total: float,
    payment_type: str,
    employee_id: str,
    register_id: str,
    pos_service: Any
) -> Tuple[bool, Optional[str], Optional[List[Dict[str, Any]]]]:
    """
    Validación completa de seguridad antes de crear una venta
    
    Args:
        items: Lista de items del carrito
        total: Total de la venta
        payment_type: Tipo de pago
        employee_id: ID del empleado
        register_id: ID de la caja
        pos_service: Instancia de PosService
        
    Returns:
        Tuple[bool, Optional[str], Optional[List]]: (es_válido, mensaje_error, items_corregidos)
    """
    try:
        # 1. Validar carrito no vacío
        is_valid, error = validate_no_empty_cart(items)
        if not is_valid:
            return False, error, None
        
        # 2. Validar sesión activa
        is_valid, error = validate_session_active()
        if not is_valid:
            return False, error, None
        
        # 3. Validar bloqueo de caja
        is_valid, error = validate_register_lock(register_id, employee_id)
        if not is_valid:
            return False, error, None
        
        # 4. Validar cantidades razonables
        is_valid, error = validate_quantities_reasonable(items)
        if not is_valid:
            return False, error, None
        
        # 5. Validar total razonable
        is_valid, error = validate_total_reasonable(total)
        if not is_valid:
            return False, error, None
        
        # 6. Validar tipo de pago
        is_valid, error, normalized_payment_type = validate_payment_type(payment_type)
        if not is_valid:
            return False, error, None
        
        # 7. Validar disponibilidad de productos (existen y están activos)
        is_valid, error = validate_inventory_availability(items, pos_service)
        if not is_valid:
            return False, error, None
        
        # 8. Re-validar precios desde la API
        is_valid, error, corrected_items = validate_prices_match_api(items, pos_service)
        if not is_valid:
            return False, error, corrected_items
        
        # Si llegamos aquí, todo es válido
        return True, None, corrected_items if corrected_items else items
        
    except Exception as e:
        logger.error(f"Error en validación completa de seguridad: {e}", exc_info=True)
        return False, f"Error de validación: {str(e)}", None


import logging
import json
from datetime import datetime, timedelta
import uuid
from decimal import ROUND_HALF_UP
from flask import render_template, request, jsonify, session, redirect, url_for, flash, current_app, send_file, send_from_directory
from app.utils.timezone import CHILE_TZ
from app.blueprints.pos import caja_bp
from app.blueprints.pos.services import pos_service
from app.infrastructure.services.ticket_printer_service import TicketPrinterService
from app.models import PosSale, PosSaleItem, RegisterClose, db
from app.models.pos_models import PaymentIntent
from app.helpers.rate_limiter import rate_limit
from app.helpers.sale_security_validator import (
    validate_session_active, comprehensive_sale_validation,
    validate_payment_type, validate_quantities_reasonable, MAX_QUANTITY_PER_ITEM
)
from app.helpers.sale_audit_logger import SaleAuditLogger
from app.helpers.session_manager import update_session_activity
from app.helpers.shift_manager_compat import get_shift_status
from app.helpers.register_lock_db import is_register_locked, get_register_lock
from app.infrastructure.external.phppos_kiosk_client import PHPPosKioskClient
from app.application.services.service_factory import get_shift_service
from app import socketio
from app.helpers.financial_utils import to_decimal, round_currency, safe_float
from app.helpers.register_session_service import RegisterSessionService
from app.helpers.idempotency_helper import generate_sale_idempotency_key
from app.models.jornada_models import Jornada

logger = logging.getLogger(__name__)


def generate_ticket_code(register_code: str, sale_id: int) -> str:
    """
    Genera un código de ticket único en formato: caja1-BMB-000123
    Ejemplo: "caja1-BMB-000123", "caja2-BMB-000456"
    """
    # Formatear el ID de venta con ceros a la izquierda (6 dígitos)
    sale_id_str = str(sale_id).zfill(6)
    return f"{register_code}-BMB-{sale_id_str}"

@caja_bp.route('/ventas', methods=['GET'])
def sales():
    """Pantalla principal del POS - ventas"""
    if not session.get('pos_logged_in'):
        flash("Por favor, inicia sesión primero.", "info")
        return redirect(url_for('caja.login'))
    
    if not session.get('pos_register_id'):
        flash("Por favor, selecciona una caja primero.", "info")
        return redirect(url_for('caja.register'))
    
    # Verificar que la caja esté bloqueada por este cajero
    register_id = session.get('pos_register_id')
    employee_id = session.get('pos_employee_id')
    
    # ⚠️ VALIDACIÓN: Verificar que la caja no sea superadmin_only si el usuario no es superadmin
    from app.models.pos_models import PosRegister
    is_superadmin = False
    if session.get('admin_logged_in'):
        username = session.get('admin_username', '').lower()
        is_superadmin = (username == 'sebagatica')
    
    if register_id:
        register_obj = PosRegister.query.filter(
            (PosRegister.id == register_id) | (PosRegister.code == str(register_id))
        ).first()
        
        if register_obj and register_obj.superadmin_only and not is_superadmin:
            flash("No tienes autorización para usar esta caja.", "error")
            logger.warning(f"⚠️ Intento de acceso no autorizado a caja SUPERADMIN por usuario no superadmin")
            session.pop('pos_register_id', None)
            session.pop('pos_register_name', None)
            return redirect(url_for('caja.register'))
    
    if register_id and employee_id:
        # Normalizar employee_id a string para comparación consistente
        employee_id = str(employee_id) if employee_id else None
        
        if not is_register_locked(register_id):
            flash("La caja no está bloqueada. Por favor, selecciona la caja nuevamente.", "error")
            return redirect(url_for('caja.register'))
        
        lock_info = get_register_lock(register_id)
        if lock_info:
            # Normalizar employee_id del lock para comparación
            lock_employee_id = str(lock_info.get('employee_id', '')) if lock_info.get('employee_id') else ''
            if lock_employee_id != employee_id:
                logger.warning(f"⚠️  Caja {register_id} bloqueada por {lock_employee_id}, pero sesión tiene {employee_id}")
                flash(f"Esta caja está siendo usada por {lock_info.get('employee_name', 'otro cajero')}. Por favor, selecciona otra caja.", "error")
                return redirect(url_for('caja.register'))
    
    # Obtener categorías permitidas de la caja actual
    allowed_categories = None
    if register_id:
        try:
            register_obj = PosRegister.query.filter(
                (PosRegister.id == register_id) | (PosRegister.code == str(register_id))
            ).first()
            if register_obj and register_obj.allowed_categories:
                import json
                allowed_categories = json.loads(register_obj.allowed_categories)
                logger.info(f"🔍 Caja {register_obj.name} tiene restricción de categorías: {allowed_categories}")
        except Exception as e:
            logger.warning(f"Error al obtener categorías permitidas de la caja: {e}")
    
    # Normalizar categorías permitidas para comparación
    normalized_allowed = None
    if allowed_categories:
        normalized_allowed = [cat.upper().strip() for cat in allowed_categories]
        logger.info(f"🔍 Categorías permitidas normalizadas: {normalized_allowed}")
    
    # Obtener nombre del cajero (legacy - mantener por compatibilidad)
    employee_name = session.get('pos_employee_name', '')
    is_david = employee_name and 'David' in employee_name
    
    # Obtener Item Kits desde PHP POS
    products = pos_service.get_products()
    
    # Si el cajero es David Y no hay restricciones de caja, también obtener items normales de ENTRADAS (legacy)
    if is_david and not normalized_allowed:
        try:
            php_pos_client = PHPPosKioskClient()
            normal_items = php_pos_client.get_items(limit=1000)
            
            # Normalizar y agregar items normales que sean de ENTRADAS
            for item in normal_items:
                category_raw = item.get('category') or item.get('category_name') or ''
                
                # Normalizar categoría
                if '>' in category_raw:
                    category = category_raw.split('>')[-1].strip()
                elif category_raw.lower() == 'puerta':
                    category = 'Entradas'  # Mapear "Puerta" a "Entradas"
                else:
                    category = category_raw.strip()
                
                # Normalizar: eliminar "Barra" si está al inicio
                if category.lower().startswith('barra'):
                    category = category.replace('Barra', '').replace('barra', '').strip()
                    if category.startswith('>'):
                        category = category[1:].strip()
                
                category_upper = category.upper()
                
                # Solo agregar si es ENTRADAS (o variaciones)
                if category_upper in ['ENTRADAS', 'ENTRADA'] or 'entrada' in category.lower():
                    # Verificar si ya existe en products (para evitar duplicados)
                    item_id = str(item.get('item_id') or item.get('id') or '')
                    exists = False
                    for existing_product in products:
                        existing_id = str(existing_product.get('item_id') or existing_product.get('item_kit_id') or '')
                        if existing_id == item_id:
                            exists = True
                            break
                    
                    if not exists and item_id:
                        # Normalizar categoría y agregar
                        item['category_normalized'] = 'Entradas'
                        item['category_display'] = 'ENTRADAS'
                        item['is_kit'] = False
                        products.append(item)
            
            logger.info(f"✅ Agregados items normales de ENTRADAS para David ({len([p for p in products if not p.get('is_kit', False)])} items)")
        except Exception as e:
            logger.error(f"Error al obtener items normales para David: {e}")
    
    # Asegurar que los precios sean números y normalizar IDs
    for product in products:
        price = product.get('unit_price') or product.get('price') or 0
        try:
            product['price'] = float(price) if price else 0.0
        except (ValueError, TypeError):
            product['price'] = 0.0
        
        # Normalizar ID: usar item_kit_id si existe, sino item_id
        if 'item_kit_id' in product:
            product['item_id'] = str(product['item_kit_id'])  # Para compatibilidad con el carrito
            product['is_kit'] = True
        elif 'item_id' in product:
            product['item_id'] = str(product['item_id'])
            if 'is_kit' not in product:
                product['is_kit'] = False
    
    # Agrupar productos por categoría normalizada y filtrar por categorías permitidas de la caja
    categorized_products = {}
    for product in products:
        # Usar categoría normalizada si existe, sino normalizar aquí
        category = product.get('category_normalized') or product.get('category_display')
        if not category:
            category = product.get('category_name') or product.get('category') or 'Sin categoría'
            # Normalizar: eliminar "Barra >" y tomar solo la categoría principal
            if '>' in category:
                category = category.split('>')[-1].strip()
            if category.lower().startswith('barra'):
                category = category.replace('Barra', '').replace('barra', '').strip()
                if category.startswith('>'):
                    category = category[1:].strip()
            
            # Mapear "Puerta" a "Entradas"
            if category.lower() == 'puerta':
                category = 'Entradas'
            
            category = category.upper()  # Mostrar en mayúsculas
        
        category_normalized = category.upper().strip()
        
        # FILTRAR POR CATEGORÍAS PERMITIDAS DE LA CAJA (prioridad sobre filtrado por empleado)
        if normalized_allowed:
            # Verificar si la categoría del producto está EXACTAMENTE en las permitidas
            category_allowed = False
            
            # Comparación exacta (case-insensitive)
            if category_normalized in normalized_allowed:
                category_allowed = True
            else:
                # También verificar variaciones comunes (ENTRADAS, ENTRADA, etc.)
                for allowed_cat in normalized_allowed:
                    # Comparación exacta
                    if category_normalized == allowed_cat:
                        category_allowed = True
                        break
                    # Variaciones comunes: ENTRADAS puede venir como "ENTRADA" o viceversa
                    if allowed_cat == 'ENTRADAS' and category_normalized == 'ENTRADA':
                        category_allowed = True
                        break
                    if allowed_cat == 'ENTRADA' and category_normalized == 'ENTRADAS':
                        category_allowed = True
                        break
            
            if not category_allowed:
                logger.debug(f"❌ Producto '{product.get('name')}' con categoría '{category_normalized}' NO permitido para esta caja")
                continue  # Saltar este producto - NO está en las categorías permitidas
        
        # Si el cajero es David Y no hay restricciones de caja, solo mostrar productos de ENTRADAS (legacy)
        # NOTA: Si no hay productos de ENTRADAS en la BD, mostrar todos los productos para evitar que la página quede vacía
        elif is_david:
            category_upper = category.upper()
            # Verificar primero si hay productos de ENTRADAS en la lista completa
            has_entradas_products = any(
                (p.get('category_normalized') or p.get('category_display') or p.get('category_name') or p.get('category') or '').upper() in ['ENTRADAS', 'ENTRADA'] or 
                'entrada' in (p.get('category_normalized') or p.get('category_display') or p.get('category_name') or p.get('category') or '').lower()
                for p in products
            )
            # Solo filtrar si hay productos de ENTRADAS disponibles
            if has_entradas_products:
                if category_upper not in ['ENTRADAS', 'ENTRADA'] and 'entrada' not in category.lower():
                    continue  # Saltar productos que no sean de ENTRADAS
        
        if category not in categorized_products:
            categorized_products[category] = []
        categorized_products[category].append(product)
    
    # Ordenar categorías alfabéticamente y convertir a diccionario para el template
    sorted_categories = sorted(categorized_products.items())
    categorized_products_dict = dict(sorted_categories)
    
    # Log para debugging
    logger.info(f"✅ Productos categorizados: {len(categorized_products_dict)} categorías, {sum(len(prods) for prods in categorized_products_dict.values())} productos totales")
    
    # Obtener carrito de la sesión
    cart = session.get('pos_cart', [])
    
    # Asegurar que los subtotales del carrito sean números
    for item in cart:
        if 'subtotal' in item:
            try:
                item['subtotal'] = safe_float(item.get('subtotal', 0))
            except (ValueError, TypeError):
                item['subtotal'] = float(item.get('quantity', 1)) * float(item.get('price', 0))
    
    # Calcular total
    total = pos_service.calculate_total(cart)
    
    # Contar ventas del cajero desde que abrió la caja (usando locked_at)
    employee_sales_count = 0
    try:
        shift_status = get_shift_status()
        shift_date = shift_status.get('shift_date') if shift_status.get('is_open') else None
        
        if employee_id and shift_date and register_id:
            # Normalizar employee_id a string para comparación
            employee_id_str = str(employee_id)
            
            # Obtener información del bloqueo para saber desde cuándo contar
            lock_info = get_register_lock(register_id)
            locked_at = None
            
            if lock_info and lock_info.get('locked_at'):
                try:
                    # locked_at viene en formato ISO string, convertir a datetime
                    locked_at_str = lock_info['locked_at']
                    if isinstance(locked_at_str, str):
                        # Si termina en Z, quitarlo y agregar UTC
                        if locked_at_str.endswith('Z'):
                            locked_at_str = locked_at_str[:-1] + '+00:00'
                        elif '+' not in locked_at_str and 'T' in locked_at_str:
                            locked_at_str = locked_at_str + '+00:00'
                        locked_at = datetime.fromisoformat(locked_at_str)
                        # Convertir a datetime naive para comparación con created_at de la BD
                        if locked_at.tzinfo:
                            locked_at = locked_at.replace(tzinfo=None)
                except Exception as e:
                    logger.warning(f"Error al parsear locked_at: {e}, contando todas las ventas del turno")
                    locked_at = None
            
            # Contar ventas del empleado desde que abrió la caja
            query = PosSale.query.filter(
                PosSale.employee_id == employee_id_str,
                PosSale.shift_date == shift_date,
                PosSale.register_id == str(register_id)
            )
            
            # Si tenemos locked_at, filtrar solo ventas posteriores
            if locked_at:
                query = query.filter(PosSale.created_at >= locked_at)
            
            sales_count = query.count()
            employee_sales_count = sales_count
            
            logger.debug(
                f"Ventas del cajero {employee_id_str} en turno {shift_date} "
                f"desde {locked_at or 'inicio del turno'}: {sales_count}"
            )
    except Exception as e:
        logger.error(f"Error al contar ventas del cajero: {e}", exc_info=True)
        employee_sales_count = 0
    
    # Verificar si es caja SUPERADMIN
    is_superadmin_register = False
    if register_id:
        register_obj = PosRegister.query.filter(
            (PosRegister.id == register_id) | (PosRegister.code == str(register_id))
        ).first()
        is_superadmin_register = register_obj and register_obj.superadmin_only if register_obj else False
    
    return render_template(
        'pos/sales.html',
        categorized_products=categorized_products_dict,  # Pasar productos agrupados por categoría como diccionario
        cart=cart,
        total=total,
        employee_name=session.get('pos_employee_name', 'Usuario'),
        register_name=session.get('pos_register_name', 'Caja'),
        register_id=str(session.get('pos_register_id')) if session.get('pos_register_id') is not None else None,
        employee_sales_count=employee_sales_count,
        is_superadmin_register=is_superadmin_register,
        is_superadmin=is_superadmin
    )


@caja_bp.route('/api/cart/add', methods=['POST'])
def api_add_to_cart():
    """API: Agregar producto al carrito con validaciones de seguridad"""
    if not session.get('pos_logged_in'):
        return jsonify({'success': False, 'error': 'No autenticado'}), 401
    
    try:
        # Validar sesión activa
        is_valid, error = validate_session_active()
        if not is_valid:
            return jsonify({'success': False, 'error': error}), 401
        
        data = request.get_json()
        item_id = data.get('item_id')
        quantity = int(data.get('quantity', 1))
        
        if not item_id:
            return jsonify({'success': False, 'error': 'item_id requerido'}), 400
        
        # Validar cantidad razonable
        if quantity <= 0:
            return jsonify({'success': False, 'error': 'La cantidad debe ser mayor a 0'}), 400
        
        if quantity > MAX_QUANTITY_PER_ITEM:
            return jsonify({
                'success': False,
                'error': f'Cantidad excesiva. Máximo permitido: {MAX_QUANTITY_PER_ITEM}'
            }), 400
        
        # Obtener información del producto desde PHP POS
        # Puede ser un item normal o un item kit
        product = pos_service.get_product(item_id)
        is_kit = False
        
        if not product:
            # Intentar buscar como item kit
            product = pos_service.get_item_kit(item_id)
            is_kit = product is not None
        
        if not product:
            return jsonify({'success': False, 'error': 'Producto no encontrado'}), 404
        
        # Obtener precio
        price = float(product.get('unit_price', 0) or product.get('price', 0))
        
        # DEBUG: Log el precio obtenido del backend
        logger.info(f"🔍 DEBUG api_add_to_cart - precio obtenido: item_id={item_id}, price={price}, product={product.get('name', 'unknown')}")
        
        # Normalizar ID y determinar si es kit
        if 'item_kit_id' in product:
            product_id = str(product['item_kit_id'])
            product['item_id'] = product_id  # Para compatibilidad
            is_kit = True
        else:
            product_id = str(product.get('item_id', item_id))
            is_kit = False
        
        # Obtener carrito actual
        cart = session.get('pos_cart', [])
        
        # Verificar si el producto ya está en el carrito - normalizar IDs para comparación
        item_found = False
        item_id_str = str(item_id) if item_id else None
        product_id_str = str(product_id) if product_id else None
        
        for item in cart:
            item_cart_id = str(item.get('item_id', '')) if item.get('item_id') else None
            # Comparar ambos IDs normalizados
            if (item_cart_id and item_cart_id == item_id_str) or (item_cart_id and item_cart_id == product_id_str):
                item['quantity'] += quantity
                # Usar el precio que ya tiene el item si existe, sino usar el precio del backend
                existing_price = item.get('price') or item.get('unit_price')
                current_price = existing_price if existing_price and existing_price > 0 else price
                
                # DEBUG: Log el precio que se está usando
                if existing_price and existing_price != price:
                    logger.info(f"🔍 DEBUG api_add_to_cart - usando precio existente: item_id={item_id}, existing_price={existing_price}, backend_price={price}")
                
                item['price'] = current_price
                item['unit_price'] = current_price  # Mantener sincronizado
                item['subtotal'] = item['quantity'] * current_price
                item_found = True
                break
        
        # Si no está, agregarlo
        if not item_found:
            cart.append({
                'item_id': product_id,  # Usar el ID normalizado
                'name': product.get('name', 'Producto'),
                'quantity': quantity,
                'price': price,
                'subtotal': quantity * price,
                'is_kit': is_kit  # Marcar si es kit
            })
        
        # Guardar carrito en sesión
        session['pos_cart'] = cart
        
        # Calcular nuevo total
        total = pos_service.calculate_total(cart)
        
        return jsonify({
            'success': True,
            'cart': cart,
            'total': total,
            'message': 'Producto agregado al carrito'
        })
        
    except Exception as e:
        logger.error(f"Error al agregar al carrito: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@caja_bp.route('/api/cart/remove', methods=['POST'])
def api_remove_from_cart():
    """API: Remover producto del carrito"""
    if not session.get('pos_logged_in'):
        return jsonify({'success': False, 'error': 'No autenticado'}), 401
    
    try:
        data = request.get_json()
        item_id = data.get('item_id')
        quantity = int(data.get('quantity', 1))
        
        if not item_id:
            return jsonify({'success': False, 'error': 'item_id requerido'}), 400
        
        cart = session.get('pos_cart', [])
        
        # Buscar y actualizar/remover item - normalizar IDs para comparación
        new_cart = []
        item_id_str = str(item_id) if item_id else None
        
        for item in cart:
            # Normalizar ambos IDs a string para comparación
            item_id_from_cart = str(item.get('item_id', '')) if item.get('item_id') else None
            
            if item_id_from_cart == item_id_str:
                if item.get('quantity', 0) > quantity:
                    item['quantity'] -= quantity
                    item['subtotal'] = item['quantity'] * item.get('price', 0)
                    new_cart.append(item)
                # Si quantity >= item['quantity'], no agregar (remover completamente)
            else:
                new_cart.append(item)
        
        session['pos_cart'] = new_cart
        
        total = pos_service.calculate_total(new_cart)
        
        return jsonify({
            'success': True,
            'cart': new_cart,
            'total': total,
            'message': 'Producto removido del carrito'
        })
        
    except Exception as e:
        logger.error(f"Error al remover del carrito: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@caja_bp.route('/api/cart/clear', methods=['POST'])
def api_clear_cart():
    """API: Limpiar carrito - FORZAR limpieza completa"""
    if not session.get('pos_logged_in'):
        return jsonify({'success': False, 'error': 'No autenticado'}), 401
    
    # Forzar limpieza completa del carro
    session['pos_cart'] = []
    session.modified = True  # Asegurar que la sesión se guarde
    
    logger.info(f"🧹 Carro limpiado completamente por API")
    
    return jsonify({
        'success': True,
        'cart': [],
        'total': 0,
        'message': 'Carrito limpiado'
    })


@caja_bp.route('/api/cart', methods=['GET'])
def api_get_cart():
    """API: Obtener carrito actual"""
    if not session.get('pos_logged_in'):
        return jsonify({'success': False, 'error': 'No autenticado'}), 401
    
    try:
        cart = session.get('pos_cart', [])
        total = pos_service.calculate_total(cart)
        
        return jsonify({
            'success': True,
            'cart': cart,
            'total': total
        })
    except Exception as e:
        logger.error(f"Error al obtener carrito: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@caja_bp.route('/api/stock/validate', methods=['POST'])
@rate_limit(max_requests=60, window_seconds=60)
def api_validate_stock():
    """
    MEJORA: API para validar stock disponible antes de crear una venta.
    Permite al frontend mostrar alertas antes de confirmar el pago.
    """
    if not session.get('pos_logged_in'):
        return jsonify({'success': False, 'error': 'No autenticado'}), 401
    
    try:
        data = request.get_json()
        cart = data.get('cart', [])
        register_id = session.get('pos_register_id') or data.get('register_id')
        
        if not cart:
            return jsonify({
                'success': True,
                'valid': True,
                'issues': []
            })
        
        # Validar stock usando el servicio mejorado
        from app.application.services.inventory_stock_service import InventoryStockService
        service = InventoryStockService()
        
        # Preparar cart en formato esperado
        cart_formatted = []
        for item in cart:
            cart_formatted.append({
                'product_id': item.get('item_id') or item.get('product_id'),
                'quantity': float(item.get('quantity') or item.get('qty') or 1)
            })
        
        # Validar stock
        all_available, issues = service.validate_stock_availability(
            cart=cart_formatted,
            register_id=register_id
        )
        
        return jsonify({
            'success': True,
            'valid': all_available,
            'issues': issues,
            'has_warnings': len(issues) > 0
        })
        
    except Exception as e:
        logger.error(f"Error al validar stock: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'valid': False,
            'issues': []
        }), 500


@caja_bp.route('/api/sale/create', methods=['POST'])
@rate_limit(max_requests=30, window_seconds=60)  # 30 ventas por minuto
def api_create_sale():
    """API: Crear venta con validaciones de seguridad completas"""
    if not session.get('pos_logged_in'):
        return jsonify({'success': False, 'error': 'No autenticado'}), 401
    
    print_status = "no_intentado"
    
    try:
        # Obtener datos de sesión
        register_id = session.get('pos_register_id')
        employee_id = session.get('pos_employee_id')
        employee_name = session.get('pos_employee_name', 'Cajero')
        
        if not register_id or not employee_id:
            return jsonify({'success': False, 'error': 'No hay caja seleccionada. Por favor, selecciona una caja.'}), 400
        
        # Normalizar employee_id a string
        employee_id = str(employee_id) if employee_id else None
        
        # ==========================================
        # P0-005: Validar RegisterSession OPEN
        # ==========================================
        can_sell, error_msg = RegisterSessionService.can_sell_in_register(register_id)
        if not can_sell:
            # Registrar auditoría (P0-013)
            from app.models.pos_models import SaleAuditLog
            import json as json_lib
            audit = SaleAuditLog(
                event_type='SALE_BLOCKED_NO_SESSION',
                severity='warning',
                actor_user_id=employee_id,
                actor_name=employee_name,
                register_id=register_id,
                payload_json=json_lib.dumps({'error': error_msg})
            )
            db.session.add(audit)
            db.session.commit()
            return jsonify({'success': False, 'error': error_msg}), 403
        
        # Obtener sesión activa
        active_session = RegisterSessionService.get_active_session(register_id)
        if not active_session:
            return jsonify({'success': False, 'error': 'No hay sesión abierta para esta caja'}), 403
        
        # P0-002, P0-004: Validar jornada activa y obtener datos
        jornada = Jornada.query.get(active_session.jornada_id)
        if not jornada:
            return jsonify({'success': False, 'error': 'Jornada asociada no encontrada'}), 500
        
        if jornada.estado_apertura != 'abierto':
            return jsonify({'success': False, 'error': f'La jornada no está abierta (estado: {jornada.estado_apertura})'}), 403
        
        jornada_id = active_session.jornada_id
        shift_date = active_session.shift_date
        
        # ==========================================
        # VALIDACIONES DE SEGURIDAD COMPLETAS
        # ==========================================
        data = request.get_json() or {}
        payment_type = data.get("payment_type")
        payment_provider = data.get("payment_provider")
        payment_intent_id = data.get("payment_intent_id") or data.get("paymentIntentId")

        if not payment_type:
            return jsonify({
                "success": False,
                "error": "Debe seleccionarse un método de pago"
            }), 400
        
        # VALIDACIÓN SUAVE: Asignar GETNET por defecto si falta provider para tarjetas
        if payment_type in ['debit', 'credit']:
            if not payment_provider or payment_provider.strip() == '' or payment_provider == 'NONE':
                logger.warning(
                    f"⚠️ PAYMENT_FLOW: {payment_type} sin provider, asignando GETNET por defecto. "
                    f"Employee: {employee_id}, Register: {register_id}"
                )
                payment_provider = 'GETNET'
        
        # Logging claro del flujo de pago
        if payment_type in ['debit', 'credit']:
            logger.info(
                f"✅ PAYMENT_FLOW: {payment_type} + {payment_provider} - "
                f"Employee: {employee_id}, Register: {register_id}"
            )
        payment_intent = None
        # Si viene payment_intent_id, usar carrito congelado en PaymentIntent (APPROVED)
        if payment_intent_id:
            try:
                intent_uuid = uuid.UUID(str(payment_intent_id))
            except Exception:
                return jsonify({'success': False, 'error': 'payment_intent_id inválido'}), 400

            intent = PaymentIntent.query.get(intent_uuid)
            if not intent:
                return jsonify({'success': False, 'error': 'PaymentIntent no encontrado'}), 404

            # Validar que pertenece a esta caja
            if str(intent.register_id) != str(register_id):
                return jsonify({'success': False, 'error': 'PaymentIntent no pertenece a esta caja'}), 403

            # Debe estar aprobado por el agente
            if intent.status != PaymentIntent.STATUS_APPROVED:
                return jsonify({
                    'success': False,
                    'error': f'PaymentIntent no está APPROVED (actual: {intent.status})'
                }), 400

            # Idempotencia: si ya existe sale_id en metadata_json, devolverlo
            try:
                meta = json.loads(intent.metadata_json) if intent.metadata_json else {}
            except Exception:
                meta = {}
            existing_sale_id = meta.get('sale_id')
            if existing_sale_id:
                return jsonify({
                    'success': True,
                    'sale_id': existing_sale_id,
                    'message': 'Venta ya creada para este PaymentIntent'
                })

            try:
                cart = json.loads(intent.cart_json) if intent.cart_json else []
            except Exception:
                cart = []
            # Reflejar en sesión para compatibilidad con validaciones posteriores
            session['pos_cart'] = cart
            payment_intent = intent
        else:
            cart = session.get('pos_cart', [])
        
        # Calcular total
        total = pos_service.calculate_total(cart)
        
        # Validación completa de seguridad
        is_valid, error_message, validated_items = comprehensive_sale_validation(
            items=cart,
            total=total,
            payment_type=payment_type,
            employee_id=employee_id,
            register_id=register_id,
            pos_service=pos_service
        )
        
        if not is_valid:
            # Registrar evento de seguridad
            SaleAuditLogger.log_security_event(
                event_type='sale_validation_failed',
                employee_id=employee_id,
                employee_name=employee_name,
                register_id=register_id,
                details={
                    'error': error_message,
                    'cart_size': len(cart),
                    'total': total,
                    'payment_type': payment_type
                },
                severity='warning'
            )
            
            logger.warning(f"⚠️ Validación de seguridad falló: {error_message}")
            
            # Si hay items corregidos (precios actualizados), devolverlos
            if validated_items:
                return jsonify({
                    'success': False,
                    'error': error_message,
                    'cart_updated': True,
                    'corrected_cart': validated_items,
                    'corrected_total': pos_service.calculate_total(validated_items)
                }), 400
            
            return jsonify({'success': False, 'error': error_message}), 400
        
        # Usar items validados (con precios actualizados si fue necesario)
        if validated_items:
            cart = validated_items
            total = pos_service.calculate_total(cart)
        
        # Normalizar tipo de pago (ya validado por comprehensive_sale_validation)
        # Mantener este valor para cálculo de pagos y persistencia (NO sobrescribir más abajo).
        _, _, payment_type_normalized = validate_payment_type(payment_type)
        
        # Validar que la caja no esté cerrada
        recent_close = RegisterClose.query.filter(
            RegisterClose.register_id == register_id,
            RegisterClose.closed_at >= datetime.now(CHILE_TZ) - timedelta(hours=2)
        ).order_by(RegisterClose.closed_at.desc()).first()
        
        if recent_close:
            shift_service = get_shift_service()
            current_shift = shift_service.get_current_shift()
            
            if current_shift and recent_close.shift_date == current_shift.shift_date:
                return jsonify({
                    'success': False,
                    'error': f'Esta caja fue cerrada el {recent_close.closed_at.strftime("%Y-%m-%d %H:%M")}. No se pueden hacer más ventas en esta caja durante este turno.'
                }), 400
        
        # ==========================================
        # P1-007: Validar register_id válido
        # ==========================================
        from app.models.pos_models import PosRegister
        is_superadmin = False
        if session.get('admin_logged_in'):
            username = session.get('admin_username', '').lower()
            is_superadmin = (username == 'sebagatica')
        
        register_obj = PosRegister.query.filter(
            (PosRegister.id == register_id) | (PosRegister.code == str(register_id))
        ).first()
        
        if not register_obj:
            error_msg = f'Caja no encontrada: {register_id}'
            logger.error(f"⚠️ P1-007: {error_msg}")
            SaleAuditLogger.log_security_event(
                event_type='sale_validation_failed',
                employee_id=employee_id,
                employee_name=employee_name,
                register_id=register_id,
                details={'error': error_msg},
                severity='error'
            )
            return jsonify({'success': False, 'error': 'Caja no válida. Por favor, selecciona una caja nuevamente.'}), 400
        
        is_superadmin_register = register_obj.superadmin_only if register_obj else False
        
        # Validar que solo superadmin pueda usar caja SUPERADMIN
        if is_superadmin_register and not is_superadmin:
            return jsonify({'success': False, 'error': 'No autorizado para usar esta caja'}), 403

        # --- FIX BEGIN ---
        # Validar contra la caja SOLO si payment_methods está definido
        allowed_methods = register_obj.payment_methods
        payment_type_norm = str(payment_type).strip().lower() if payment_type is not None else ''

        if allowed_methods:
            # allowed_methods puede venir como JSON string
            if isinstance(allowed_methods, str):
                try:
                    allowed_methods = json.loads(allowed_methods)
                except Exception:
                    allowed_methods = []

            # Normalizar lista (lowercase/strip) y soportar strings simples
            if isinstance(allowed_methods, (list, tuple, set)):
                allowed_norm = {
                    str(m).strip().lower()
                    for m in allowed_methods
                    if m is not None and str(m).strip() != ''
                }
            else:
                allowed_norm = {str(allowed_methods).strip().lower()} if str(allowed_methods).strip() else set()

            if allowed_norm and payment_type_norm not in allowed_norm:
                return jsonify({
                    "success": False,
                    "error": f"Método de pago no permitido para esta caja: {payment_type_norm}"
                }), 400
        # --- FIX END ---
        
        # Obtener datos de operación especial si es caja SUPERADMIN
        tipo_operacion = None
        motivo = None
        is_courtesy = False
        is_test = False
        
        # Detectar si el payment_type es "Cortesía" (nuevo medio de pago para superadmin)
        payment_type_upper = payment_type.upper().replace('Í', 'I').replace('í', 'i') if payment_type else ''
        if payment_type_upper in ['CORTESIA', 'COURTESY']:
            if not is_superadmin_register:
                return jsonify({'success': False, 'error': 'Cortesía solo está disponible en la caja de superadmin'}), 403
            is_courtesy = True
            # Forzar total a 0 para cortesías
            total = 0.0
            # Si viene tipo_operacion, usarlo como motivo; si no, usar un motivo por defecto
            tipo_operacion = data.get('tipo_operacion', 'CORTESIA').upper()
            motivo = data.get('motivo', '').strip()
            if not motivo or len(motivo) < 5:
                motivo = f'Cortesía procesada desde medio de pago - {datetime.now(CHILE_TZ).strftime("%Y-%m-%d %H:%M:%S")}'
        
        if is_superadmin_register and not is_courtesy:
            tipo_operacion = data.get('tipo_operacion', '').upper()
            motivo = data.get('motivo', '').strip()
            
            # Solo validar tipo_operacion si no es una cortesía por medio de pago
            if tipo_operacion and tipo_operacion not in ['CORTESIA', 'PRUEBA_DEPLOY']:
                return jsonify({'success': False, 'error': 'Tipo de operación inválido (CORTESIA o PRUEBA_DEPLOY)'}), 400
            
            if tipo_operacion == 'CORTESIA':
                is_courtesy = True
                # Forzar total a 0 para cortesías
                total = 0.0
                if not motivo or len(motivo) < 5:
                    return jsonify({'success': False, 'error': 'Motivo obligatorio para cortesía (mínimo 5 caracteres)'}), 400
            elif tipo_operacion == 'PRUEBA_DEPLOY':
                is_test = True
                if not motivo or len(motivo) < 5:
                    return jsonify({'success': False, 'error': 'Motivo obligatorio para prueba de deploy (mínimo 5 caracteres)'}), 400
        
        # ==========================================
        # P0-007: Idempotencia de venta
        # ==========================================
        idempotency_key = generate_sale_idempotency_key(cart, register_id, employee_id, payment_type, total)
        existing_sale = PosSale.query.filter_by(idempotency_key=idempotency_key).first()
        if existing_sale:
            # Retornar venta existente (idempotencia)
            logger.info(f"✅ Venta duplicada detectada (idempotencia), retornando venta existente: {existing_sale.id}")
            return jsonify({
                'success': True,
                'sale_id': existing_sale.id,
                'sale_id_local': existing_sale.id,
                'message': 'Venta ya procesada (idempotencia)',
                'ticket_printed': 'no_intentado'
            }), 200
        
        # ==========================================
        # CREAR VENTA CON TRANSACCIÓN ATÓMICA
        # ==========================================
        # Generar ID de venta local único
        local_sale_id = f"BMB-{datetime.now(CHILE_TZ).strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
        
        print_status = "no_intentado"
        
        # Actualizar actividad de sesión
        update_session_activity()
        
        # Guardar venta localmente en base de datos con transacción atómica
        try:
            # Verificar bloqueo antes de crear la venta
            if not is_register_locked(register_id):
                raise Exception("La caja ya no está bloqueada")
            
            lock_info = get_register_lock(register_id)
            if lock_info:
                lock_employee_id = str(lock_info.get('employee_id', '')) if lock_info.get('employee_id') else ''
                if lock_employee_id != employee_id:
                    raise Exception(f"La caja está siendo usada por {lock_info.get('employee_name', 'otro cajero')}")
            
            # shift_date y jornada_id ya obtenidos de active_session arriba (P0-004)

            # LOG TEMPORAL (DEBUG)
            print("SALE_CREATE DEBUG =>", {
                "payment_type": payment_type,
                "payment_provider": payment_provider,
                "register_id": register_obj.id if register_obj else None,
                "register_payment_methods": register_obj.payment_methods if register_obj else None
            })
            
            # Calcular montos por método de pago usando Decimal
            # Si es cortesía, todos los pagos deben ser 0
            if is_courtesy:
                total_decimal = to_decimal(0.0)
                payment_cash = 0.0
                payment_debit = 0.0
                payment_credit = 0.0
            else:
                total_decimal = to_decimal(total)
                # Normalizado en español por validate_payment_type()
                # Nota: Transferencia/QR se contabilizan como "no-efectivo" en payment_debit por ahora.
                payment_cash = round_currency(total_decimal) if payment_type_normalized == 'Efectivo' else 0.0
                payment_debit = round_currency(total_decimal) if payment_type_normalized in ['Débito', 'Transferencia', 'QR', 'Prepago'] else 0.0
                payment_credit = round_currency(total_decimal) if payment_type_normalized == 'Crédito' else 0.0
            
            # ==========================================
            # P1-008: Validar que solo un medio de pago tenga valor
            # ==========================================
            payment_methods_with_value = sum([
                1 if payment_cash > 0 else 0,
                1 if payment_debit > 0 else 0,
                1 if payment_credit > 0 else 0
            ])
            
            if payment_methods_with_value > 1:
                error_msg = 'Solo se puede usar un método de pago por venta'
                SaleAuditLogger.log_security_event(
                    event_type='sale_validation_failed',
                    employee_id=employee_id,
                    employee_name=employee_name,
                    register_id=register_id,
                    details={'error': error_msg, 'payment_cash': payment_cash, 'payment_debit': payment_debit, 'payment_credit': payment_credit},
                    severity='error'
                )
                return jsonify({'success': False, 'error': error_msg}), 400
            
            # Nota: la ausencia de payment_type se valida arriba.
            
            # Preparar items para la venta
            # Usar el mismo método de cálculo que calculate_total para consistencia
            sale_items_data = []
            items_total = to_decimal(0.0)
            for item in cart:
                quantity = int(item.get('quantity', 1))
                unit_price = safe_float(item.get('price', 0))
                
                # Usar el mismo método que calculate_total: usar subtotal si existe, sino calcular
                if 'subtotal' in item:
                    # calculate_total usa to_decimal directamente del subtotal
                    subtotal_decimal = to_decimal(item.get('subtotal', 0))
                    items_total += subtotal_decimal
                    subtotal = float(subtotal_decimal)
                else:
                    # Calcular desde quantity y price (igual que calculate_total)
                    quantity_decimal = to_decimal(item.get('quantity', 1))
                    price_decimal = to_decimal(item.get('price', 0))
                    subtotal_decimal = quantity_decimal * price_decimal
                    items_total += subtotal_decimal
                    subtotal = float(subtotal_decimal)
                
                sale_items_data.append({
                    'product_id': str(item.get('item_id', '')),
                    'product_name': item.get('name', 'Producto'),
                    'quantity': quantity,
                    'unit_price': unit_price,
                    'subtotal': subtotal
                })
            
            # ==========================================
            # P1-005: Validar integridad de totales
            # ==========================================
            # Verificar que la suma de items coincida con total_amount
            # Usar el mismo método de cálculo que calculate_total para consistencia
            # calculate_total redondea a 2 decimales usando quantize, así que hacemos lo mismo aquí
            from decimal import Decimal
            total_from_items_decimal = items_total.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            total_from_items = total_from_items_decimal
            
            total_from_payments = to_decimal(round_currency(to_decimal(payment_cash + payment_debit + payment_credit)))
            
            # Recalcular total usando el mismo método que calculate_total para asegurar consistencia
            recalculated_total = pos_service.calculate_total(cart)
            expected_total = to_decimal(recalculated_total) if not is_courtesy else to_decimal(0.0)
            
            # Tolerancia de 2 pesos para redondeos (aumentada para evitar falsos positivos por diferencias de redondeo)
            tolerance = to_decimal(2.0)
            
            if abs(total_from_items - expected_total) > tolerance:
                error_msg = f'Inconsistencia en totales: items suman ${total_from_items} pero total esperado es ${expected_total}'
                logger.error(f"⚠️ P1-005: {error_msg}")
                SaleAuditLogger.log_security_event(
                    event_type='sale_validation_failed',
                    employee_id=employee_id,
                    employee_name=employee_name,
                    register_id=register_id,
                    details={
                        'error': error_msg,
                        'total_from_items': float(total_from_items),
                        'expected_total': float(expected_total),
                        'difference': float(abs(total_from_items - expected_total))
                    },
                    severity='error'
                )
                return jsonify({'success': False, 'error': 'Error de cálculo en totales. Por favor, intenta nuevamente.'}), 400
            
            if abs(total_from_payments - expected_total) > tolerance and not is_courtesy:
                error_msg = f'Inconsistencia en pagos: pagos suman ${total_from_payments} pero total esperado es ${expected_total}'
                logger.error(f"⚠️ P1-005: {error_msg}")
                SaleAuditLogger.log_security_event(
                    event_type='sale_validation_failed',
                    employee_id=employee_id,
                    employee_name=employee_name,
                    register_id=register_id,
                    details={
                        'error': error_msg,
                        'total_from_payments': float(total_from_payments),
                        'expected_total': float(expected_total),
                        'difference': float(abs(total_from_payments - expected_total))
                    },
                    severity='error'
                )
                return jsonify({'success': False, 'error': 'Error de cálculo en pagos. Por favor, intenta nuevamente.'}), 400
            
            # Crear venta local
            local_sale = PosSale(
                sale_id_phppos=None,
                total_amount=round_currency(to_decimal(total)) if not is_courtesy else 0.0,
                payment_type=payment_type_normalized,
                payment_cash=payment_cash,
                payment_debit=payment_debit,
                payment_credit=payment_credit,
                employee_id=employee_id,
                employee_name=employee_name,
                register_id=register_id,
                register_name=session.get('pos_register_name', 'Caja'),
                shift_date=shift_date,  # P0-004: Ya validado desde active_session
                jornada_id=jornada_id,  # P0-004: Asociación fuerte
                synced_to_phppos=False,
                is_courtesy=is_courtesy,
                is_test=is_test,
                no_revenue=(is_superadmin_register or is_courtesy or is_test),  # P0-016
                idempotency_key=idempotency_key  # P0-007
            )
            db.session.add(local_sale)
            db.session.flush()  # Para obtener el ID
            
            # FASE 1: Generar ticket QR automáticamente al crear venta
            from app.helpers.ticket_entrega_service import TicketEntregaService
            ticket_created, ticket_obj, ticket_msg = TicketEntregaService.create_ticket_for_sale(
                sale=local_sale,
                employee_id=employee_id,
                employee_name=employee_name,
                register_id=register_id
            )
            
            if ticket_created and ticket_obj:
                logger.info(f"✅ Ticket QR generado: {ticket_obj.display_code} para venta {local_sale.id}")
                # Emitir evento SocketIO para actualizar "Últimas entregas"
                try:
                    socketio.emit('ticket_created', {
                        'ticket_id': ticket_obj.id,
                        'display_code': ticket_obj.display_code,
                        'sale_id': local_sale.id,
                        'register_id': register_id,
                        'created_at': datetime.now(CHILE_TZ).isoformat()
                    }, namespace='/pos')
                except Exception as e:
                    logger.warning(f"Error al emitir evento ticket_created: {e}")
            elif not ticket_created:
                logger.warning(f"⚠️  No se pudo crear ticket QR: {ticket_msg}")
            
            # Si es caja SUPERADMIN, crear registro de auditoría
            if is_superadmin_register and tipo_operacion and motivo:
                from app.models.superadmin_sale_audit_models import SuperadminSaleAudit
                admin_user_id = session.get('admin_username', employee_id)
                admin_user_name = session.get('admin_username', employee_name)
                
                audit = SuperadminSaleAudit(
                    sale_id=local_sale.id,
                    register_id=register_id,
                    admin_user_id=admin_user_id,
                    admin_user_name=admin_user_name,
                    tipo_operacion=tipo_operacion,
                    motivo=motivo,
                    total=round_currency(to_decimal(total)) if not is_courtesy else 0.0
                )
                db.session.add(audit)
                logger.info(f"✅ Auditoría creada para venta SUPERADMIN: {tipo_operacion} - {motivo[:50]}")
            
            # Agregar items
            for item_data in sale_items_data:
                sale_item = PosSaleItem(
                    sale_id=local_sale.id,
                    product_id=item_data['product_id'],
                    product_name=item_data['product_name'],
                    quantity=item_data['quantity'],
                    unit_price=item_data['unit_price'],
                    subtotal=item_data['subtotal']
                )
                db.session.add(sale_item)
            
            # Commit de la transacción
            db.session.commit()

            # Si esta venta viene de un PaymentIntent, persistir vínculo en metadata_json (idempotencia)
            if payment_intent is not None:
                try:
                    meta = json.loads(payment_intent.metadata_json) if payment_intent.metadata_json else {}
                except Exception:
                    meta = {}
                meta['sale_id'] = local_sale_id
                meta['sale_id_local'] = local_sale.id
                meta['sale_created_at'] = datetime.now(CHILE_TZ).isoformat()
                payment_intent.metadata_json = json.dumps(meta, ensure_ascii=False)
                payment_intent.updated_at = datetime.utcnow()
                db.session.commit()
            
            # Si llegamos aquí, la transacción fue exitosa
            logger.info(f"✅ Venta guardada localmente (ID local: {local_sale.id}, ID venta: {local_sale_id})")
            
            # ==========================================
            # CREAR ESTADO DE ENTREGA (NO DESCONTAR INVENTARIO)
            # ==========================================
            # Según la lógica operativa de Club Bimba:
            # - NO se descuenta inventario al vender
            # - El inventario solo se descuenta al entregar (por bartender)
            # - Crear estado de entrega para tracking
            try:
                from app.services.sale_delivery_service import get_sale_delivery_service
                delivery_service = get_sale_delivery_service()
                
                # Crear estado de entrega para esta venta
                delivery_status = delivery_service.create_delivery_status(local_sale)
                logger.info(f"✅ Estado de entrega creado para venta {delivery_status.sale_id}")
                
            except Exception as e:
                logger.error(f"⚠️ Error al crear estado de entrega (venta guardada igualmente): {e}", exc_info=True)
                # No fallar la venta si hay error en el estado de entrega
            
            # Registrar auditoría
            sale_data_for_audit = {
                'total_amount': round_currency(to_decimal(total)),
                'payment_type': payment_type_normalized,
                'items': sale_items_data
            }
            SaleAuditLogger.log_sale_created(
                sale_id=local_sale.id,
                sale_data=sale_data_for_audit,
                employee_id=employee_id,
                employee_name=employee_name,
                register_id=register_id
            )
            
            # Auto-imprimir ticket
            try:
                printer_service = TicketPrinterService()
                
                # Si es pago en efectivo, abrir cajón de dinero
                if payment_type_normalized == 'Efectivo':
                    try:
                        drawer_opened = printer_service.open_cash_drawer()
                        if drawer_opened:
                            logger.info(f"✅ Cajón de dinero abierto para venta {local_sale.id} (pago en efectivo)")
                        else:
                            logger.warning(f"⚠️  No se pudo abrir cajón de dinero para venta {local_sale.id}")
                    except Exception as drawer_error:
                        logger.error(f"Error al abrir cajón de dinero: {drawer_error}")
                
                # Preparar datos de venta para impresión
                sale_data = {
                    'sale_id': local_sale_id,
                    'total': round_currency(to_decimal(total)),
                    'items': cart,
                    'payment_type': payment_type_normalized,
                    'register_name': session.get('pos_register_name', 'POS'),
                    'employee_name': employee_name
                }
                
                # Si existe ticket QR (FASE 1), pasar qr_token/display_code al servicio de impresión
                if ticket_created and ticket_obj:
                    sale_data['qr_token'] = ticket_obj.qr_token
                    sale_data['ticket_display_code'] = ticket_obj.display_code
                
                # NOTA: La impresión se hace desde el cliente Windows (navegador), no desde el servidor Linux
                # El servidor solo genera la imagen del ticket con QR, que se abre en el navegador para imprimir
                # Por lo tanto, siempre deshabilitamos auto_print en el servidor
                print_status = "impresion_desde_cliente"
                logger.info(f"📄 Ticket generado para venta {local_sale.id} - Se imprimirá desde el cliente Windows")
            except Exception as e:
                logger.error(f"❌ Error al imprimir ticket automáticamente: {e}", exc_info=True)
                print_status = "error_impresion"
            
            # P0-015: Notificar en tiempo real SIN exponer datos sensibles
            try:
                # Evento público (sin datos sensibles)
                socketio.emit('pos_sale_created', {
                    'register_id': register_id,
                    'event': 'sale_created',
                    'sale_id': local_sale.id,
                    'created_at': datetime.now(CHILE_TZ).isoformat()
                }, namespace='/pos')
                
                # Evento privado para admin (solo si es admin)
                is_admin = session.get('admin_logged_in', False)
                if is_admin:
                    socketio.emit('pos_sale_created_admin', {
                        'sale': local_sale.to_dict(),
                        'register_id': register_id,
                        'register_name': session.get('pos_register_name')
                    }, namespace='/admin')
                
                # FASE 8: Emitir evento de actividad para visor de cajas (sin datos sensibles)
                socketio.emit('register_activity', {
                    'register_id': register_id,
                    'action': 'sale_created',
                    'sale_id': local_sale.id,
                    'timestamp': datetime.now(CHILE_TZ).isoformat()
                }, namespace='/admin')
                
                # Emitir actualización de métricas del dashboard
                from app.helpers.dashboard_metrics_service import get_metrics_service
                metrics_service = get_metrics_service()
                metrics = metrics_service.get_all_metrics(use_cache=False)
                socketio.emit('metrics_update', {'metrics': metrics}, namespace='/admin_stats')
            except Exception as e:
                logger.warning(f"Error al enviar notificación de venta: {e}")
            
            # Enviar evento a n8n (después de crear venta exitosamente)
            try:
                from app.helpers.n8n_client import send_sale_created
                send_sale_created(
                    sale_id=str(local_sale.id),
                    amount=float(total),
                    payment_method=payment_type_normalized,
                    register_id=register_id
                )
            except Exception as e:
                logger.warning(f"Error enviando evento de venta a n8n: {e}")
            
            # Limpiar carrito
            session['pos_cart'] = []
            session.modified = True
            
            # Incluir información del ticket QR en la respuesta (FASE 1)
            ticket_info = None
            if ticket_created and ticket_obj:
                ticket_info = {
                    'ticket_id': ticket_obj.id,
                    'display_code': ticket_obj.display_code,
                    'qr_token': ticket_obj.qr_token,
                    'ticket_url': url_for('caja.view_ticket', ticket_id=ticket_obj.id)
                }
            
            return jsonify({
                'success': True,
                'sale_id': local_sale_id,
                'sale_id_local': local_sale.id,
                'message': 'Venta creada exitosamente',
                'ticket_printed': print_status,
                'ticket': ticket_info  # FASE 1: Información del ticket QR
            })
                    
        except Exception as e:
            logger.error(f"Error al guardar venta localmente: {e}", exc_info=True)
            db.session.rollback()
            
            # Registrar evento de seguridad
            SaleAuditLogger.log_security_event(
                event_type='sale_creation_failed',
                employee_id=employee_id,
                employee_name=employee_name,
                register_id=register_id,
                details={'error': str(e)},
                severity='error'
            )
            
            return jsonify({
                'success': False,
                'error': f'Error al guardar venta: {str(e)}'
            }), 500
            
    except Exception as e:
        logger.error(f"Error al crear venta: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@caja_bp.route('/api/sale/<int:sale_id>/cancel', methods=['POST'])
def api_cancel_sale(sale_id):
    """API: Cancelar una venta (P0-008) - Solo admin/superadmin"""
    # Validar permisos
    is_admin = session.get('admin_logged_in', False)
    if not is_admin:
        return jsonify({'success': False, 'error': 'No autorizado. Solo administradores pueden cancelar ventas.'}), 403
    
    data = request.get_json() or {}
    reason = data.get('reason', '').strip()
    
    if not reason or len(reason) < 5:
        return jsonify({'success': False, 'error': 'Motivo obligatorio (mínimo 5 caracteres)'}), 400
    
    try:
        sale = PosSale.query.get(sale_id)
        if not sale:
            return jsonify({'success': False, 'error': 'Venta no encontrada'}), 404
        
        if sale.is_cancelled:
            return jsonify({'success': False, 'error': 'La venta ya está cancelada'}), 400
        
        # Cancelar venta
        sale.is_cancelled = True
        sale.cancelled_at = datetime.now(CHILE_TZ).replace(tzinfo=None)
        sale.cancelled_by = session.get('admin_username', 'Admin')
        sale.cancelled_reason = reason
        
        db.session.commit()
        
        # P0-013: Registrar auditoría
        from app.models.pos_models import SaleAuditLog
        import json as json_lib
        audit = SaleAuditLog(
            event_type='SALE_CANCELLED',
            severity='warning',
            actor_user_id=session.get('admin_username'),
            actor_name=session.get('admin_username', 'Admin'),
            register_id=sale.register_id,
            sale_id=sale.id,
            jornada_id=sale.jornada_id,
            payload_json=json_lib.dumps({
                'reason': reason,
                'total_amount': float(sale.total_amount),
                'payment_type': sale.payment_type
            })
        )
        db.session.add(audit)
        db.session.commit()
        
        logger.warning(f"⚠️ Venta {sale_id} cancelada por {session.get('admin_username')}: {reason}")
        
        return jsonify({'success': True, 'message': 'Venta cancelada correctamente'})
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error al cancelar venta: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@caja_bp.route('/ticket/<int:ticket_id>', methods=['GET'])
def view_ticket(ticket_id):
    """FASE 1: Ver ticket de entrega con QR"""
    try:
        from app.models.ticket_entrega_models import TicketEntrega
        import qrcode
        import io
        import base64
        
        ticket = TicketEntrega.query.get(ticket_id)
        if not ticket:
            flash("Ticket no encontrado", "error")
            return redirect(url_for('home.index'))
        
        # Generar QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )
        qr.add_data(ticket.qr_token)  # El QR contiene el token, no el display_code
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")
        
        # Convertir a base64 para mostrar en HTML
        img_buffer = io.BytesIO()
        qr_img.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        qr_base64 = base64.b64encode(img_buffer.getvalue()).decode()
        
        return render_template(
            'pos/ticket_entrega.html',
            ticket=ticket,
            qr_base64=qr_base64,
            qr_token=ticket.qr_token
        )
        
    except Exception as e:
        logger.error(f"Error al mostrar ticket: {e}", exc_info=True)
        flash(f"Error al mostrar ticket: {str(e)}", "error")
        return redirect(url_for('home.index'))


@caja_bp.route('/ticket/<int:ticket_id>/print', methods=['GET'])
def print_ticket(ticket_id):
    """FASE 1: Imprimir ticket de entrega"""
    try:
        from app.models.ticket_entrega_models import TicketEntrega
        from app.infrastructure.services.ticket_printer_service import TicketPrinterService
        
        ticket = TicketEntrega.query.get(ticket_id)
        if not ticket:
            flash("Ticket no encontrado", "error")
            return redirect(url_for('home.index'))
        
        # Usar servicio de impresión existente
        printer_service = TicketPrinterService()
        
        # Generar e imprimir ticket (adaptar método existente o crear nuevo)
        # Por ahora, redirigir a vista para imprimir desde navegador
        return redirect(url_for('caja.view_ticket', ticket_id=ticket_id))
        
    except Exception as e:
        logger.error(f"Error al imprimir ticket: {e}", exc_info=True)
        flash(f"Error al imprimir ticket: {str(e)}", "error")
        return redirect(url_for('home.index'))


# ============================================================================
# ENDPOINTS SIMPLES PARA INTEGRACIÓN GETNET LOCAL
# ============================================================================

@caja_bp.route('/api/caja/venta-ok', methods=['POST'])
@rate_limit(max_requests=30, window_seconds=60)
def api_venta_ok():
    """
    Endpoint simple para registrar ventas exitosas con Getnet.
    Se llama DESPUÉS de que Getnet confirma el pago localmente.
    
    Body esperado:
    {
        "total": 15000,
        "venta": {
            "caja_codigo": "caja1",
            "cajero": "usuario_x",
            "items": [
                { "sku": "PISCO_SOUR", "nombre": "Pisco Sour", "cantidad": 2, "precio_unitario": 5000 }
            ]
        },
        "getnet": {
            "responseCode": "0",
            "responseMessage": "Aprobado",
            "authorizationCode": "123456"
        }
    }
    """
    if not session.get('pos_logged_in'):
        return jsonify({'ok': False, 'error': 'No autenticado'}), 401
    
    try:
        data = request.get_json() or {}
        total = data.get('total', 0)
        venta = data.get('venta', {})
        getnet = data.get('getnet', {})
        
        # Validaciones básicas
        if not total or total <= 0:
            return jsonify({'ok': False, 'error': 'Total inválido'}), 400
        
        # Obtener datos del payload o de la sesión
        caja_codigo = venta.get('caja_codigo') or session.get('pos_register_id', '')
        cajero = venta.get('cajero') or session.get('pos_employee_name', 'Cajero')
        items_raw = venta.get('items', [])
        
        if not items_raw or len(items_raw) == 0:
            return jsonify({'ok': False, 'error': 'Carrito vacío. No hay items en la venta.'}), 400
        
        # Obtener datos de sesión para validación
        register_id = session.get('pos_register_id')
        employee_id = session.get('pos_employee_id')
        employee_name = session.get('pos_employee_name', 'Cajero')
        
        if not register_id or not employee_id:
            return jsonify({'ok': False, 'error': 'No hay caja seleccionada'}), 400
        
        # Convertir items del formato especificado al formato interno
        # Formato especificado: { "sku": "...", "nombre": "...", "cantidad": 2, "precio_unitario": 5000 }
        cart = []
        for item in items_raw:
            sku = item.get('sku') or item.get('item_id') or item.get('id') or ''
            nombre = item.get('nombre') or item.get('name') or 'Producto sin nombre'
            cantidad = item.get('cantidad') or item.get('quantity') or item.get('qty') or 1
            precio_unitario = item.get('precio_unitario') or item.get('price') or item.get('unit_price') or 0
            subtotal = item.get('subtotal') or (precio_unitario * cantidad)
            
            cart.append({
                'item_id': str(sku),
                'name': nombre,
                'quantity': cantidad,
                'price': precio_unitario,
                'subtotal': subtotal
            })
        
        # Validar sesión activa
        can_sell, error_msg = RegisterSessionService.can_sell_in_register(register_id)
        if not can_sell:
            return jsonify({'ok': False, 'error': error_msg}), 403
        
        active_session = RegisterSessionService.get_active_session(register_id)
        if not active_session:
            return jsonify({'ok': False, 'error': 'No hay sesión abierta para esta caja'}), 403
        
        jornada = Jornada.query.get(active_session.jornada_id)
        if not jornada or jornada.estado_apertura != 'abierto':
            return jsonify({'ok': False, 'error': 'Jornada no está abierta'}), 403
        
        # Determinar tipo de pago desde getnet
        payment_type = 'Débito'  # Por defecto
        if getnet.get('cardType') == 'CREDIT' or getnet.get('CardType') == 'CREDIT':
            payment_type = 'Crédito'
        
        # Validar que Getnet devolvió OK
        response_code = getnet.get('responseCode') or getnet.get('ResponseCode', '')
        if str(response_code) != '0':
            logger.warning(f"⚠️ Getnet no devolvió OK: responseCode={response_code}")
            return jsonify({'ok': False, 'error': f'Getnet no devolvió OK. ResponseCode: {response_code}'}), 400
        
        # Crear la venta
        from app.helpers.financial_utils import to_decimal, round_currency
        
        # Validación completa de seguridad
        is_valid, error_message, validated_items = comprehensive_sale_validation(
            items=cart,
            total=float(total),
            payment_type=payment_type,
            employee_id=str(employee_id),
            register_id=str(register_id),
            pos_service=pos_service
        )
        
        if not is_valid:
            # Registrar evento de seguridad
            SaleAuditLogger.log_security_event(
                event_type='sale_validation_failed',
                employee_id=str(employee_id),
                employee_name=employee_name,
                register_id=str(register_id),
                details={
                    'error': error_message,
                    'cart_size': len(cart),
                    'total': total,
                    'payment_type': payment_type
                },
                severity='warning'
            )
            return jsonify({'ok': False, 'error': error_message or 'Validación falló'}), 400
        
        # Usar items validados si están disponibles
        if validated_items:
            cart = validated_items
        
        # Crear la venta
        # NOTA: Los datos de Getnet (authorizationCode, responseCode, etc.) no se guardan directamente en PosSale
        # Se pueden guardar en PaymentIntent si es necesario para trazabilidad futura
        sale = PosSale(
            register_id=str(register_id),
            register_name=session.get('pos_register_name', caja_codigo),
            employee_id=str(employee_id),
            employee_name=employee_name,
            jornada_id=active_session.jornada_id,
            shift_date=active_session.shift_date,
            total_amount=to_decimal(total),
            payment_type=payment_type,
            payment_provider='GETNET',
            payment_cash=0,
            payment_debit=to_decimal(total) if payment_type == 'Débito' else 0,
            payment_credit=to_decimal(total) if payment_type == 'Crédito' else 0
        )
        
        db.session.add(sale)
        db.session.flush()  # Para obtener el ID antes de generar ticket_code
        
        # Generar ticket_code único (ej: "caja1-BMB-000123")
        ticket_code = generate_ticket_code(caja_codigo, sale.id)
        sale.sale_id_phppos = ticket_code  # Usar sale_id_phppos temporalmente para almacenar ticket_code
        
        # Agregar items de la venta
        for item in cart:
            sale_item = PosSaleItem(
                sale_id=sale.id,
                product_id=str(item.get('item_id', '')),
                product_name=item.get('name', 'Producto'),
                quantity=int(item.get('quantity', 1)),
                unit_price=to_decimal(item.get('price', 0)),
                subtotal=to_decimal(item.get('subtotal', 0))
            )
            db.session.add(sale_item)
        
        # Limpiar carrito de la sesión
        session['pos_cart'] = []
        
        db.session.commit()
        
        logger.info(f"✅ Venta Getnet registrada: Sale ID {sale.id}, Ticket {ticket_code}, Total ${total}, Tipo {payment_type}")
        
        return jsonify({
            'ok': True,
            'venta_id': sale.id,
            'ticket_code': ticket_code
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Error en api_venta_ok: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({'ok': False, 'error': str(e)}), 500


@caja_bp.route('/api/caja/venta-fallida-log', methods=['POST'])
@rate_limit(max_requests=50, window_seconds=60)
def api_venta_fallida_log():
    """
    Endpoint simple para registrar logs de ventas fallidas con Getnet.
    NO crea una venta, solo registra el intento fallido.
    
    Body esperado:
    {
        "total": 15000,
        "venta": {
            "caja_codigo": "caja1",
            "cajero": "usuario_x",
            "items": [
                { "sku": "PISCO_SOUR", "nombre": "Pisco Sour", "cantidad": 2, "precio_unitario": 5000 }
            ]
        },
        "motivo": "Rechazado por Getnet (responseCode XX)"
    }
    """
    if not session.get('pos_logged_in'):
        return jsonify({'ok': False, 'error': 'No autenticado'}), 401
    
    try:
        data = request.get_json() or {}
        total = data.get('total', 0)
        venta = data.get('venta', {})
        motivo = data.get('motivo', 'Pago rechazado por Getnet')
        
        # Obtener datos del payload o de la sesión
        caja_codigo = venta.get('caja_codigo') or session.get('pos_register_id', '')
        cajero = venta.get('cajero') or session.get('pos_employee_name', 'Cajero')
        items = venta.get('items', [])
        
        # Validaciones básicas
        if not caja_codigo:
            return jsonify({'ok': False, 'error': 'caja_codigo es requerido'}), 400
        
        if not items or len(items) == 0:
            items = []  # Permitir items vacíos para logs
        
        # Registrar en tabla logs_intentos_pago
        from app.models.pos_models import LogIntentoPago
        from app.helpers.financial_utils import to_decimal
        
        log_entry = LogIntentoPago(
            caja_codigo=str(caja_codigo),
            cajero=str(cajero),
            total=to_decimal(total),
            items_json=items,  # Guardar como JSON
            motivo=str(motivo)
        )
        
        db.session.add(log_entry)
        db.session.commit()
        
        logger.warning(f"⚠️ Pago Getnet rechazado: Total ${total}, Motivo: {motivo}, Cajero: {cajero}, Caja: {caja_codigo}")
        
        return jsonify({
            'ok': True
        }), 200
        
    except Exception as e:
        logger.error(f"Error en api_venta_fallida_log: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({'ok': False, 'error': str(e)}), 500


@caja_bp.route('/api/caja/venta/<int:venta_id>/voucher', methods=['GET'])
def api_venta_voucher(venta_id):
    """
    Endpoint para obtener datos de una venta para mostrar en el voucher.
    
    Usado por voucher.html para renderizar el ticket térmico.
    """
    try:
        from app.models.pos_models import PosSale, PosSaleItem
        from datetime import datetime
        
        # Obtener la venta
        venta = PosSale.query.get(venta_id)
        if not venta:
            return jsonify({'error': 'Venta no encontrada'}), 404
        
        # Obtener items de la venta
        items = PosSaleItem.query.filter_by(sale_id=venta_id).all()
        
        # Formatear items para el voucher
        items_formateados = []
        for item in items:
            items_formateados.append({
                'sku': item.product_id,
                'nombre': item.product_name,
                'cantidad': item.quantity,
                'precio_unitario': float(item.unit_price)
            })
        
        # Obtener ticket_code
        ticket_code = venta.sale_id_phppos or f"TOTEM-{venta_id}"
        
        # Formatear fecha (shift_date es String, usar created_at si está disponible)
        fecha = venta.created_at.strftime('%d/%m/%Y %H:%M:%S') if venta.created_at else datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        
        # Determinar medio de pago
        medio_pago = venta.payment_type or 'TARJETA_GETNET'
        if venta.payment_provider == 'GETNET':
            medio_pago = 'TARJETA_GETNET'
        
        # Preparar respuesta
        respuesta = {
            'fecha': fecha,
            'ticket_code': ticket_code,
            'items': items_formateados,
            'subtotal': float(venta.total_amount),
            'total': float(venta.total_amount),
            'medio_pago': medio_pago
        }
        
        # Agregar datos de Getnet si están disponibles (desde PaymentIntent u otra fuente)
        # TODO: Si guardas datos de Getnet en PaymentIntent, agregarlos aquí
        # respuesta['getnet'] = { ... }
        
        return jsonify(respuesta), 200
        
    except Exception as e:
        logger.error(f"Error en api_venta_voucher: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@caja_bp.route('/voucher/<int:venta_id>', methods=['GET'])
def voucher_page(venta_id):
    """
    Página HTML para mostrar e imprimir el voucher de una venta.
    
    Esta página se abre automáticamente después de una venta exitosa
    y llama a window.print() para imprimir el ticket térmico.
    """
    import os
    voucher_path = os.path.join(current_app.static_folder, 'html', 'voucher.html')
    
    if os.path.exists(voucher_path):
        return send_from_directory(
            os.path.join(current_app.static_folder, 'html'),
            'voucher.html'
        )
    else:
        # Fallback: renderizar template si existe
        return render_template('voucher.html', venta_id=venta_id), 404

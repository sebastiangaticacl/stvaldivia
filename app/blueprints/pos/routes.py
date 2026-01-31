"""
Rutas para el POS propio
"""
import json
import logging
import time
from flask import render_template, request, jsonify, session, redirect, url_for, flash, current_app
from . import caja_bp
from .services import pos_service
from app.infrastructure.services.ticket_printer_service import TicketPrinterService
from app.helpers.pos_api import authenticate_employee, get_employees
from app.helpers.rate_limiter import rate_limit
from app.helpers.session_manager import update_session_activity, is_session_valid, init_session, clear_expired_session
from app.helpers.financial_utils import to_decimal, round_currency

logger = logging.getLogger(__name__)

# Instancia del servicio importada de services.py


@caja_bp.route('/test-print', methods=['GET', 'POST'])
def test_print():
    """Ruta para probar la impresión de un ticket de prueba"""
    if not session.get('pos_logged_in'):
        # Si es una petición AJAX, devolver JSON
        if request.is_json or request.headers.get('Content-Type') == 'application/json':
            return jsonify({'success': False, 'error': 'No autenticado'}), 401
        flash("Por favor, inicia sesión primero.", "info")
        return redirect(url_for('caja.login'))
    
    try:
        printer_service = TicketPrinterService()
        
        # Datos de prueba
        sale_id = "123456"
        sale_data = {
            'sale_id': sale_id,
            'total': 15000,
            'payment_type': 'Efectivo',
            'register_name': session.get('pos_register_name', 'POS Test'),
            'employee_name': session.get('pos_employee_name', 'Test')
        }
        
        items = [
            {'item_id': '1', 'name': 'Producto de Prueba 1', 'quantity': 2, 'price': 5000, 'subtotal': 10000},
            {'item_id': '2', 'name': 'Producto de Prueba 2', 'quantity': 1, 'price': 5000, 'subtotal': 5000}
        ]
        
        # Imprimir ticket de prueba
        success = printer_service.print_ticket(
            sale_id=sale_id,
            sale_data=sale_data,
            items=items,
            register_name=session.get('pos_register_name', 'POS Test'),
            employee_name=session.get('pos_employee_name', 'Test')
        )
        
        # Si es una petición AJAX, devolver JSON
        if request.is_json or request.headers.get('Content-Type') == 'application/json' or request.method == 'POST':
            if success:
                return jsonify({'success': True, 'message': '✅ Ticket de prueba impreso correctamente'})
            else:
                return jsonify({'success': False, 'message': '⚠️ No se pudo imprimir el ticket de prueba. Verifica la impresora.'}), 400
        
        # Comportamiento legacy para GET (redirección)
        if success:
            flash("✅ Ticket de prueba impreso correctamente", "success")
        else:
            flash("⚠️ No se pudo imprimir el ticket de prueba. Verifica la impresora.", "warning")
        
        return redirect(url_for('caja.sales'))
        
    except Exception as e:
        logger.error(f"Error al imprimir ticket de prueba: {e}", exc_info=True)
        # Si es una petición AJAX, devolver JSON
        if request.is_json or request.headers.get('Content-Type') == 'application/json' or request.method == 'POST':
            return jsonify({'success': False, 'error': str(e)}), 500
        flash(f"Error al imprimir: {str(e)}", "error")
        return redirect(url_for('caja.sales'))


@caja_bp.route('/resumen')
def resumen():
    """Resumen de cajas abiertas para administradores"""
    # Verificar que sea admin
    if not session.get('admin_logged_in'):
        flash("Debes iniciar sesión como administrador para acceder a esta sección.", "info")
        return redirect(url_for('routes.login_admin'))
    
    try:
        from app.helpers.register_lock_db import get_all_register_locks
        from app.models import PosSale, db
        from datetime import datetime, timedelta
        
        # Obtener todas las cajas disponibles - Usar siempre 6 cajas por defecto
        default_registers = [
            {'id': '1', 'name': 'Caja 1'},
            {'id': '2', 'name': 'Caja 2'},
            {'id': '3', 'name': 'Caja 3'},
            {'id': '4', 'name': 'Caja 4'},
            {'id': '5', 'name': 'Caja 5'},
            {'id': '6', 'name': 'Caja 6'},
        ]
        
        try:
            api_registers = pos_service.get_registers()
            # Si la API devuelve cajas, usarlas; si no, usar las por defecto
            if api_registers and len(api_registers) > 0:
                registers = api_registers
            else:
                registers = default_registers
        except Exception as e:
            logger.error(f"Error al obtener cajas desde API: {e}")
            # En caso de error, usar siempre las 6 cajas por defecto
            registers = default_registers
        
        # Asegurar que siempre haya al menos las 6 cajas
        if not registers or len(registers) == 0:
            registers = default_registers
        
        logger.info(f"Cajas a mostrar: {len(registers)} - IDs: {[r['id'] for r in registers]}")
        
        # Obtener bloqueos activos
        register_locks = get_all_register_locks()
        locks_dict = {lock['register_id']: lock for lock in register_locks}
        
        # Obtener fecha del turno actual si está abierto (usando módulo de compatibilidad)
        from app.helpers.shift_manager_compat import get_shift_status
        shift_status = get_shift_status()
        shift_date = shift_status.get('shift_date') if shift_status.get('is_open') else None
        
        # Obtener fecha de hoy para filtrar ventas
        today = datetime.now().strftime('%Y-%m-%d')
        filter_date = shift_date or today
        
        # Obtener cierres de caja del día
        from app.models import RegisterClose, PosSaleItem
        from collections import Counter, defaultdict
        
        register_closes = {}
        try:
            closes_query = RegisterClose.query.filter(
                RegisterClose.shift_date == filter_date
            ).all()
            for close in closes_query:
                reg_id_close = str(close.register_id)
                if reg_id_close not in register_closes:
                    register_closes[reg_id_close] = close
        except Exception as e:
            logger.error(f"Error al obtener cierres de caja: {e}")
        
        # Obtener estadísticas de ventas del día para cada caja
        registers_with_stats = []
        for reg in registers:
            reg_id = str(reg['id'])
            lock_info = locks_dict.get(reg_id)
            
            # Estadísticas de ventas del día
            total_sales = 0
            total_amount = 0.0
            total_cash = 0.0
            total_debit = 0.0
            total_credit = 0.0
            sales_query = []
            products_counter = Counter()
            hour_counter = Counter()
            last_sales = []
            avg_sale = 0.0
            performance = 0.0
            peak_hour = None
            opened_at_formatted = None
            closed_at_formatted = None
            
            try:
                sales_query = PosSale.query.options(
                    db.joinedload(PosSale.items)
                ).filter(
                    PosSale.register_id == reg_id,
                    PosSale.shift_date == filter_date
                ).order_by(PosSale.created_at.desc()).all()
                
                total_sales = len(sales_query)
                if total_sales > 0:
                    # CORRECCIÓN: Usar Decimal para suma de montos
                    from app.helpers.financial_utils import to_decimal, round_currency
                    total_amount = round_currency(
                        sum(to_decimal(sale.total_amount or 0) for sale in sales_query)
                    )
                    total_cash = sum(float(sale.payment_cash) for sale in sales_query)
                    total_debit = sum(float(sale.payment_debit) for sale in sales_query)
                    total_credit = sum(float(sale.payment_credit) for sale in sales_query)
                    
                    # Media de venta
                    avg_sale = total_amount / total_sales if total_sales > 0 else 0.0
                    
                    # Productos más vendidos
                    for sale in sales_query:
                        for item in sale.items:
                            products_counter[item.product_name] += item.quantity
                    
                    # Hora peak y últimas ventas
                    for sale in sales_query:
                        if sale.created_at:
                            hour = sale.created_at.hour
                            hour_counter[hour] += 1
                    
                    # Obtener hora peak
                    if hour_counter:
                        peak_hour_num = hour_counter.most_common(1)[0][0]
                        peak_hour = f"{peak_hour_num:02d}:00"
                    
                    # Últimos 10 tickets
                    last_sales = [
                        {
                            'id': sale.sale_id_phppos or f"#{sale.id}",
                            'total': round_currency(to_decimal(sale.total_amount or 0)),
                            'created_at': sale.created_at.strftime('%H:%M:%S') if sale.created_at else 'N/A',
                            'employee_name': sale.employee_name,
                            'payment_type': sale.payment_type
                        }
                        for sale in sales_query[:10]
                    ]
                    
                    # Rendimiento (ventas por hora si está abierta)
                    if lock_info and lock_info.get('locked_at'):
                        try:
                            locked_at_str = lock_info['locked_at']
                            if locked_at_str.endswith('Z'):
                                locked_at_str = locked_at_str[:-1]
                            if '+' in locked_at_str:
                                locked_at_str = locked_at_str.split('+')[0]
                            
                            locked_at = datetime.fromisoformat(locked_at_str)
                            now = datetime.now()
                            time_diff = now - locked_at
                            
                            if time_diff.total_seconds() > 0:
                                hours_open = time_diff.total_seconds() / 3600
                                performance = total_sales / hours_open if hours_open > 0 else 0.0
                        except:
                            pass
                            
            except Exception as e:
                logger.error(f"Error al obtener estadísticas de caja {reg_id}: {e}")
            
            # Formatear hora de apertura
            if lock_info and lock_info.get('locked_at'):
                try:
                    locked_at_str = lock_info['locked_at']
                    if locked_at_str.endswith('Z'):
                        locked_at_str = locked_at_str[:-1]
                    if '+' in locked_at_str:
                        locked_at_str = locked_at_str.split('+')[0]
                    
                    locked_at = datetime.fromisoformat(locked_at_str)
                    opened_at_formatted = locked_at.strftime('%H:%M:%S')
                except:
                    opened_at_formatted = "N/A"
            
            # Obtener hora de cierre desde RegisterClose
            if reg_id in register_closes:
                close_info = register_closes[reg_id]
                if close_info.closed_at:
                    closed_at_formatted = close_info.closed_at.strftime('%H:%M:%S')
                else:
                    closed_at_formatted = None
            else:
                closed_at_formatted = None
            
            # Calcular tiempo abierta
            time_open = None
            if lock_info and lock_info.get('locked_at'):
                try:
                    locked_at_str = lock_info['locked_at']
                    if locked_at_str.endswith('Z'):
                        locked_at_str = locked_at_str[:-1]
                    if '+' in locked_at_str:
                        locked_at_str = locked_at_str.split('+')[0]
                    
                    locked_at = datetime.fromisoformat(locked_at_str)
                    now = datetime.now()
                    time_diff = now - locked_at
                    
                    if time_diff.total_seconds() < 0:
                        time_open = "0m"
                    else:
                        hours = int(time_diff.total_seconds() // 3600)
                        minutes = int((time_diff.total_seconds() % 3600) // 60)
                        time_open = f"{hours}h {minutes}m"
                except Exception as e:
                    logger.error(f"Error al calcular tiempo abierta para caja {reg_id}: {e}")
                    time_open = "N/A"
            
            # Top 5 productos más vendidos
            top_products = [
                {'name': name, 'quantity': qty}
                for name, qty in products_counter.most_common(5)
            ]
            
            registers_with_stats.append({
                'id': reg_id,
                'name': reg.get('name', f"Caja {reg_id}"),
                'is_open': lock_info is not None,
                'locked_by': lock_info.get('employee_name') if lock_info else None,
                'locked_by_id': lock_info.get('employee_id') if lock_info else None,
                'locked_at': lock_info.get('locked_at') if lock_info else None,
                'opened_at': opened_at_formatted,
                'closed_at': closed_at_formatted,
                'time_open': time_open,
                'total_sales': total_sales,
                'total_amount': total_amount,
                'total_cash': total_cash,
                'total_debit': total_debit,
                'total_credit': total_credit,
                'avg_sale': avg_sale,
                'performance': performance,
                'peak_hour': peak_hour,
                'top_products': top_products,
                'last_sales': last_sales
            })
        
        # Ordenar: cajas abiertas primero
        registers_with_stats.sort(key=lambda x: (not x['is_open'], x['name']))
        
        # Estadísticas generales
        total_open = sum(1 for r in registers_with_stats if r['is_open'])
        total_registers = len(registers_with_stats)
        total_sales_all = sum(r['total_sales'] for r in registers_with_stats)
        total_amount_all = sum(r['total_amount'] for r in registers_with_stats)
        total_cash_all = sum(r['total_cash'] for r in registers_with_stats)
        total_debit_all = sum(r['total_debit'] for r in registers_with_stats)
        total_credit_all = sum(r['total_credit'] for r in registers_with_stats)
        
        # Calcular ticket promedio
        avg_ticket_all = total_amount_all / total_sales_all if total_sales_all > 0 else 0.0
        
        return render_template(
            'pos/resumen.html',
            registers=registers_with_stats,
            total_open=total_open,
            total_registers=total_registers,
            total_sales_all=total_sales_all,
            total_amount_all=total_amount_all,
            total_cash_all=total_cash_all,
            total_debit_all=total_debit_all,
            total_credit_all=total_credit_all,
            avg_ticket_all=avg_ticket_all,
            filter_date=filter_date
        )
        
    except Exception as e:
        logger.error(f"Error en overview de cajas: {e}", exc_info=True)
        flash(f"Error al cargar resumen de cajas: {str(e)}", "error")
        return redirect(url_for('routes.admin_dashboard'))


# Login route moved to views/auth.py





@caja_bp.route('/api/products', methods=['GET'])
def api_get_products():
    """API: Obtener productos actualizados desde PHP POS"""
    if not session.get('pos_logged_in'):
        return jsonify({'success': False, 'error': 'No autenticado'}), 401
    
    try:
        # Obtener productos desde servicio local
        products = pos_service.get_products()
        
        # Obtener caja actual y sus categorías permitidas
        register_id = session.get('pos_register_id')
        allowed_categories = None
        
        if register_id:
            try:
                from app.models.pos_models import PosRegister
                register = PosRegister.query.filter_by(id=int(register_id) if register_id.isdigit() else None).first()
                if register and register.allowed_categories:
                    import json
                    allowed_categories = json.loads(register.allowed_categories)
                    logger.info(f"🔍 Caja {register.name} tiene restricción de categorías: {allowed_categories}")
            except Exception as e:
                logger.warning(f"Error al obtener categorías permitidas de la caja: {e}")
        
        # Filtrar productos por categorías permitidas de la caja
        filtered_products = []
        categorized_products = {}
        
        # Normalizar categorías permitidas para comparación
        normalized_allowed = None
        if allowed_categories:
            normalized_allowed = [cat.upper().strip() for cat in allowed_categories]
            logger.info(f"🔍 Categorías permitidas normalizadas: {normalized_allowed}")
        
        for product in products:
            # Obtener categoría del producto de diferentes campos posibles
            category = product.get('category') or product.get('category_normalized') or product.get('category_display') or 'GENERAL'
            category_normalized = category.upper().strip()
            
            # Si la caja tiene restricciones de categorías, filtrar estrictamente
            if normalized_allowed:
                # Verificar si la categoría del producto está EXACTAMENTE en las permitidas (case-insensitive)
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
                        # Si la categoría contiene la palabra clave (ej: "ENTRADAS" contiene "ENTRADA")
                        if allowed_cat in category_normalized or category_normalized in allowed_cat:
                            # Solo permitir si es una coincidencia razonable (no demasiado permisivo)
                            if len(allowed_cat) >= 5:  # Evitar coincidencias muy cortas
                                category_allowed = True
                                break
                
                if not category_allowed:
                    logger.debug(f"❌ Producto '{product.get('name')}' con categoría '{category_normalized}' NO permitido para esta caja")
                    continue  # Saltar este producto - NO está en las categorías permitidas
            
            filtered_products.append(product)
            
            # Agrupar por categoría
            category_display = product.get('category_display') or category_normalized
            if category_display not in categorized_products:
                categorized_products[category_display] = []
            categorized_products[category_display].append(product)
        
        # Ordenar categorías alfabéticamente
        sorted_categories = {k: categorized_products[k] for k in sorted(categorized_products.keys())}
        
        return jsonify({
            'success': True,
            'products': filtered_products,
            'categorized_products': sorted_categories
        })
    except Exception as e:
        logger.error(f"Error al obtener productos: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# Verify PIN route moved to views/auth.py


# Close register routes moved to views/register.py


# Close shift route moved to views/register.py


# SOS drawer request route moved to views/register.py


# SOS drawer authorize route moved to views/register.py


# Logout routes moved to views/auth.py


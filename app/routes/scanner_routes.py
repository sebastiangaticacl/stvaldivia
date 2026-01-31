"""
Rutas del Sistema de Escaneo y Entregas
"""
from flask import Blueprint, render_template, request, redirect, session, url_for, flash, jsonify
from collections import defaultdict
from app.application.services.service_factory import get_delivery_service
from app.application.validators import SaleIdValidator
from app.application.validators.sale_id_validator import SaleIdValidationError
from app.application.dto.delivery_dto import ScanSaleRequest, DeliveryRequest
from app.helpers.logger import get_logger, log_error
from app.helpers.fraud_detection import save_fraud_attempt
from app.helpers.pos_api import get_entity_details, get_employees, authenticate_employee
from app.infrastructure.rate_limiter.decorators import rate_limit

scanner_bp = Blueprint('scanner', __name__)
logger = get_logger(__name__)


@scanner_bp.route('/scanner', methods=['GET', 'POST'])
@rate_limit(max_requests=30, per_seconds=60)
def scanner():
    """Página del escáner - sistema de entregas independiente de turnos"""
    # Verificar sesión antes de mostrar el escáner
    # Permitir acceso tanto de bartenders autenticados como de admins
    is_admin = session.get('admin_logged_in', False)
    
    if is_admin:
        # Si es admin, crear sesión automática de bartender si no existe
        if 'bartender' not in session:
            admin_username = session.get('admin_username', 'Admin')
            session['bartender'] = f"Admin: {admin_username}"
            session['bartender_id'] = f"admin-{admin_username.lower()}"
            session['bartender_first_name'] = admin_username
            session['bartender_last_name'] = 'Admin'
            session['is_admin_session'] = True  # Marcar como sesión de admin
        # Si no hay barra seleccionada, usar una por defecto o permitir seleccionar
        if 'barra' not in session:
            session['barra'] = 'Barra Principal'  # Barra por defecto para admin
    else:
        # Para bartenders regulares, requiere autenticación normal
        # IMPORTANTE: Primero verificar bartender (login), luego barra (ubicación)
        if 'bartender' not in session:
            flash("Por favor, selecciona un bartender primero.", "info")
            return redirect(url_for('scanner.seleccionar_bartender'))
        if 'barra' not in session:
            flash("Por favor, selecciona una barra.", "info")
            return redirect(url_for('scanner.seleccionar_barra'))

    delivery_service = get_delivery_service()
    fraud_service = delivery_service.fraud_service
    
    items = []
    error = None
    venta_info = None
    fraud_detected = None

    # Validar entrada del usuario usando validador estricto
    user_input_id = (request.form.get('code', '') or request.args.get('sale_id', '')).strip()
    sale_id_canonical = None
    id_for_api_query = None

    if user_input_id:
        try:
            # Sanitizar primero
            sanitized_input = SaleIdValidator.sanitize_input(user_input_id)
            
            # Validar y normalizar usando el validador estricto
            sale_id_canonical, id_for_api_query = SaleIdValidator.validate_and_normalize(sanitized_input)
            
        except SaleIdValidationError as e:
            # Error de validaci?n - mostrar mensaje amigable
            error = f"Error: {str(e)}"
            sale_id_canonical = None
            id_for_api_query = None
        except Exception as e:
            # Error inesperado
            log_error(
                logger,
                "Error validando sale_id",
                error=e,
                context={'user_input': user_input_id[:50]}
            )
            error = f"Error inesperado al validar c?digo: {str(e)}"
            sale_id_canonical = None
            id_for_api_query = None

    # Obtener entregas existentes usando repositorio (optimizado: una sola iteraci?n)
    all_deliveries = delivery_service.delivery_repository.find_all()
    entregados_qty = defaultdict(int)
    entregados_info = {}
    entregados_todos = defaultdict(list)

    # Optimizaci?n: una sola iteraci?n sobre las entregas
    for delivery in all_deliveries:
        key = (delivery.sale_id, delivery.item_name)
        qty = delivery.qty
        
        entregados_qty[key] += qty
        # Solo guardar la primera entrega como info principal
        if key not in entregados_info:
            entregados_info[key] = delivery.to_csv_row()
        entregados_todos[key].append({
            'qty': qty,
            'bartender': delivery.bartender,
            'barra': delivery.barra,
            'timestamp': delivery.timestamp
        })

    # Escanear venta si hay ID
    if id_for_api_query:
        try:
            # Si es un ticket del kiosko (prefijo "B"), buscar primero en tabla pagos
            if sale_id_canonical and sale_id_canonical.startswith("B "):
                try:
                    from app.models.kiosk_models import Pago
                    # Buscar pago por ticket_code
                    pago = Pago.query.filter_by(ticket_code=sale_id_canonical).first()
                    if pago and pago.sale_id_phppos:
                        # Usar el sale_id_phppos para buscar en PHP POS
                        logger.info(f"Ticket del kiosko encontrado: {sale_id_canonical} -> sale_id_phppos: {pago.sale_id_phppos}")
                        sale_id_canonical = pago.sale_id_phppos
                        id_for_api_query = pago.sale_id_phppos
                except Exception as e:
                    logger.warning(f"Error al buscar ticket del kiosko: {e}")
                    # Continuar con b?squeda normal en PHP POS
            
            # Intentar escanear usando el nuevo sistema de entregas primero
            try:
                from app.services.sale_delivery_service import get_sale_delivery_service
                sale_delivery_service = get_sale_delivery_service()
                
                # Obtener información del bartender de forma consistente
                is_admin = session.get('admin_logged_in', False)
                bartender_id = session.get('bartender_id')
                bartender_name = session.get('bartender', 'Desconocido')
                
                # Si es admin y no tiene bartender_id, crearlo
                if is_admin and not bartender_id:
                    admin_username = session.get('admin_username', 'Admin')
                    bartender_id = f"admin-{admin_username.lower()}"
                    bartender_name = f"Admin: {admin_username}"
                
                # Si no hay bartender_id pero sí bartender, usar el nombre como ID temporal
                if not bartender_id and bartender_name:
                    bartender_id = bartender_name
                
                scan_result = sale_delivery_service.scan_ticket(
                    sale_id=sale_id_canonical,
                    scanner_id=bartender_id,
                    scanner_name=bartender_name
                )
                
                if 'error' in scan_result:
                    # Si hay error, intentar con el sistema antiguo
                    scan_request = ScanSaleRequest(sale_id=sale_id_canonical)
                    scan_request.validate()
                    venta_info = delivery_service.scan_sale(scan_request)
                    
                    if 'error' in venta_info:
                        error = venta_info['error']
                        items = []
                    else:
                        items = venta_info.get('items', [])
                        # Crear estado de entrega si no existe
                        try:
                            from app.models.pos_models import PosSale
                            sale = PosSale.query.filter_by(sale_id_phppos=sale_id_canonical).first()
                            if sale:
                                sale_delivery_service.create_delivery_status(sale)
                        except:
                            pass
                else:
                    # Usar datos del nuevo sistema
                    items_detail = scan_result.get('items_detail', [])
                    items = [
                        {
                            'name': item.get('product_name', ''),
                            'quantity': item.get('quantity', 0),
                            'entregado': item.get('entregado', 0),
                            'pendiente': item.get('pendiente', 0)
                        }
                        for item in items_detail
                    ]
                    venta_info = {
                        'sale_id': sale_id_canonical,
                        'items': items,
                        'estado': scan_result.get('estado', 'pendiente'),
                        'items_pendientes': scan_result.get('items_pendientes', 0),
                        'items_entregados': scan_result.get('items_entregados', 0)
                    }
            except Exception as e:
                current_app.logger.warning(f"Error al escanear con nuevo sistema, usando sistema antiguo: {e}")
                # Fallback al sistema antiguo
                scan_request = ScanSaleRequest(sale_id=sale_id_canonical)
                scan_request.validate()
                venta_info = delivery_service.scan_sale(scan_request)
                
                if 'error' in venta_info:
                    error = venta_info['error']
                    items = []
                else:
                    items = venta_info.get('items', [])
                sale_id_canonical = venta_info.get('venta_id', sale_id_canonical)
                
                # Guardar informaci?n completa del ticket escaneado en el log (solo en el primer escaneo)
                if items:
                    from app.helpers.ticket_scans import save_ticket_scan
                    # Preparar items para guardar
                    items_to_save = [{'name': item.get('name', ''), 'quantity': item.get('quantity', 0)} for item in items]
                    # Guardar toda la informaci?n de la venta para uso futuro
                    save_ticket_scan(sale_id_canonical, items_to_save, venta_info)
                
                # Verificar fraudes antes de mostrar el ticket
                sale_time = venta_info.get('fecha_venta', '')
                fraud_check = fraud_service.detect_fraud(sale_id_canonical, sale_time)
                
                if fraud_check['is_fraud']:
                    fraud_detected = fraud_check
                    # Guardar el intento de fraude
                    save_fraud_attempt(
                        sale_id=sale_id_canonical,
                        bartender=session.get('bartender', 'Desconocido'),
                        barra=session.get('barra', 'Desconocida'),
                        item_name='N/A',
                        qty=0,
                        fraud_type=fraud_check['fraud_type'],
                        authorized=False
                    )
        except ValueError as e:
            error = f"Error al escanear venta: {str(e)}"
        except Exception as e:
            log_error(
                logger,
                "Error al escanear venta",
                error=e,
                context={
                    'sale_id': sale_id_canonical,
                    'user_input': user_input_id[:50] if user_input_id else None
                }
            )
            error = f"Error inesperado al escanear venta: {str(e)}"

    # Si se detect? fraude, mostrar la pantalla de fraude
    if fraud_detected and fraud_detected.get('is_fraud'):
        return render_template(
            'fraud_detection.html',
            sale_id=sale_id_canonical,
            fraud_message=fraud_detected['message'],
            fraud_type=fraud_detected['fraud_type'],
            fraud_details=fraud_detected['details'],
            venta_info_adicional=venta_info,
            item_name='',
            qty=0,
            return_url=url_for('scanner.scanner')
        )

    return render_template(
        'index.html',
        items=items,
        error=error,
        sale_id=sale_id_canonical,
        entregados_qty=entregados_qty,
        entregados_info=entregados_info,
        entregados_todos=entregados_todos,
        session_bartender=session.get('bartender'),
        session_barra=session.get('barra'),
        venta_info_adicional=venta_info
    )


@scanner_bp.route('/entregar', methods=['POST'])
@rate_limit(max_requests=50, per_seconds=60)
def entregar():
    """Registrar una entrega - thin controller usando DeliveryService"""
    from flask import current_app
    from app.domain.exceptions import ShiftNotOpenError, FraudDetectedError, DeliveryValidationError
    from app.helpers.fraud_detection import load_fraud_attempts
    
    # Verificar sesi?n
    if 'barra' not in session or 'bartender' not in session:
        flash("Error: No se ha seleccionado barra o bartender.", "error")
        return redirect(url_for('scanner.seleccionar_barra'))

    # Validar datos del formulario usando validadores estrictos
    from app.application.validators import SaleIdValidator, InputValidator, QuantityValidator
    from app.application.validators.sale_id_validator import SaleIdValidationError
    from app.application.validators.input_validator import InputValidationError
    from app.application.validators.quantity_validator import QuantityValidationError
    
    sale_id_raw = request.form.get('sale_id', '').strip()
    item_name_raw = request.form.get('item_name', '').strip()
    qty_str = request.form.get('qty', '').strip()
    
    # Validar sale_id
    try:
        sale_id_canonical, numeric_sale_id = SaleIdValidator.validate_and_normalize(
            SaleIdValidator.sanitize_input(sale_id_raw)
        )
        sale_id = sale_id_canonical
    except SaleIdValidationError as e:
        flash(f"Error en c?digo de venta: {str(e)}", "error")
        return redirect(url_for('scanner.scanner', sale_id=sale_id_raw))
    
    # Validar item_name
    try:
        item_name = InputValidator.validate_string(
            item_name_raw,
            field_name="Nombre del producto",
            min_length=1,
            max_length=200,
            required=True
        )
    except InputValidationError as e:
        flash(f"Error en nombre del producto: {str(e)}", "error")
        return redirect(url_for('scanner.scanner', sale_id=sale_id))
    
    # Validar cantidad
    try:
        qty = QuantityValidator.validate(qty_str, field_name="Cantidad")
    except QuantityValidationError as e:
        flash(f"Error en cantidad: {str(e)}", "error")
        return redirect(url_for('scanner.scanner', sale_id=sale_id))

    # Usar servicios
    delivery_service = get_delivery_service()
    
    # Obtener informaci?n de la venta para validar cantidad pendiente y fecha
    venta_info = None
    sale_time = None
    
    try:
        scan_request = ScanSaleRequest(sale_id=sale_id)
        scan_request.validate()
        venta_info = delivery_service.scan_sale(scan_request)
        sale_time = venta_info.get('fecha_venta', '') if venta_info and 'error' not in venta_info else None
    except Exception as e:
        current_app.logger.warning(f"Error al obtener info de venta para validaci?n: {e}")
    
    # Validar cantidad pendiente si tenemos info de la venta
    # CORRECCI?N: Sumar todas las cantidades del mismo item (puede haber m?ltiples items con mismo nombre)
    if venta_info and 'error' not in venta_info:
        items = venta_info.get('items', [])
        # Sumar todas las cantidades de items con el mismo nombre
        total_item_qty = sum(
            item.get('quantity', 0) if isinstance(item, dict) else getattr(item, 'quantity', 0)
            for item in items
            if (item.get('name', '') if isinstance(item, dict) else getattr(item, 'name', '')) == item_name
        )
        
        if total_item_qty > 0:
            # CORRECCI?N: Usar transacci?n at?mica con lock para prevenir race conditions
            from app.models import db
            from app.models.delivery_models import Delivery as DeliveryModel
            from sqlalchemy import select
            
            try:
                with db.session.begin():
                    # Obtener entregas existentes con lock para prevenir race conditions
                    existing_deliveries_locked = db.session.execute(
                        select(DeliveryModel)
                        .where(DeliveryModel.sale_id == sale_id)
                        .with_for_update()
                    ).scalars().all()
                    
                    delivered = sum(d.qty for d in existing_deliveries_locked if d.item_name == item_name)
                    pending = total_item_qty - delivered
                    
                    if qty > pending:
                        db.session.rollback()
                        flash(f"No se puede entregar {qty} unidades. Solo hay {pending} pendientes (de {total_item_qty} totales).", "error")
                        return redirect(url_for('scanner.scanner', sale_id=sale_id))
            except Exception as e:
                current_app.logger.error(f"Error al validar cantidad pendiente: {e}", exc_info=True)
                # Continuar sin validaci?n estricta si hay error (fallback)
                pass
    
    # Verificar autorizaci?n de fraudes previos
    fraud_check = delivery_service.fraud_service.detect_fraud(sale_id, sale_time)
    
    if fraud_check['is_fraud']:
        # CORRECCI?N: Mejorar manejo de errores al cargar intentos de fraude
        is_authorized = False
        try:
            fraud_attempts = load_fraud_attempts()
        except Exception as e:
            current_app.logger.error(f"Error al cargar intentos de fraude para {sale_id}: {e}", exc_info=True)
            fraud_attempts = []
        
        # Verificar autorizaci?n previa con validaci?n de timestamp
        from datetime import datetime, timedelta
        for attempt in reversed(fraud_attempts):
            if len(attempt) >= 7 and attempt[0] == sale_id and attempt[6] == fraud_check['fraud_type']:
                if attempt[7] == '1':  # Autorizado
                    # CORRECCI?N: Validar que la autorizaci?n sea reciente (?ltima hora)
                    try:
                        # Intentar obtener timestamp de autorizaci?n (si est? disponible)
                        if len(attempt) > 8:
                            auth_time_str = attempt[8] if isinstance(attempt[8], str) else str(attempt[8])
                            try:
                                auth_time = datetime.fromisoformat(auth_time_str)
                                # Autorizaci?n v?lida solo por 1 hora
                                if (datetime.now() - auth_time).total_seconds() < 3600:
                                    is_authorized = True
                                    break
                            except (ValueError, TypeError):
                                # Si no se puede parsear, asumir autorizaci?n antigua (no v?lida)
                                pass
                        else:
                            # Si no hay timestamp, asumir autorizaci?n antigua (no v?lida)
                            pass
                    except Exception as e:
                        current_app.logger.warning(f"Error al validar timestamp de autorizaci?n: {e}")
                else:
                    break
        
        if not is_authorized:
            # Guardar el intento de fraude
            save_fraud_attempt(
                sale_id=sale_id,
                bartender=session.get('bartender', 'Desconocido'),
                barra=session.get('barra', 'Desconocida'),
                item_name=item_name,
                qty=qty,
                fraud_type=fraud_check['fraud_type'],
                authorized=False
            )
            
            return render_template(
                'fraud_detection.html',
                sale_id=sale_id,
                fraud_message=fraud_check['message'],
                fraud_type=fraud_check['fraud_type'],
                fraud_details=fraud_check['details'],
                venta_info_adicional=venta_info,
                item_name=item_name,
                qty=qty,
                return_url=url_for('scanner.scanner', sale_id=sale_id)
            )

    # Registrar entrega usando el nuevo sistema de entregas
    try:
        from app.services.sale_delivery_service import get_sale_delivery_service
        sale_delivery_service = get_sale_delivery_service()
        
        # Obtener información del bartender y ubicación de forma consistente
        bartender_id = session.get('bartender_id')
        bartender_name = session.get('bartender', 'Desconocido')
        # Si no hay bartender_id pero sí bartender, usar el nombre como ID temporal
        if not bartender_id and bartender_name:
            bartender_id = bartender_name
        
        barra = session.get('barra', '')
        # Mapear barra a ubicación de forma más precisa
        barra_lower = barra.lower()
        if 'pista' in barra_lower or 'principal' in barra_lower:
            ubicacion = 'Barra Pista'
        elif 'terraza' in barra_lower or 'exterior' in barra_lower:
            ubicacion = 'Terraza'
        elif 'vip' in barra_lower:
            ubicacion = 'Barra VIP'
        else:
            ubicacion = barra if barra else 'Barra Principal'
        
        # Entregar producto usando el nuevo servicio (descuenta inventario según receta)
        success, message, delivery_item, ingredients_consumed = sale_delivery_service.deliver_product(
            sale_id=sale_id,
            product_name=item_name,
            quantity=qty,
            bartender_id=bartender_id,
            bartender_name=bartender_name,
            location=ubicacion
        )
        
        if success:
            flash(f"{qty} x {item_name} entregado(s).", "success")
            
            # Mostrar detalle de ingredientes consumidos si aplica
            if ingredients_consumed:
                consumo_detalle = ", ".join([
                    f"{c.get('cantidad', 0)} {c.get('unidad', '')} de {c.get('ingrediente', '')}"
                    for c in ingredients_consumed
                ])
                flash(f"📦 Inventario consumido: {consumo_detalle}", "info")
            
            # Emitir actualización de métricas del dashboard
            try:
                from app import socketio
                from app.helpers.dashboard_metrics_service import get_metrics_service
                metrics_service = get_metrics_service()
                metrics = metrics_service.get_all_metrics(use_cache=False)
                socketio.emit('metrics_update', {'metrics': metrics}, namespace='/admin_stats')
            except Exception as e:
                current_app.logger.warning(f"Error al emitir actualización de métricas: {e}")
        else:
            flash(f"❌ {message}", "error")
            
    except ShiftNotOpenError as e:
        flash(f"?? {str(e)}", "error")
        return redirect(url_for('scanner.seleccionar_barra'))
    except FraudDetectedError as e:
        flash(f"?? {str(e)}", "error")
        return redirect(url_for('scanner.scanner', sale_id=sale_id))
    except DeliveryValidationError as e:
        flash(f"? {str(e)}", "error")
        return redirect(url_for('scanner.scanner', sale_id=sale_id))
    except Exception as e:
        current_app.logger.error(f"Error al registrar entrega: {e}")
        flash(f"? Error al registrar entrega: {str(e)}", "error")
        return redirect(url_for('scanner.scanner', sale_id=sale_id))
    
    return redirect(url_for('scanner.scanner', sale_id=sale_id))


@scanner_bp.route('/barra', methods=['GET', 'POST'])
def seleccionar_barra():
    """Seleccionar barra para la sesión"""
    # Permitir acceso tanto de bartenders autenticados como de admins
    is_admin = session.get('admin_logged_in', False)
    
    if not is_admin:
        # Para bartenders regulares, requiere autenticación normal
        if 'bartender' not in session:
            flash("Por favor, inicia sesión primero.", "info")
            return redirect(url_for('scanner.seleccionar_bartender'))
    
    if request.method == 'POST':
        b = request.form.get('barra')
        if b:
            session['barra'] = b
            # Despu?s de seleccionar barra, ir al scanner
            return redirect(url_for('scanner.scanner'))
        flash("Debes seleccionar una barra.", "error")

    barras = ['Barra Principal', 'Barra Terraza', 'Barra VIP', 'Barra Exterior']
    return render_template(
        'seleccionar_barra.html', 
        barras=barras, 
        current_barra=session.get('barra'),
        bartender_name=session.get('bartender', '')
    )


@scanner_bp.route('/bartender', methods=['GET', 'POST'])
def seleccionar_bartender():
    """Seleccionar y autenticar bartender"""
    from flask import current_app
    import time
    
    selected_employee_id = session.get('selected_employee_id')
    selected_employee_info = session.get('selected_employee_info')

    if request.method == 'POST':
        # Si se cancela la selecci?n
        if request.form.get('cancel'):
            session.pop('selected_employee_id', None)
            session.pop('selected_employee_info', None)
            return redirect(url_for('scanner.seleccionar_bartender'))
        
        # Si se selecciona un empleado
        employee_id = request.form.get('employee_id')
        if employee_id and not selected_employee_id:
            # Obtener informaci?n del empleado
            employee = get_entity_details("employees", employee_id)
            if employee:
                emp_id = employee.get('person_id') or employee.get('employee_id') or employee.get('id')
                emp_name = f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip() or employee.get('name', 'Empleado')
                
                session['selected_employee_id'] = emp_id
                session['selected_employee_info'] = {
                    'id': emp_id,
                    'name': emp_name,
                    'first_name': employee.get('first_name', ''),
                    'last_name': employee.get('last_name', '')
                }
                return redirect(url_for('scanner.seleccionar_bartender'))
            else:
                flash("No se pudo obtener informaci?n del empleado.", "error")
        
        # Si se ingresa el PIN
        pin = request.form.get('pin', '').strip()
        if pin and selected_employee_id:
            if not pin:
                flash("Debes ingresar tu PIN.", "error")
            else:
                # Autenticar empleado con PIN de PHP Point of Sale
                from app.helpers.pos_api import authenticate_employee
                employee = authenticate_employee(None, pin=pin, employee_id=selected_employee_id)
                
                if employee:
                    # Guardar información completa del empleado en la sesión
                    emp_id = employee.get('id') or employee.get('person_id') or employee.get('employee_id')
                    emp_name = employee.get('name') or f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip()
                    
                    if not emp_id:
                        flash("Error: No se pudo obtener el ID del empleado.", "error")
                    else:
                        session['bartender'] = emp_name
                        session['bartender_id'] = str(emp_id)  # Asegurar que sea string para consistencia
                        session['bartender_first_name'] = employee.get('first_name', '')
                        session['bartender_last_name'] = employee.get('last_name', '')
                        session['last_activity'] = time.time()
                        # Limpiar selección temporal
                        session.pop('selected_employee_id', None)
                        session.pop('selected_employee_info', None)
                        flash(f"Bienvenido, {emp_name}!", "success")
                        # Ahora redirigir a seleccionar barra (después del login)
                        return redirect(url_for('scanner.seleccionar_barra'))
                else:
                    flash("PIN incorrecto. Intenta nuevamente.", "error")

    # Obtener lista de empleados bartenders desde la API
    try:
        employees = get_employees(only_bartenders=True)
    except Exception as e:
        current_app.logger.error(f"Error al obtener empleados: {e}")
        employees = []
        flash("No se pudieron cargar los empleados desde la API. Contacta al administrador.", "error")
    
    return render_template(
        'seleccionar_bartender.html', 
        employees=employees, 
        current_bartender=session.get('bartender'),
        selected_employee_id=selected_employee_id,
        selected_employee_info=selected_employee_info
    )


@scanner_bp.route('/api/tickets/scan', methods=['POST'])
@rate_limit(max_requests=30, per_seconds=60)
def api_scan_ticket():
    """FASE 2: API para escanear ticket por QR token"""
    try:
        from flask import current_app
        from app.helpers.ticket_entrega_service import TicketEntregaService
        
        data = request.get_json() or {}
        qr_token = data.get('qr_token', '').strip()
        
        if not qr_token:
            return jsonify({'success': False, 'error': 'QR token requerido'}), 400
        
        # Obtener información del bartender de forma consistente
        is_admin = session.get('admin_logged_in', False)
        bartender_id = session.get('bartender_id')
        bartender_name = session.get('bartender', 'Desconocido')
        
        # Si es admin y no tiene bartender_id, crearlo
        if is_admin and not bartender_id:
            admin_username = session.get('admin_username', 'Admin')
            bartender_id = f"admin-{admin_username.lower()}"
            bartender_name = f"Admin: {admin_username}"
        
        # Si no hay bartender_id pero sí bartender, usar el nombre como ID temporal
        if not bartender_id and bartender_name:
            bartender_id = bartender_name
        
        scanner_id = request.headers.get('X-Scanner-Id') or bartender_id
        
        # Escanear ticket
        success, ticket_data, message = TicketEntregaService.scan_ticket(
            qr_token=qr_token,
            scanner_id=scanner_id,
            scanner_name=bartender_name
        )
        
        if not success:
            return jsonify({'success': False, 'error': message}), 404
        
        return jsonify({
            'success': True,
            'message': message,
            'ticket': ticket_data
        })
        
    except Exception as e:
        current_app.logger.error(f"Error al escanear ticket QR: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@scanner_bp.route('/api/tickets/<int:ticket_id>/deliver', methods=['POST'])
@rate_limit(max_requests=50, per_seconds=60)
def api_deliver_item(ticket_id):
    """FASE 2: API para entregar un item del ticket"""
    try:
        from flask import current_app
        from app.helpers.ticket_entrega_service import TicketEntregaService
        
        data = request.get_json() or {}
        item_id = data.get('item_id')
        qty_to_deliver = int(data.get('qty', 1))
        
        if not item_id:
            return jsonify({'success': False, 'error': 'item_id requerido'}), 400
        
        if qty_to_deliver <= 0:
            return jsonify({'success': False, 'error': 'Cantidad debe ser mayor a 0'}), 400
        
        # Obtener información del bartender de forma consistente
        is_admin = session.get('admin_logged_in', False)
        bartender_id = session.get('bartender_id')
        bartender_name = session.get('bartender', 'Desconocido')
        
        # Si es admin y no tiene bartender_id, crearlo
        if is_admin and not bartender_id:
            admin_username = session.get('admin_username', 'Admin')
            bartender_id = f"admin-{admin_username.lower()}"
            bartender_name = f"Admin: {admin_username}"
        
        # Si no hay bartender_id pero sí bartender, usar el nombre como ID temporal
        if not bartender_id and bartender_name:
            bartender_id = bartender_name
        
        # Entregar item
        success, message = TicketEntregaService.deliver_item(
            ticket_id=ticket_id,
            item_id=item_id,
            qty_to_deliver=qty_to_deliver,
            bartender_id=bartender_id,
            bartender_name=bartender_name
        )
        
        if not success:
            return jsonify({'success': False, 'error': message}), 400
        
        # Emitir evento SocketIO para actualizar "Últimas entregas"
        try:
            from app import socketio
            socketio.emit('delivery_update', {
                'ticket_id': ticket_id,
                'item_id': item_id,
                'qty_delivered': qty_to_deliver,
                'bartender_name': bartender_name,
                'timestamp': datetime.now().isoformat()
            }, namespace='/pos')
        except Exception as e:
            current_app.logger.warning(f"Error al emitir evento delivery_update: {e}")
        
        return jsonify({
            'success': True,
            'message': message
        })
        
    except Exception as e:
        current_app.logger.error(f"Error al entregar item: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@scanner_bp.route('/reset')
@scanner_bp.route('/logout')
def logout_bartender():
    """Cerrar sesión de bartender (alias: reset)"""
    bartender_name = session.get('bartender', 'Usuario')
    
    # Limpiar todas las variables de sesión relacionadas con bartender
    session.pop('bartender', None)
    session.pop('bartender_id', None)
    session.pop('bartender_first_name', None)
    session.pop('bartender_last_name', None)
    session.pop('barra', None)
    session.pop('last_activity', None)
    session.pop('selected_employee_id', None)
    session.pop('selected_employee_info', None)
    
    flash(f"Hasta luego, {bartender_name}!", "info")
    return redirect(url_for('scanner.seleccionar_bartender'))















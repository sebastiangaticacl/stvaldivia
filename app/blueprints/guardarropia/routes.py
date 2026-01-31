"""
Rutas para la gestión de Guardarropía
"""
from flask import render_template, request, redirect, session, url_for, flash, jsonify
from flask import current_app
from datetime import datetime
from sqlalchemy import not_
from app.application.services.service_factory import get_guardarropia_service
from app.application.dto.guardarropia_dto import (
    DepositItemRequest,
    RetrieveItemRequest,
    MarkLostRequest
)
from app.helpers.logger import get_logger
from app.helpers.pos_api import authenticate_employee
from app.helpers.puesto_validator import puede_abrir_puesto, obtener_empleados_habilitados_para_puesto
from app.helpers.session_manager import init_session
from app.helpers.motivational_messages import get_welcome_message, get_time_based_greeting

# Los blueprints se importan desde __init__.py
from . import guardarropia_bp, guardarropia_admin_bp

logger = get_logger(__name__)


def require_admin():
    """Verifica que el usuario esté autenticado como administrador"""
    if not session.get('admin_logged_in'):
        flash("Debes iniciar sesión como administrador.", "error")
        return redirect(url_for('auth.login_admin'))
    return None


def require_guardarropia_employee():
    """Verifica que el usuario esté autenticado como empleado de guardarropía"""
    if not session.get('guardarropia_logged_in'):
        flash("Debes iniciar sesión como empleado de guardarropía.", "error")
        return redirect(url_for('guardarropia.login'))
    return None


@guardarropia_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login de guardarropía - igual que las otras cajas"""
    # Limpiar sesión de caja regular si existe (para evitar conflictos)
    if session.get('pos_logged_in'):
        session.pop('pos_logged_in', None)
        session.pop('pos_employee_id', None)
        session.pop('pos_employee_name', None)
        session.pop('register_id', None)
        session.pop('register_name', None)
    
    if request.method == 'POST':
        pin = request.form.get('pin', '').strip()
        employee_id = request.form.get('employee_id')
        
        if not pin or not employee_id:
            flash("Debes ingresar tu PIN.", "error")
            employees = obtener_empleados_habilitados_para_puesto("guardarropia")
            return render_template('pos/login.html', employees=employees, puesto='guardarropia')
        
        employee = authenticate_employee(None, pin=pin, employee_id=employee_id)
        
        if employee:
            employee_id_str = str(employee["id"]) if employee.get("id") else None
            puede_acceder, mensaje_validacion, jornada_id = puede_abrir_puesto(employee_id_str, "guardarropia")
        
            if not puede_acceder:
                flash(mensaje_validacion, "error")
                employee_name = employee.get("name", "Desconocido")
                logger.warning(f"⚠️  Intento de acceso denegado a guardarropía: {employee_name} - {mensaje_validacion}")
                employees = obtener_empleados_habilitados_para_puesto("guardarropia")
                return render_template("pos/login.html", employees=employees, puesto='guardarropia')
            
            employee_id_str = str(employee['id']) if employee.get('id') else None
            session['guardarropia_employee_id'] = employee_id_str
            session['guardarropia_jornada_id'] = jornada_id
            session['guardarropia_employee_name'] = employee['name']
            session['guardarropia_logged_in'] = True
            # Guardar fecha/hora de login
            from datetime import datetime
            from app.helpers.timezone_utils import CHILE_TZ
            session['guardarropia_logged_in_at'] = datetime.now(CHILE_TZ).strftime('%Y-%m-%d %H:%M:%S')
            employee_name = employee.get("name", "Empleado")
            logger.info(f"✅ Login exitoso en guardarropía: {employee_name}")
            init_session()
            welcome_msg = f"{get_time_based_greeting()} {get_welcome_message(employee_name)}"
            flash(welcome_msg, "success")
            # Redirigir a POS de guardarropía
            return redirect(url_for('guardarropia.pos'))
        else:
            flash("PIN incorrecto. Intenta nuevamente.", "error")
    
    employees = obtener_empleados_habilitados_para_puesto("guardarropia")
    if not employees:
        # Verificar si hay un turno abierto
        from app.models.jornada_models import Jornada
        from datetime import datetime
        from app.helpers.timezone_utils import CHILE_TZ
        
        jornada_abierta = Jornada.query.filter_by(estado_apertura='abierto').order_by(
            Jornada.fecha_jornada.desc()
        ).first()
        
        if not jornada_abierta:
            logger.warning("⚠️ No hay turno abierto para Guardarropía")
            flash("No hay un turno abierto actualmente. Por favor, abre un turno desde el panel administrativo antes de acceder a Guardarropía.", "warning")
        else:
            logger.warning("⚠️ No hay empleados habilitados para Guardarropía en el turno actual")
            flash("No hay trabajadores asignados a Guardarropía en el turno actual. Por favor, asigna trabajadores a Guardarropía en la planilla del turno desde el panel administrativo.", "warning")
    return render_template('pos/login.html', employees=employees, puesto='guardarropia')


@guardarropia_bp.route('/')
def index():
    """Página principal de guardarropía - Muestra estadísticas si es admin, o redirige según autenticación"""
    # Si es administrador, mostrar dashboard con estadísticas
    if session.get('admin_logged_in'):
        try:
            service = get_guardarropia_service()
            
            # Obtener fecha del turno actual o fecha de hoy
            from app.application.services.service_factory import get_shift_service
            from datetime import datetime
            from app.helpers.timezone_utils import CHILE_TZ
            
            shift_service = get_shift_service()
            shift_status = shift_service.get_current_shift_status()
            
            if shift_status and shift_status.is_open:
                shift_date = shift_status.shift_date
            else:
                shift_date = datetime.now(CHILE_TZ).strftime('%Y-%m-%d')
            
            # Obtener estadísticas básicas
            stats = service.get_stats(shift_date=shift_date)
            
            # Obtener items depositados recientes
            from app.models.guardarropia_models import GuardarropiaItem
            from sqlalchemy import or_, desc
            
            recent_items = GuardarropiaItem.query.filter(
                GuardarropiaItem.status == 'deposited',
                or_(
                    GuardarropiaItem.notes.is_(None),
                    ~GuardarropiaItem.notes.like('%[ELIMINADO]%')
                )
            ).order_by(desc(GuardarropiaItem.deposited_at)).limit(10).all()
            
            return render_template(
                'guardarropia/admin_dashboard.html',
                stats=stats,
                recent_items=recent_items,
                shift_date=shift_date
            )
        except Exception as e:
            current_app.logger.error(f"Error en index admin de guardarropía: {e}", exc_info=True)
            flash(f'Error al cargar dashboard: {str(e)}', 'error')
            # Redirigir al informe de espacios como fallback
            return redirect(url_for('guardarropia_admin.informe_espacios'))
    
    # Si el empleado está autenticado y hay turno abierto, redirigir a POS
    if session.get('guardarropia_logged_in'):
        from app.application.services.service_factory import get_shift_service
        shift_service = get_shift_service()
        shift_status = shift_service.get_current_shift_status()
        
        if shift_status and shift_status.is_open:
            return redirect(url_for('guardarropia.pos'))
    
    # Si no está autenticado, redirigir a login
    if not session.get('guardarropia_logged_in'):
        return redirect(url_for('guardarropia.login'))
    
    try:
        service = get_guardarropia_service()
        
        # Obtener estadísticas
        stats = service.get_stats()
        
        # Obtener items depositados (no retirados)
        deposited_items = service.get_deposited_items()
        
        # Verificar estado del turno
        from app.application.services.service_factory import get_shift_service
        shift_service = get_shift_service()
        shift_status = shift_service.get_current_shift_status()
        
        return render_template(
            'guardarropia/index.html',
            stats=stats,
            deposited_items=deposited_items,
            shift_status=shift_status
        )
    except Exception as e:
        current_app.logger.error(f"Error en index de guardarropía: {e}", exc_info=True)
        flash(f"Error al cargar guardarropía: {str(e)}", "error")
        return redirect(url_for('guardarropia.login'))


@guardarropia_bp.route('/abrir-turno', methods=['GET', 'POST'])
def abrir_turno():
    """Abre un turno de guardarropía y redirige automáticamente a POS - Solo admin"""
    if require_admin():
        return require_admin()
    
    try:
        from app.application.services.service_factory import get_shift_service
        from app.application.dto.shift_dto import OpenShiftRequest
        from app.domain.exceptions import ShiftAlreadyOpenError
        
        shift_service = get_shift_service()
        shift_status = shift_service.get_current_shift_status()
        
        # Si ya hay turno abierto, redirigir directamente
        if shift_status.is_open:
            flash("Turno ya está abierto. Redirigiendo a guardarropía...", "info")
            return redirect(url_for('guardarropia.pos'))
        
        # Si es POST, abrir el turno
        if request.method == 'POST':
            opened_by = session.get('admin_user', 'admin')
            
            request_dto = OpenShiftRequest(
                fiesta_nombre=request.form.get('fiesta_nombre', 'Guardarropía'),
                opened_by=opened_by,
                djs='',
                barras_disponibles=[],
                bartenders=[],
                cashiers=[]
            )
            
            success, message = shift_service.open_shift(request_dto)
            
            if success:
                flash(f"✅ {message}", "success")
                return redirect(url_for('guardarropia.pos'))
            else:
                flash(f"❌ {message}", "error")
                return render_template('guardarropia/abrir_turno.html')
        
        # Si es GET, mostrar formulario para abrir turno
        return render_template('guardarropia/abrir_turno.html')
        
    except ShiftAlreadyOpenError:
        flash("Ya hay un turno abierto. Redirigiendo a guardarropía...", "info")
        return redirect(url_for('guardarropia.pos'))
    except Exception as e:
        current_app.logger.error(f"Error al abrir turno de guardarropía: {e}", exc_info=True)
        flash(f"Error inesperado: {str(e)}", "error")
        return redirect(url_for('guardarropia.index'))


@guardarropia_bp.route('/pos', methods=['GET'])
def pos():
    """Interfaz POS para venta de espacios de guardarropía"""
    try:
        # Permitir acceso a administradores, cajeros y empleados de guardarropía
        is_admin = session.get('admin_logged_in', False)
        is_cashier = session.get('pos_logged_in', False)  # Los cajeros operan las cajas
        is_employee = session.get('guardarropia_logged_in', False)
        
        current_app.logger.info(f"🔍 Acceso a POS guardarropía - Admin: {is_admin}, Cajero: {is_cashier}, Empleado: {is_employee}")
        
        if not is_admin and not is_cashier and not is_employee:
            # Si no es ni admin ni empleado, requerir login
            current_app.logger.warning("⚠️ Intento de acceso sin autenticación")
            if require_guardarropia_employee():
                return require_guardarropia_employee()
            is_employee = True  # Si pasó la validación, es empleado
        
        # Obtener estado del turno
        from app.application.services.service_factory import get_shift_service
        shift_service = get_shift_service()
        shift_status = shift_service.get_current_shift_status()
        
        current_app.logger.info(f"📊 Estado del turno - Abierto: {shift_status.is_open if shift_status else False}")
        
        # Verificar que hay turno abierto (solo para empleados, admins pueden ver siempre)
        if not is_admin:
            if not shift_status or not shift_status.is_open:
                flash("No hay un turno abierto actualmente.", "warning")
                if is_employee:
                    return redirect(url_for('guardarropia.login'))
        
        # Obtener estadísticas de espacios para mostrar en el informe
        stats = None
        occupied_clusters = []
        available_clusters = []
        try:
            service = get_guardarropia_service()
            stats = service.get_stats()
            occupied_clusters = service.get_occupied_clusters()
            available_clusters = service.get_available_clusters(count=90)
        except Exception as e:
            current_app.logger.warning(f"No se pudieron obtener estadísticas de espacios: {e}")
            # Crear stats por defecto
            stats = type('Stats', (), {
                'spaces_occupied': 0,
                'spaces_available': 90,
                'total_deposited': 0,
                'total_retrieved': 0,
                'currently_stored': 0
            })()
            available_clusters = list(range(1, 91))
        
        # Convertir shift_status a diccionario si es un objeto (para compatibilidad con templates)
        shift_status_dict = None
        if shift_status:
            if hasattr(shift_status, 'to_dict'):
                shift_status_dict = shift_status.to_dict()
            else:
                # Si es un objeto ShiftStatus, convertir manualmente
                shift_status_dict = {
                    'is_open': shift_status.is_open,
                    'shift_date': shift_status.shift_date,
                    'opened_at': shift_status.opened_at,
                    'closed_at': shift_status.closed_at,
                    'opened_by': shift_status.opened_by,
                    'closed_by': shift_status.closed_by,
                    'fiesta_nombre': shift_status.fiesta_nombre,
                    'djs': shift_status.djs,
                    'barras_disponibles': shift_status.barras_disponibles if hasattr(shift_status, 'barras_disponibles') else [],
                    'bartenders': shift_status.bartenders if hasattr(shift_status, 'bartenders') else []
                }
        
        # Renderizar template
        return render_template(
            'guardarropia/pos.html', 
            is_admin=is_admin or is_cashier,  # Tratar cajeros como admins para la vista
            shift_status=shift_status_dict,  # Pasar como diccionario
            stats=stats,
            total_spaces=90,
            occupied_clusters=occupied_clusters,
            available_clusters=available_clusters
        )
    except Exception as e:
        current_app.logger.error(f"❌ Error en ruta POS guardarropía: {e}", exc_info=True)
        flash(f"Error al cargar POS: {str(e)}", "error")
        # Redirigir según el tipo de usuario
        if session.get('guardarropia_logged_in'):
            return redirect(url_for('guardarropia.index'))
        elif session.get('admin_logged_in') or session.get('pos_logged_in'):
            return redirect(url_for('routes.admin_dashboard'))
        else:
            return redirect(url_for('guardarropia.login'))


@guardarropia_bp.route('/confirmar-pago', methods=['POST'])
def confirmar_pago():
    """Paso intermedio: Confirmar pago antes de depositar e imprimir"""
    if require_guardarropia_employee():
        return require_guardarropia_employee()
    
    try:
        # Obtener datos del formulario
        customer_name = request.form.get('customer_name', '').strip()
        customer_phone = request.form.get('customer_phone', '').strip()
        description = request.form.get('description', '').strip() or None
        notes = request.form.get('notes', '').strip() or None
        payment_type = request.form.get('payment_type', 'cash').strip() or 'cash'
        clusters = int(request.form.get('clusters', 1) or 1)
        if clusters < 1:
            clusters = 1
        precio_unitario = 500.0
        price = precio_unitario * clusters
        
        # Validar campos requeridos
        if not customer_name:
            flash("El nombre del cliente es requerido", "error")
            return redirect(url_for('guardarropia.pos'))
        
        if not customer_phone:
            flash("El teléfono del cliente es requerido", "error")
            return redirect(url_for('guardarropia.pos'))
        
        if not payment_type:
            flash("Debes seleccionar un método de pago", "error")
            return redirect(url_for('guardarropia.pos'))
        
        # Mostrar página de confirmación
        return render_template(
            'guardarropia/confirmar_pago.html',
            customer_name=customer_name,
            customer_phone=customer_phone,
            description=description,
            notes=notes,
            payment_type=payment_type,
            clusters=clusters,
            precio_unitario=precio_unitario,
            price=price
        )
    except Exception as e:
        current_app.logger.error(f"Error en confirmar pago: {e}", exc_info=True)
        flash(f"Error inesperado: {str(e)}", "error")
        return redirect(url_for('guardarropia.pos'))


@guardarropia_bp.route('/depositar', methods=['GET', 'POST'])
def depositar():
    """Depositar una prenda en guardarropía (después de confirmar pago)"""
    # Permitir acceso a administradores, cajeros y empleados de guardarropía
    is_admin = session.get('admin_logged_in', False)
    is_cashier = session.get('pos_logged_in', False)  # Los cajeros operan las cajas
    is_employee = session.get('guardarropia_logged_in', False)
    
    if not is_admin and not is_cashier and not is_employee:
        if require_guardarropia_employee():
            return require_guardarropia_employee()
    
    if request.method == 'POST':
        try:
            service = get_guardarropia_service()
            # Obtener nombre del usuario (priorizar guardarropía, luego cajero, luego admin)
            deposited_by = (
                session.get('guardarropia_employee_name') or 
                session.get('pos_employee_name') or  # Nombre del cajero
                session.get('admin_username') or 
                session.get('admin_user') or 
                'Cajero'
            )
            
            # Obtener turno actual para asociar
            from app.application.services.service_factory import get_shift_service
            shift_service = get_shift_service()
            shift_status = shift_service.get_current_shift_status()
            shift_date = shift_status.shift_date if shift_status.is_open else None
            
            # Obtener cantidad de clusters (por defecto 1)
            clusters = int(request.form.get('clusters', 1) or 1)
            if clusters < 1:
                clusters = 1
            
            # Precio unitario fijo de $500
            precio_unitario = 500.0
            price = precio_unitario * clusters  # Precio total
            
            # Tipo de pago (viene del formulario de confirmación)
            payment_type = request.form.get('payment_type', 'cash').strip() or 'cash'
            
            # Nombre y teléfono (vienen del formulario de confirmación)
            customer_name = request.form.get('customer_name', '').strip()
            customer_phone = request.form.get('customer_phone', '').strip()
            
            # Validar campos requeridos
            if not customer_name:
                flash("El nombre del cliente es requerido", "error")
                return redirect(url_for('guardarropia.pos'))
            
            if not customer_phone:
                flash("El teléfono del cliente es requerido", "error")
                return redirect(url_for('guardarropia.pos'))
            
            request_dto = DepositItemRequest(
                ticket_code=None,  # Se genera automáticamente
                description=request.form.get('description', '').strip() or None,
                customer_name=customer_name,
                customer_phone=customer_phone,
                notes=request.form.get('notes', '').strip() or None,
                shift_date=shift_date,
                price=price,  # Precio total
                clusters=clusters,  # Cantidad de clusters
                payment_type=payment_type
            )
            
            success, message, item = service.deposit_item(request_dto, deposited_by)
            
            if success:
                # Generar e imprimir ticket con QR
                try:
                    from app.infrastructure.services.ticket_printer_service import TicketPrinterService
                    printer_service = TicketPrinterService()
                    
                    # Generar ticket específico para guardarropía
                    ticket_img = printer_service.generate_guardarropia_ticket(
                        ticket_code=item.ticket_code,
                        customer_name=customer_name,
                        customer_phone=customer_phone,
                        description=item.description,
                        price=float(price),
                        payment_type=payment_type,
                        deposited_at=item.deposited_at.isoformat() if item.deposited_at else None
                    )
                    
                    # Guardar y imprimir
                    import tempfile
                    import os
                    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
                    ticket_img.save(temp_file.name, 'PNG')
                    temp_file.close()
                    
                    # Imprimir
                    printer_service._print_macos(temp_file.name)
                    
                    # Limpiar
                    try:
                        os.remove(temp_file.name)
                    except:
                        pass
                        
                except Exception as e:
                    current_app.logger.error(f"Error al imprimir ticket: {e}", exc_info=True)
                    # Continuar aunque falle la impresión
                
                # Redirigir a página de éxito con ticket
                return redirect(url_for('guardarropia.ticket_success', ticket_code=item.ticket_code))
            else:
                flash(message, "error")
                return render_template('guardarropia/depositar.html')
                
        except Exception as e:
            current_app.logger.error(f"Error al depositar item: {e}", exc_info=True)
            flash(f"Error inesperado: {str(e)}", "error")
            return redirect(url_for('guardarropia.pos'))
    
    # Si es GET, redirigir a POS
    return redirect(url_for('guardarropia.pos'))


@guardarropia_bp.route('/retirar', methods=['GET', 'POST'])
def retirar():
    """Retirar una prenda de guardarropía"""
    # Permitir acceso a administradores, cajeros y empleados de guardarropía
    is_admin = session.get('admin_logged_in', False)
    is_cashier = session.get('pos_logged_in', False)  # Los cajeros operan las cajas
    is_employee = session.get('guardarropia_logged_in', False)
    
    if not is_admin and not is_cashier and not is_employee:
        if require_guardarropia_employee():
            return require_guardarropia_employee()
    
    if request.method == 'POST':
        try:
            # FASE 3: Intentar primero con QR token, luego con ticket_code legacy
            qr_token = request.form.get('qr_token', '').strip()
            ticket_code = request.form.get('ticket_code', '').strip().upper()
            
            if qr_token:
                # Usar sistema nuevo con QR token
                from app.helpers.guardarropia_ticket_service import GuardarropiaTicketService
                
                retrieved_by = (
                    session.get('guardarropia_employee_name') or 
                    session.get('pos_employee_name') or 
                    session.get('admin_username') or 
                    session.get('admin_user') or 
                    'Empleado'
                )
                
                retrieved_by_id = (
                    session.get('guardarropia_employee_id') or 
                    session.get('pos_employee_id') or 
                    session.get('admin_username') or 
                    'admin'
                )
                
                # Escanear ticket
                success_scan, ticket_data, scan_msg = GuardarropiaTicketService.scan_ticket(
                    qr_token=qr_token,
                    actor_user_id=str(retrieved_by_id),
                    actor_name=retrieved_by
                )
                
                if not success_scan:
                    flash(scan_msg, "error")
                    return render_template('guardarropia/retirar.html')
                
                # Retirar item
                success, message = GuardarropiaTicketService.check_out_item(
                    ticket_id=ticket_data['ticket']['id'],
                    actor_user_id=str(retrieved_by_id),
                    actor_name=retrieved_by
                )
                
                if success:
                    flash(message, "success")
                    return redirect(url_for('guardarropia.index'))
                else:
                    flash(message, "error")
                    return render_template('guardarropia/retirar.html')
            else:
                # Sistema legacy: usar ticket_code
                service = get_guardarropia_service()
                retrieved_by = (
                    session.get('guardarropia_employee_name') or 
                    session.get('pos_employee_name') or 
                    session.get('admin_username') or 
                    session.get('admin_user') or 
                    'Empleado'
                )
                
                request_dto = RetrieveItemRequest(
                    ticket_code=ticket_code,
                    retrieved_by=retrieved_by
                )
                
                success, message, item = service.retrieve_item(request_dto)
                
                if success:
                    flash(message, "success")
                    return redirect(url_for('guardarropia.index'))
                else:
                    flash(message, "error")
                    return render_template('guardarropia/retirar.html')
                
        except Exception as e:
            current_app.logger.error(f"Error al retirar item: {e}", exc_info=True)
            flash(f"Error inesperado: {str(e)}", "error")
            return render_template('guardarropia/retirar.html')
    
    return render_template('guardarropia/retirar.html')


@guardarropia_bp.route('/api/buscar-ticket', methods=['POST'])
def api_buscar_ticket():
    """API: Buscar un ticket sin retirarlo (solo para mostrar información)"""
    # Permitir acceso a administradores, cajeros y empleados de guardarropía
    is_admin = session.get('admin_logged_in', False)
    is_cashier = session.get('pos_logged_in', False)
    is_employee = session.get('guardarropia_logged_in', False)
    
    if not is_admin and not is_cashier and not is_employee:
        return jsonify({'success': False, 'error': 'No autorizado'}), 401
    
    try:
        data = request.get_json()
        ticket_code = data.get('ticket_code', '').strip().upper()
        
        if not ticket_code:
            return jsonify({'success': False, 'error': 'Código de ticket requerido'}), 400
        
        from app.models.guardarropia_models import GuardarropiaItem
        
        # Buscar el item directamente en la BD para obtener todos los campos
        item = GuardarropiaItem.query.filter_by(ticket_code=ticket_code).first()
        
        if not item:
            return jsonify({
                'success': False,
                'error': f'No se encontró un ticket con el código {ticket_code}'
            }), 404
        
        # Verificar estado
        if item.is_retrieved():
            return jsonify({
                'success': False,
                'error': f'El ticket {ticket_code} ya fue retirado',
                'item': item.to_dict()
            }), 400
        
        if item.is_lost():
            return jsonify({
                'success': False,
                'error': f'El ticket {ticket_code} está marcado como perdido',
                'item': item.to_dict()
            }), 400
        
        # Retornar información completa del ticket
        return jsonify({
            'success': True,
            'item': item.to_dict()
        })
        
    except Exception as e:
        current_app.logger.error(f"Error al buscar ticket: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@guardarropia_bp.route('/buscar', methods=['GET', 'POST'])
def buscar():
    """Buscar un item por código de ticket"""
    if require_guardarropia_employee():
        return require_guardarropia_employee()
    
    item = None
    if request.method == 'POST':
        try:
            service = get_guardarropia_service()
            ticket_code = request.form.get('ticket_code', '').strip().upper()
            
            if ticket_code:
                item = service.get_item_by_ticket(ticket_code)
                if not item:
                    flash(f"No se encontró un item con el código {ticket_code}", "error")
            else:
                flash("Por favor ingresa un código de ticket", "error")
                
        except Exception as e:
            current_app.logger.error(f"Error al buscar item: {e}", exc_info=True)
            flash(f"Error inesperado: {str(e)}", "error")
    
    return render_template('guardarropia/buscar.html', item=item)


@guardarropia_bp.route('/listar')
def listar():
    """Listar todos los items de guardarropía"""
    if require_guardarropia_employee():
        return require_guardarropia_employee()
    
    try:
        service = get_guardarropia_service()
        
        # Obtener parámetros de filtro
        status = request.args.get('status', '')
        shift_date = request.args.get('shift_date', '')
        
        # Obtener items
        items = service.get_all_items(
            status=status if status else None,
            shift_date=shift_date if shift_date else None
        )
        
        # Obtener estadísticas
        stats = service.get_stats(shift_date=shift_date if shift_date else None)
        
        return render_template(
            'guardarropia/listar.html',
            items=items,
            stats=stats,
            current_status=status,
            current_shift_date=shift_date
        )
    except Exception as e:
        current_app.logger.error(f"Error al listar items: {e}", exc_info=True)
        flash(f"Error al cargar items: {str(e)}", "error")
        return redirect(url_for('guardarropia.index'))


@guardarropia_bp.route('/marcar_perdido', methods=['POST'])
def marcar_perdido():
    """Marcar un item como perdido (API endpoint)"""
    if require_guardarropia_employee():
        return jsonify({'success': False, 'error': 'No autorizado'}), 401
    
    try:
        service = get_guardarropia_service()
        data = request.get_json()
        
        request_dto = MarkLostRequest(
            ticket_code=data.get('ticket_code', '').strip().upper(),
            notes=data.get('notes', '').strip() or None
        )
        
        success, message, item = service.mark_as_lost(request_dto)
        
        if success:
            return jsonify({
                'success': True,
                'message': message,
                'item': item.to_dict() if item else None
            })
        else:
            return jsonify({
                'success': False,
                'error': message
            }), 400
            
    except Exception as e:
        current_app.logger.error(f"Error al marcar item como perdido: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f"Error inesperado: {str(e)}"
        }), 500


@guardarropia_bp.route('/ticket/<ticket_code>')
def ticket_success(ticket_code):
    """Muestra el ticket generado con QR"""
    # Permitir acceso a administradores, cajeros y empleados de guardarropía
    is_admin = session.get('admin_logged_in', False)
    is_cashier = session.get('pos_logged_in', False)  # Los cajeros operan las cajas
    is_employee = session.get('guardarropia_logged_in', False)
    
    if not is_admin and not is_cashier and not is_employee:
        if require_guardarropia_employee():
            return require_guardarropia_employee()
    
    try:
        service = get_guardarropia_service()
        item = service.get_item_by_ticket(ticket_code)
        
        if not item:
            flash(f"No se encontró el ticket {ticket_code}", "error")
            return redirect(url_for('guardarropia.index'))
        
        # Generar QR code para mostrar en pantalla
        import qrcode
        import base64
        import io
        
        # FASE 3: Buscar ticket QR asociado para usar token seguro
        qr_token = None
        ticket_qr = None
        if hasattr(item, 'ticket_qr') and item.ticket_qr:
            ticket_qr = item.ticket_qr
            qr_token = ticket_qr.qr_token
        else:
            # Si no existe ticket QR, usar ticket_code (legacy)
            qr_token = item.ticket_code
        
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4
        )
        qr.add_data(qr_token)  # El QR contiene el token, no el display_code
        qr.make(fit=True)
        
        qr_img = qr.make_image(fill_color="black", back_color="white")
        
        # Convertir a base64 para mostrar en HTML
        img_buffer = io.BytesIO()
        qr_img.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        qr_base64 = base64.b64encode(img_buffer.getvalue()).decode()
        
        return render_template(
            'guardarropia/ticket_success.html',
            item=item,
            qr_code=qr_base64,
            qr_token=qr_token,
            ticket_qr=ticket_qr
        )
    except Exception as e:
        current_app.logger.error(f"Error al mostrar ticket: {e}", exc_info=True)
        flash(f"Error al mostrar ticket: {str(e)}", "error")
        return redirect(url_for('guardarropia.index'))


@guardarropia_admin_bp.route('/ticket/<ticket_code>')
@guardarropia_bp.route('/ticket/<ticket_code>')  # También disponible para trabajadores
def admin_ticket_detail(ticket_code):
    """Muestra el detalle del ticket para administradores, cajeros y empleados de guardarropía"""
    # Permitir acceso a administradores, cajeros y empleados de guardarropía
    is_admin = session.get('admin_logged_in', False)
    is_cashier = session.get('pos_logged_in', False)  # Los cajeros operan las cajas
    is_employee = session.get('guardarropia_logged_in', False)
    
    if not is_admin and not is_cashier and not is_employee:
        # Si no está autenticado, redirigir al login apropiado
        flash("Debes iniciar sesión para ver este ticket.", "error")
        return redirect(url_for('auth.login_admin'))
    
    try:
        service = get_guardarropia_service()
        item = service.get_item_by_ticket(ticket_code)
        
        if not item:
            flash(f"No se encontró el ticket {ticket_code}", "error")
            return redirect(url_for('routes.admin_dashboard'))
        
        # Generar QR code para mostrar en pantalla
        import qrcode
        import base64
        import io
        
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4
        )
        qr.add_data(ticket_code)
        qr.make(fit=True)
        
        qr_img = qr.make_image(fill_color="black", back_color="white")
        
        # Convertir a base64 para mostrar en HTML
        img_buffer = io.BytesIO()
        qr_img.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        qr_base64 = base64.b64encode(img_buffer.getvalue()).decode()
        
        return render_template(
            'guardarropia/ticket_success.html',
            item=item,
            qr_code=qr_base64,
            is_admin=True
        )
    except Exception as e:
        current_app.logger.error(f"Error al mostrar ticket admin: {e}", exc_info=True)
        flash(f"Error al mostrar ticket: {str(e)}", "error")
        # Redirigir según el tipo de usuario
        if session.get('guardarropia_logged_in'):
            return redirect(url_for('guardarropia.index'))
        elif session.get('admin_logged_in') or session.get('pos_logged_in'):
            return redirect(url_for('routes.admin_dashboard'))
        else:
            return redirect(url_for('guardarropia.login'))


@guardarropia_admin_bp.route('/')
def admin_index():
    """Página principal de administración de guardarropía con estadísticas de rendimiento y recaudaciones"""
    # Permitir acceso sin login para mostrar estadísticas (pero requerir login para acciones)
    # if require_admin():
    #     return require_admin()
    
    try:
        service = get_guardarropia_service()
        
        # Obtener fecha del turno actual o fecha de hoy
        from app.application.services.service_factory import get_shift_service
        from datetime import datetime, timedelta
        from app.helpers.timezone_utils import CHILE_TZ
        from sqlalchemy import func, or_, desc
        from decimal import Decimal
        
        shift_service = get_shift_service()
        shift_status = shift_service.get_current_shift_status()
        
        # Obtener información del turno actual
        jornada_info = None
        if shift_status and shift_status.is_open:
            shift_date = shift_status.shift_date
            # Obtener información completa de la jornada
            from app.models.jornada_models import Jornada
            jornada_info = Jornada.query.filter_by(
                fecha_jornada=shift_date,
                estado_apertura='abierto'
            ).first()
        else:
            shift_date = datetime.now(CHILE_TZ).strftime('%Y-%m-%d')
        
        # Calcular duración del turno y horas de operación
        turno_duracion = None
        horas_operacion = None
        turno_cruza_medianoche = False
        
        if jornada_info:
            hora_apertura = jornada_info.horario_apertura_programado or '22:00'
            hora_cierre = jornada_info.horario_cierre_programado or '04:00'
            fecha_cierre = jornada_info.fecha_cierre_programada or shift_date
            
            # Parsear horas
            try:
                hora_ap = int(hora_apertura.split(':')[0])
                min_ap = int(hora_apertura.split(':')[1]) if ':' in hora_apertura and len(hora_apertura.split(':')) > 1 else 0
                hora_ci = int(hora_cierre.split(':')[0])
                min_ci = int(hora_cierre.split(':')[1]) if ':' in hora_cierre and len(hora_cierre.split(':')) > 1 else 0
                
                # Verificar si cruza medianoche (usando fecha_cierre_programada si está disponible)
                if fecha_cierre != shift_date:
                    turno_cruza_medianoche = True
                    # Calcular duración cruzando medianoche
                    horas_hasta_medianoche = 24 - hora_ap - (min_ap / 60)
                    horas_desde_medianoche = hora_ci + (min_ci / 60)
                    duracion_horas = horas_hasta_medianoche + horas_desde_medianoche
                    turno_duracion = f"{int(duracion_horas)}h {int((duracion_horas % 1) * 60)}m"
                    horas_operacion = f"{hora_apertura} (día {shift_date}) - {hora_cierre} (día {fecha_cierre})"
                elif hora_ci < hora_ap or (hora_ci == hora_ap and min_ci < min_ap):
                    # Si no hay fecha_cierre pero los horarios indican cruce de medianoche
                    turno_cruza_medianoche = True
                    horas_hasta_medianoche = 24 - hora_ap - (min_ap / 60)
                    horas_desde_medianoche = hora_ci + (min_ci / 60)
                    duracion_horas = horas_hasta_medianoche + horas_desde_medianoche
                    turno_duracion = f"{int(duracion_horas)}h {int((duracion_horas % 1) * 60)}m"
                    horas_operacion = f"{hora_apertura} (día {shift_date}) - {hora_cierre} (día siguiente)"
                else:
                    # Turno normal sin cruzar medianoche
                    duracion_horas = (hora_ci - hora_ap) + ((min_ci - min_ap) / 60)
                    turno_duracion = f"{int(duracion_horas)}h {int((duracion_horas % 1) * 60)}m"
                    horas_operacion = f"{hora_apertura} - {hora_cierre} (día {shift_date})"
            except Exception as e:
                current_app.logger.warning(f"Error al calcular duración del turno: {e}")
                turno_duracion = "N/A"
                horas_operacion = f"{hora_apertura} - {hora_cierre}"
        
        # Obtener estadísticas básicas
        stats = service.get_stats(shift_date=shift_date)
        
        # Obtener items depositados recientes (sin duplicados por ticket_code)
        from app.models.guardarropia_models import GuardarropiaItem
        from app.models import db
        
        # Obtener items únicos por ticket_code (tomar el más reciente de cada ticket)
        # Usar subquery para obtener el ID máximo de cada ticket_code
        from sqlalchemy import func
        subquery = db.session.query(
            GuardarropiaItem.ticket_code,
            func.max(GuardarropiaItem.id).label('max_id')
        ).filter(
            GuardarropiaItem.status == 'deposited',
            or_(
                GuardarropiaItem.notes.is_(None),
                ~GuardarropiaItem.notes.like('%[ELIMINADO]%')
            )
        ).group_by(GuardarropiaItem.ticket_code).subquery()
        
        # Obtener los items completos usando los IDs únicos
        recent_items = GuardarropiaItem.query.join(
            subquery,
            GuardarropiaItem.id == subquery.c.max_id
        ).order_by(desc(GuardarropiaItem.deposited_at)).limit(10).all()
        
        # ========== ESTADÍSTICAS DE RENDIMIENTO Y RECAUDACIONES ==========
        
        # 1. Recaudaciones de guardarropía (ventas POS relacionadas)
        from app.models.pos_models import PosSale, PosSaleItem
        
        # Obtener ventas de guardarropía (registro_id = 'GUARDARROPIA' o similar)
        guardarropia_sales = PosSale.query.filter(
            or_(
                PosSale.register_id.like('%GUARDARROPIA%'),
                PosSale.register_name.like('%Guardarropía%'),
                PosSale.register_name.like('%guardarropía%')
            )
        ).filter(PosSale.shift_date >= (datetime.now(CHILE_TZ) - timedelta(days=30)).strftime('%Y-%m-%d')).all()
        
        # Recaudación total de guardarropía (últimos 30 días)
        total_revenue_30d = sum(float(sale.total_amount) for sale in guardarropia_sales)
        
        # Recaudación del día/turno actual
        guardarropia_sales_today = [s for s in guardarropia_sales if s.shift_date == shift_date]
        revenue_today = sum(float(sale.total_amount) for sale in guardarropia_sales_today)
        
        # Recaudación por método de pago (hoy)
        revenue_cash_today = sum(float(sale.payment_cash) for sale in guardarropia_sales_today)
        revenue_debit_today = sum(float(sale.payment_debit) for sale in guardarropia_sales_today)
        revenue_credit_today = sum(float(sale.payment_credit) for sale in guardarropia_sales_today)
        
        # 2. Métricas de rendimiento
        # Items depositados hoy
        items_deposited_today = GuardarropiaItem.query.filter(
            GuardarropiaItem.shift_date == shift_date,
            GuardarropiaItem.status == 'deposited',
            or_(
                GuardarropiaItem.notes.is_(None),
                ~GuardarropiaItem.notes.like('%[ELIMINADO]%')
            )
        ).count()
        
        # Items retirados hoy
        items_retrieved_today = GuardarropiaItem.query.filter(
            GuardarropiaItem.shift_date == shift_date,
            GuardarropiaItem.status == 'retrieved'
        ).count()
        
        # Tasa de retiro (porcentaje de items retirados vs depositados)
        retrieval_rate = (items_retrieved_today / items_deposited_today * 100) if items_deposited_today > 0 else 0
        
        # 3. Comparativa con días anteriores
        fecha_ayer = (datetime.now(CHILE_TZ) - timedelta(days=1)).strftime('%Y-%m-%d')
        fecha_semana_pasada = (datetime.now(CHILE_TZ) - timedelta(days=7)).strftime('%Y-%m-%d')
        
        # Items depositados ayer
        items_deposited_yesterday = GuardarropiaItem.query.filter(
            GuardarropiaItem.shift_date == fecha_ayer,
            GuardarropiaItem.status == 'deposited',
            or_(
                GuardarropiaItem.notes.is_(None),
                ~GuardarropiaItem.notes.like('%[ELIMINADO]%')
            )
        ).count()
        
        # Recaudación ayer
        guardarropia_sales_yesterday = [s for s in guardarropia_sales if s.shift_date == fecha_ayer]
        revenue_yesterday = sum(float(sale.total_amount) for sale in guardarropia_sales_yesterday)
        
        # Variación porcentual
        variation_items = ((items_deposited_today - items_deposited_yesterday) / items_deposited_yesterday * 100) if items_deposited_yesterday > 0 else 0
        variation_revenue = ((revenue_today - revenue_yesterday) / revenue_yesterday * 100) if revenue_yesterday > 0 else 0
        
        # 4. Métricas de ocupación
        occupied_clusters = service.get_occupied_cluster_numbers(shift_date=shift_date)
        total_clusters = 90
        occupancy_rate = (len(occupied_clusters) / total_clusters * 100) if total_clusters > 0 else 0
        
        # 5. Promedio de precio por item
        avg_price_per_item = revenue_today / items_deposited_today if items_deposited_today > 0 else 0
        
        # 6. Estadísticas de la última semana
        fecha_7_dias_atras = (datetime.now(CHILE_TZ) - timedelta(days=7)).strftime('%Y-%m-%d')
        items_last_7_days = GuardarropiaItem.query.filter(
            GuardarropiaItem.shift_date >= fecha_7_dias_atras,
            GuardarropiaItem.status == 'deposited',
            or_(
                GuardarropiaItem.notes.is_(None),
                ~GuardarropiaItem.notes.like('%[ELIMINADO]%')
            )
        ).count()
        
        guardarropia_sales_last_7d = [s for s in guardarropia_sales if s.shift_date >= fecha_7_dias_atras]
        revenue_last_7d = sum(float(sale.total_amount) for sale in guardarropia_sales_last_7d)
        
        # Promedio diario últimos 7 días
        avg_daily_items_7d = items_last_7_days / 7 if items_last_7_days > 0 else 0
        avg_daily_revenue_7d = revenue_last_7d / 7 if revenue_last_7d > 0 else 0
        
        # 7. Items pendientes de retiro
        items_pending = GuardarropiaItem.query.filter(
            GuardarropiaItem.status == 'deposited',
            or_(
                GuardarropiaItem.notes.is_(None),
                ~GuardarropiaItem.notes.like('%[ELIMINADO]%')
            )
        ).count()
        
        # ========== ANÁLISIS DE UTILIDAD Y HORAS PEAK ==========
        
        # 1. Análisis de horas peak (últimos 30 días)
        from collections import defaultdict
        items_por_hora = defaultdict(int)
        ingresos_por_hora = defaultdict(float)
        
        items_30_dias = GuardarropiaItem.query.filter(
            GuardarropiaItem.deposited_at >= (datetime.now(CHILE_TZ) - timedelta(days=30))
        ).all()
        
        for item in items_30_dias:
            if item.deposited_at:
                hora = item.deposited_at.hour
                items_por_hora[hora] += 1
                if item.price:
                    ingresos_por_hora[hora] += float(item.price)
        
        # Encontrar horas peak
        hora_peak_items = max(items_por_hora.items(), key=lambda x: x[1])[0] if items_por_hora else None
        hora_peak_revenue = max(ingresos_por_hora.items(), key=lambda x: x[1])[0] if ingresos_por_hora else None
        
        # 2. Análisis de utilidad
        # Calcular métricas de eficiencia
        items_no_retirados_count = GuardarropiaItem.query.filter(
            GuardarropiaItem.marked_unretrieved_at.isnot(None)
        ).count()
        
        tasa_no_retiro = (items_no_retirados_count / items_deposited_today * 100) if items_deposited_today > 0 else 0
        
        # Ingresos por item promedio
        revenue_per_item = revenue_today / items_deposited_today if items_deposited_today > 0 else 0
        
        # Eficiencia de espacio (ingresos por espacio ocupado)
        revenue_per_space = revenue_today / len(occupied_clusters) if len(occupied_clusters) > 0 else 0
        
        # 3. Análisis de utilidad del servicio
        # Calcular score de utilidad (0-100)
        utilidad_score = 0
        utilidad_factores = []
        
        # Factor 1: Tasa de retiro (30 puntos)
        if retrieval_rate >= 80:
            utilidad_score += 30
            utilidad_factores.append(("Tasa de retiro excelente", 30))
        elif retrieval_rate >= 60:
            utilidad_score += 20
            utilidad_factores.append(("Tasa de retiro buena", 20))
        elif retrieval_rate >= 40:
            utilidad_score += 10
            utilidad_factores.append(("Tasa de retiro regular", 10))
        else:
            utilidad_factores.append(("Tasa de retiro baja", 0))
        
        # Factor 2: Ocupación (20 puntos)
        if occupancy_rate >= 70:
            utilidad_score += 20
            utilidad_factores.append(("Alta ocupación", 20))
        elif occupancy_rate >= 40:
            utilidad_score += 15
            utilidad_factores.append(("Ocupación moderada", 15))
        elif occupancy_rate >= 20:
            utilidad_score += 10
            utilidad_factores.append(("Ocupación baja", 10))
        else:
            utilidad_factores.append(("Ocupación muy baja", 0))
        
        # Factor 3: Ingresos (30 puntos)
        if revenue_today >= 50000:
            utilidad_score += 30
            utilidad_factores.append(("Ingresos altos", 30))
        elif revenue_today >= 20000:
            utilidad_score += 20
            utilidad_factores.append(("Ingresos moderados", 20))
        elif revenue_today >= 10000:
            utilidad_score += 10
            utilidad_factores.append(("Ingresos bajos", 10))
        else:
            utilidad_factores.append(("Ingresos muy bajos", 0))
        
        # Factor 4: Prendas no retiradas (20 puntos - negativo)
        if tasa_no_retiro <= 5:
            utilidad_score += 20
            utilidad_factores.append(("Pocas prendas no retiradas", 20))
        elif tasa_no_retiro <= 15:
            utilidad_score += 10
            utilidad_factores.append(("Algunas prendas no retiradas", 10))
        else:
            utilidad_factores.append(("Muchas prendas no retiradas", 0))
        
        # Determinar si el servicio es útil
        if utilidad_score >= 70:
            servicio_util = "Muy útil"
            servicio_color = "#4caf50"
        elif utilidad_score >= 50:
            servicio_util = "Útil"
            servicio_color = "#2196f3"
        elif utilidad_score >= 30:
            servicio_util = "Regular"
            servicio_color = "#ff9800"
        else:
            servicio_util = "Poco útil"
            servicio_color = "#f44336"
        
        # 4. Métricas específicas de caja
        # Obtener información de la caja guardarropía
        from app.models.pos_models import PosSale
        
        # Ventas de la caja hoy
        ventas_caja_hoy = PosSale.query.filter(
            PosSale.register_id == 'GUARDARROPIA',
            PosSale.shift_date == shift_date
        ).all()
        
        # Calcular métricas de productividad de caja
        items_por_venta = len(ventas_caja_hoy) / items_deposited_today if items_deposited_today > 0 else 0
        tiempo_promedio_por_item = None  # Se podría calcular si hay timestamps detallados
        
        # Eficiencia de caja (ingresos por venta)
        eficiencia_caja = revenue_today / len(ventas_caja_hoy) if len(ventas_caja_hoy) > 0 else 0
        
        # 5. Sugerencias de mejora (enfocadas en operación de caja)
        sugerencias = []
        
        if retrieval_rate < 60:
            sugerencias.append({
                'tipo': 'warning',
                'titulo': 'Mejorar tasa de retiro desde la caja',
                'descripcion': f'La tasa de retiro es {retrieval_rate:.1f}%. Desde la caja, asegúrate de informar a los clientes sobre el proceso de retiro y horarios disponibles.'
            })
        
        if tasa_no_retiro > 15:
            sugerencias.append({
                'tipo': 'error',
                'titulo': 'Alto número de prendas no retiradas',
                'descripcion': f'Hay {items_no_retirados_count} prendas no retiradas ({tasa_no_retiro:.1f}%). Desde la caja, revisa el módulo de seguimiento y contacta a los clientes cuando sea posible.'
            })
        
        if occupancy_rate < 30:
            sugerencias.append({
                'tipo': 'info',
                'titulo': 'Baja ocupación - Oportunidad de promoción',
                'descripcion': f'La ocupación es {occupancy_rate:.1f}%. Desde la caja, promociona el servicio de guardarropía a los clientes que ingresen.'
            })
        
        if revenue_today < 10000 and items_deposited_today > 0:
            sugerencias.append({
                'tipo': 'warning',
                'titulo': 'Ingresos de caja por debajo del promedio',
                'descripcion': f'Los ingresos de la caja hoy (${revenue_today:.0f}) están por debajo del promedio diario (${avg_daily_revenue_7d:.0f}). Verifica que se estén cobrando correctamente todos los items.'
            })
        
        if hora_peak_items and hora_peak_items not in range(20, 24):  # Si el peak no es en horario nocturno
            sugerencias.append({
                'tipo': 'info',
                'titulo': 'Horario peak inusual - Ajustar personal de caja',
                'descripcion': f'La hora peak de la caja es a las {hora_peak_items}:00. Asegúrate de tener personal suficiente en la caja guardarropía en ese horario.'
            })
        
        if eficiencia_caja < 500 and len(ventas_caja_hoy) > 0:
            sugerencias.append({
                'tipo': 'warning',
                'titulo': 'Baja eficiencia de caja',
                'descripcion': f'El ingreso promedio por venta es ${eficiencia_caja:.0f}. Verifica que se estén cobrando los precios correctos y que no haya items sin cobrar.'
            })
        
        if len(ventas_caja_hoy) < items_deposited_today * 0.9:  # Si hay menos ventas que items depositados
            sugerencias.append({
                'tipo': 'error',
                'titulo': 'Items sin registrar en caja',
                'descripcion': f'Se depositaron {items_deposited_today} items pero solo hay {len(ventas_caja_hoy)} ventas registradas. Asegúrate de registrar todas las ventas en la caja.'
            })
        
        if not sugerencias:
            sugerencias.append({
                'tipo': 'success',
                'titulo': 'Caja guardarropía funcionando correctamente',
                'descripcion': 'Las métricas indican que la caja está operando correctamente. Mantén el registro adecuado de ventas y el seguimiento de prendas.'
            })
        
        # Compilar todas las estadísticas
        performance_stats = {
            'revenue_today': revenue_today,
            'revenue_yesterday': revenue_yesterday,
            'revenue_last_7d': revenue_last_7d,
            'revenue_30d': total_revenue_30d,
            'revenue_cash_today': revenue_cash_today,
            'revenue_debit_today': revenue_debit_today,
            'revenue_credit_today': revenue_credit_today,
            'items_deposited_today': items_deposited_today,
            'items_retrieved_today': items_retrieved_today,
            'items_deposited_yesterday': items_deposited_yesterday,
            'items_last_7_days': items_last_7_days,
            'retrieval_rate': retrieval_rate,
            'variation_items': variation_items,
            'variation_revenue': variation_revenue,
            'occupancy_rate': occupancy_rate,
            'avg_price_per_item': avg_price_per_item,
            'avg_daily_items_7d': avg_daily_items_7d,
            'avg_daily_revenue_7d': avg_daily_revenue_7d,
            'items_pending': items_pending,
            'total_clusters': total_clusters,
            'occupied_clusters_count': len(occupied_clusters),
            # Nuevas métricas de utilidad
            'hora_peak_items': hora_peak_items,
            'hora_peak_revenue': hora_peak_revenue,
            'items_por_hora': dict(items_por_hora),
            'ingresos_por_hora': dict(ingresos_por_hora),
            'tasa_no_retiro': tasa_no_retiro,
            'items_no_retirados_count': items_no_retirados_count,
            'revenue_per_item': revenue_per_item,
            'revenue_per_space': revenue_per_space,
            'utilidad_score': utilidad_score,
            'servicio_util': servicio_util,
            'servicio_color': servicio_color,
            'utilidad_factores': utilidad_factores,
            'sugerencias': sugerencias,
            # Métricas de caja
            'ventas_caja_hoy': len(ventas_caja_hoy),
            'items_por_venta': items_por_venta,
            'eficiencia_caja': eficiencia_caja
        }
        
        # Obtener últimos cierres de guardarropía (sin duplicados)
        from app.models.pos_models import RegisterClose
        
        # Obtener cierres únicos, ordenados por fecha de cierre
        ultimos_cierres = RegisterClose.query.filter(
            or_(
                RegisterClose.register_id == 'GUARDARROPIA',
                RegisterClose.register_name.like('%Guardarropía%'),
                RegisterClose.register_name.like('%guardarropía%')
            )
        ).order_by(desc(RegisterClose.closed_at)).limit(20).all()
        
        # Eliminar duplicados por register_id y fecha (si hay múltiples cierres del mismo día)
        cierres_unicos = {}
        for cierre in ultimos_cierres:
            key = f"{cierre.register_id}_{cierre.shift_date}_{cierre.closed_at.strftime('%Y-%m-%d %H:%M') if cierre.closed_at else ''}"
            if key not in cierres_unicos:
                cierres_unicos[key] = cierre
        
        ultimos_cierres = list(cierres_unicos.values())[:10]  # Limitar a 10
        
        # ⭐ ESTADÍSTICAS DE PRENDAS NO RETIRADAS
        from app.models.guardarropia_models import GuardarropiaItem
        prendas_no_retiradas = GuardarropiaItem.query.filter(
            GuardarropiaItem.status == 'deposited',
            GuardarropiaItem.marked_unretrieved_at.isnot(None)
        ).all()
        
        total_prendas_no_retiradas = len(prendas_no_retiradas)
        prendas_con_foto = len([p for p in prendas_no_retiradas if p.photo_path])
        prendas_sin_foto = total_prendas_no_retiradas - prendas_con_foto
        
        # Distribución por días
        prendas_por_dias = {
            '1-7 días': 0,
            '8-30 días': 0,
            '31-90 días': 0,
            '90+ días': 0
        }
        
        for prenda in prendas_no_retiradas:
            dias = prenda.days_since_unretrieved()
            if dias <= 7:
                prendas_por_dias['1-7 días'] += 1
            elif dias <= 30:
                prendas_por_dias['8-30 días'] += 1
            elif dias <= 90:
                prendas_por_dias['31-90 días'] += 1
            else:
                prendas_por_dias['90+ días'] += 1
        
        return render_template(
            'guardarropia/admin_dashboard.html',
            stats=stats,
            recent_items=recent_items,
            shift_date=shift_date,
            performance_stats=performance_stats,
            ultimos_cierres=ultimos_cierres,
            jornada_info=jornada_info,
            turno_duracion=turno_duracion,
            horas_operacion=horas_operacion,
            turno_cruza_medianoche=turno_cruza_medianoche,
            # Estadísticas de prendas no retiradas
            total_prendas_no_retiradas=total_prendas_no_retiradas,
            prendas_con_foto=prendas_con_foto,
            prendas_sin_foto=prendas_sin_foto,
            prendas_por_dias=prendas_por_dias
        )
    except Exception as e:
        current_app.logger.error(f"Error en admin_index de guardarropía: {e}", exc_info=True)
        flash(f'Error al cargar dashboard: {str(e)}', 'error')
        # Redirigir al informe de espacios como fallback
        return redirect(url_for('guardarropia_admin.informe_espacios'))


@guardarropia_admin_bp.route('/informe-espacios')
@guardarropia_bp.route('/informe-espacios')  # También disponible para trabajadores
def informe_espacios():
    """Informe detallado de espacios/clusters usados y disponibles"""
    # Permitir acceso a administradores, cajeros y empleados de guardarropía
    is_admin = session.get('admin_logged_in', False)
    is_cashier = session.get('pos_logged_in', False)  # Los cajeros operan las cajas
    is_employee = session.get('guardarropia_logged_in', False)
    
    if not is_admin and not is_cashier and not is_employee:
        if require_guardarropia_employee():
            return require_guardarropia_employee()
    
    try:
        service = get_guardarropia_service()
        
        # Obtener fecha del turno actual o fecha de hoy
        from app.application.services.service_factory import get_shift_service
        from datetime import datetime
        from app.helpers.timezone_utils import CHILE_TZ
        
        shift_service = get_shift_service()
        shift_status = shift_service.get_current_shift_status()
        
        if shift_status and shift_status.is_open:
            # Usar fecha del turno abierto
            shift_date = shift_status.shift_date
        else:
            # Usar fecha de hoy
            shift_date = datetime.now(CHILE_TZ).strftime('%Y-%m-%d')
        
        stats = service.get_stats(shift_date=shift_date)
        
        # Obtener clusters ocupados y disponibles para el mapa visual
        occupied_cluster_numbers = service.get_occupied_cluster_numbers(shift_date=shift_date if shift_date else None)
        cluster_info = service.get_cluster_info(shift_date=shift_date if shift_date else None)  # Información detallada de cada cluster
        
        # Enriquecer cluster_info con datos completos del item para el modal
        from app.models.guardarropia_models import GuardarropiaItem
        from sqlalchemy import or_
        for cluster_num, items in cluster_info.items():
            for item_info in items:
                # Buscar el item completo para obtener todos los datos
                item = GuardarropiaItem.query.filter_by(
                    ticket_code=item_info['ticket_code'],
                    status='deposited'
                ).filter(
                    or_(
                        GuardarropiaItem.notes.is_(None),
                        ~GuardarropiaItem.notes.like('%[ELIMINADO]%')
                    )
                ).first()
                if item:
                    # Agregar todos los campos disponibles
                    item_info['id'] = item.id
                    item_info['payment_type'] = item.payment_type
                    item_info['clusters'] = item.clusters
                    item_info['cluster_numbers'] = item.cluster_numbers
                    item_info['deposited_by'] = item.deposited_by
                    item_info['notes'] = item.notes
                    item_info['sale_id'] = item.sale_id
        
        all_clusters = list(range(1, 91))  # Clusters del 1 al 90
        
        # Obtener información del usuario que abrió la caja/sesión
        opened_by = (
            session.get('guardarropia_employee_name') or 
            session.get('pos_employee_name') or 
            session.get('admin_username') or 
            session.get('admin_user') or 
            'Sistema'
        )
        opened_at = session.get('guardarropia_logged_in_at') or session.get('pos_logged_in_at')
        
        # Obtener items depositados (no retirados) para el informe
        # IMPORTANTE: Obtener TODOS los items depositados directamente de la BD
        from app.models.guardarropia_models import GuardarropiaItem
        from app.models import db
        from datetime import datetime
        from app.helpers.timezone_utils import CHILE_TZ
        
        # Usar shift_date (que ahora siempre tiene un valor: turno actual, hoy, o filtro)
        # Filtrar items depositados que NO estén eliminados (no tengan [ELIMINADO] en notas)
        from sqlalchemy import or_
        deposited_items_query = GuardarropiaItem.query.filter_by(
            status='deposited',
            shift_date=shift_date
        ).filter(
            or_(
                GuardarropiaItem.notes.is_(None),
                ~GuardarropiaItem.notes.like('%[ELIMINADO]%')
            )
        )
        
        deposited_items = deposited_items_query.order_by(
            GuardarropiaItem.deposited_at.desc()
        ).all()
        
        current_app.logger.info(f"📊 Informe espacios - Items depositados encontrados: {len(deposited_items)}")
        for item in deposited_items:
            current_app.logger.info(
                f"   - Ticket: {item.ticket_code} | "
                f"Cliente: {item.customer_name or 'N/A'} | "
                f"Teléfono: {item.customer_phone or 'N/A'} | "
                f"Fecha: {item.deposited_at} | "
                f"Precio: ${item.price or 0} | "
                f"Pago: {item.payment_type or 'N/A'}"
            )
        
        # Obtener items retirados para la fecha del informe
        retrieved_today = GuardarropiaItem.query.filter_by(
            status='retrieved',
            shift_date=shift_date
        ).order_by(GuardarropiaItem.retrieved_at.desc()).all()
        
        return render_template(
            'guardarropia/informe_espacios.html',
            stats=stats,
            deposited_items=deposited_items,
            retrieved_today=retrieved_today,
            total_spaces=90,
            shift_date=shift_date,  # Siempre mostrar la fecha (del turno o filtro)
            is_admin=is_admin or is_cashier,  # Tratar cajeros como admins para la vista
            occupied_cluster_numbers=occupied_cluster_numbers,  # Lista de clusters ocupados
            cluster_info=cluster_info,  # Información detallada de cada cluster
            all_clusters=all_clusters,  # Todos los clusters (1-90)
            opened_by=opened_by,  # Usuario que abrió la caja
            opened_at=opened_at  # Fecha/hora de apertura
        )
    except Exception as e:
            current_app.logger.error(f"Error al generar informe de espacios: {e}", exc_info=True)
            flash(f"Error al generar informe: {str(e)}", "error")
            return redirect(url_for('guardarropia.index'))


@guardarropia_bp.route('/close-register', methods=['GET'])
def close_register_view():
    """Vista para cierre de caja de guardarropía"""
    is_admin = session.get('admin_logged_in', False)
    is_cashier = session.get('pos_logged_in', False)  # Los cajeros operan las cajas
    is_employee = session.get('guardarropia_logged_in', False)
    
    if not is_admin and not is_cashier and not is_employee:
        flash("Debes iniciar sesión primero.", "error")
        if is_admin or is_cashier:
            return redirect(url_for('guardarropia.pos'))
        else:
            return redirect(url_for('guardarropia.login'))
    
    # Obtener nombre del empleado según el tipo de sesión
    if is_employee:
        employee_name = session.get('guardarropia_employee_name', 'Empleado')
    elif is_cashier:
        employee_name = session.get('pos_employee_name', 'Cajero')
    else:
        employee_name = session.get('admin_username', 'Administrador')
    
    register_name = 'Guardarropía'
    
    return render_template('guardarropia/close_register.html', 
                          employee_name=employee_name,
                          register_name=register_name)


@guardarropia_bp.route('/api/register-summary', methods=['GET'])
def api_register_summary():
    """API: Obtener resumen de guardarropía para cierre"""
    is_admin = session.get('admin_logged_in', False)
    is_cashier = session.get('pos_logged_in', False)
    is_employee = session.get('guardarropia_logged_in', False)
    
    if not is_admin and not is_cashier and not is_employee:
        return jsonify({'success': False, 'error': 'No autenticado'}), 401
    
    try:
        from app.application.services.service_factory import get_shift_service
        from app.models.pos_models import PosSale
        from app.models import db
        from datetime import datetime
        from app.helpers.timezone_utils import CHILE_TZ
        
        shift_service = get_shift_service()
        shift_status = shift_service.get_current_shift_status()
        shift_date = shift_status.shift_date if shift_status else datetime.now(CHILE_TZ).strftime('%Y-%m-%d')
        
        # Obtener fecha/hora de apertura de la sesión
        if is_employee:
            opened_at = session.get('guardarropia_logged_in_at')
            employee_name = session.get('guardarropia_employee_name', 'Empleado')
        elif is_cashier:
            opened_at = session.get('pos_logged_in_at')
            employee_name = session.get('pos_employee_name', 'Cajero')
        else:
            opened_at = None
            employee_name = session.get('admin_username', 'Administrador')
        
        # Obtener ventas de guardarropía del turno actual
        # Las ventas de guardarropía tienen register_id = 'GUARDARROPIA'
        register_sales = PosSale.query.filter_by(
            register_id='GUARDARROPIA',
            shift_date=shift_date
        ).all()
        
        # Calcular totales por método de pago
        total_cash = sum(float(s.payment_cash or 0) for s in register_sales)
        total_debit = sum(float(s.payment_debit or 0) for s in register_sales)
        total_credit = sum(float(s.payment_credit or 0) for s in register_sales)
        
        return jsonify({
            'success': True,
            'summary': {
                'total_sales': len(register_sales),
                'total_cash': total_cash,
                'total_debit': total_debit,
                'total_credit': total_credit,
                'total_amount': total_cash + total_debit + total_credit,
                'register_name': 'Guardarropía',
                'employee_name': employee_name,
                'shift_date': shift_date,
                'opened_at': opened_at or datetime.now(CHILE_TZ).strftime('%Y-%m-%d %H:%M:%S')
            },
            'sales': [s.to_dict() for s in register_sales[:50]]
        })
    except Exception as e:
        current_app.logger.error(f"Error al obtener resumen de guardarropía: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@guardarropia_bp.route('/api/close-register', methods=['POST'])
def api_close_register():
    """API: Procesar cierre de caja de guardarropía"""
    is_admin = session.get('admin_logged_in', False)
    is_cashier = session.get('pos_logged_in', False)
    is_employee = session.get('guardarropia_logged_in', False)
    
    if not is_admin and not is_cashier and not is_employee:
        return jsonify({'success': False, 'error': 'No autenticado'}), 401
    
    try:
        from app.application.services.service_factory import get_shift_service
        from app.models.pos_models import PosSale, RegisterClose
        from app.models import db
        from datetime import datetime
        from app.helpers.timezone_utils import CHILE_TZ
        from app.helpers.financial_utils import safe_float
        
        data = request.get_json()
        actual_cash = float(data.get('actual_cash', 0))
        actual_debit = float(data.get('actual_debit', 0))
        actual_credit = float(data.get('actual_credit', 0))
        notes = data.get('notes', '')
        
        if actual_cash < 0 or actual_debit < 0 or actual_credit < 0:
            return jsonify({'success': False, 'error': 'Los montos no pueden ser negativos'}), 400
        
        # Obtener resumen
        shift_service = get_shift_service()
        shift_status = shift_service.get_current_shift_status()
        shift_date = shift_status.shift_date if shift_status else datetime.now(CHILE_TZ).strftime('%Y-%m-%d')
        
        register_sales = PosSale.query.filter_by(
            register_id='GUARDARROPIA',
            shift_date=shift_date
        ).all()
        
        expected_cash = sum(float(s.payment_cash or 0) for s in register_sales)
        expected_debit = sum(float(s.payment_debit or 0) for s in register_sales)
        expected_credit = sum(float(s.payment_credit or 0) for s in register_sales)
        
        diff_cash = actual_cash - expected_cash
        diff_debit = actual_debit - expected_debit
        diff_credit = actual_credit - expected_credit
        difference = diff_cash + diff_debit + diff_credit
        
        # Obtener información del empleado según el tipo de sesión
        if is_employee:
            opened_at = session.get('guardarropia_logged_in_at')
            employee_id = session.get('guardarropia_employee_id', '')
            employee_name = session.get('guardarropia_employee_name', 'Empleado')
        elif is_cashier:
            opened_at = session.get('pos_logged_in_at')
            employee_id = session.get('pos_employee_id', '')
            employee_name = session.get('pos_employee_name', 'Cajero')
        else:
            opened_at = None
            employee_id = ''
            employee_name = session.get('admin_username', 'Administrador')
        
        # Guardar cierre
        register_close = RegisterClose(
            register_id='GUARDARROPIA',
            register_name='Guardarropía',
            employee_id=employee_id,
            employee_name=employee_name,
            shift_date=shift_date,
            opened_at=opened_at or datetime.now(CHILE_TZ).strftime('%Y-%m-%d %H:%M:%S'),
            closed_at=datetime.now(CHILE_TZ).replace(tzinfo=None),
            expected_cash=safe_float(expected_cash),
            actual_cash=safe_float(actual_cash),
            diff_cash=safe_float(diff_cash),
            expected_debit=safe_float(expected_debit),
            actual_debit=safe_float(actual_debit),
            diff_debit=safe_float(diff_debit),
            expected_credit=safe_float(expected_credit),
            actual_credit=safe_float(actual_credit),
            diff_credit=safe_float(diff_credit),
            total_sales=len(register_sales),
            total_amount=safe_float(expected_cash + expected_debit + expected_credit),
            difference_total=safe_float(difference),
            notes=notes,
            status='pending'
        )
        
        db.session.add(register_close)
        db.session.commit()
        
        current_app.logger.info(f"✅ Cierre de guardarropía registrado: ID {register_close.id}, Diferencia: ${difference}")
        
        # Limpiar sesión solo si es empleado de guardarropía
        # No limpiar sesión de cajeros o administradores
        if is_employee:
            session.pop('guardarropia_logged_in', None)
            session.pop('guardarropia_employee_id', None)
            session.pop('guardarropia_employee_name', None)
            session.pop('guardarropia_jornada_id', None)
            session.pop('guardarropia_logged_in_at', None)
        
        return jsonify({
            'success': True,
            'message': 'Cierre de guardarropía registrado correctamente',
            'redirect_url': url_for('guardarropia.login')
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error al cerrar guardarropía: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@guardarropia_bp.route('/api/verify-pin', methods=['POST'])
def api_verify_pin():
    """API: Verificar PIN para cierre de caja"""
    is_admin = session.get('admin_logged_in', False)
    is_cashier = session.get('pos_logged_in', False)
    is_employee = session.get('guardarropia_logged_in', False)
    
    if not is_admin and not is_cashier and not is_employee:
        return jsonify({'success': False, 'error': 'No autenticado'}), 401
    
    try:
        data = request.get_json()
        pin = data.get('pin', '').strip()
        
        if not pin:
            return jsonify({'success': False, 'error': 'PIN requerido'}), 400
        
        # Obtener employee_id según el tipo de sesión
        if is_employee:
            employee_id = session.get('guardarropia_employee_id')
        elif is_cashier:
            employee_id = session.get('pos_employee_id')
        else:
            # Para administradores, permitir sin verificación de PIN o verificar con admin
            return jsonify({'success': True, 'message': 'PIN correcto (admin)'})
        
        # Verificar PIN del empleado actual
        from app.helpers.pos_api import authenticate_employee
        employee = authenticate_employee(None, pin=pin, employee_id=employee_id)
        
        if employee:
            return jsonify({'success': True, 'message': 'PIN correcto'})
        else:
            return jsonify({'success': False, 'error': 'PIN incorrecto'}), 401
            
    except Exception as e:
        current_app.logger.error(f"Error al verificar PIN: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@guardarropia_bp.route('/api/open-cash-drawer', methods=['POST'])
def api_open_cash_drawer():
    """API: Abrir cajón de dinero manualmente"""
    is_admin = session.get('admin_logged_in', False)
    is_cashier = session.get('pos_logged_in', False)
    is_employee = session.get('guardarropia_logged_in', False)
    
    if not is_admin and not is_cashier and not is_employee:
        return jsonify({'success': False, 'error': 'No autenticado'}), 401
    
    try:
        from app.services.ticket_printer_service import TicketPrinterService
        printer_service = TicketPrinterService()
        success = printer_service.open_cash_drawer()
        
        if success:
            return jsonify({'success': True, 'message': 'Cajón abierto'})
        else:
            return jsonify({'success': False, 'error': 'No se pudo abrir el cajón'}), 500
    except Exception as e:
        current_app.logger.error(f"Error al abrir cajón: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@guardarropia_bp.route('/api/stats')
def api_stats():
    """API endpoint para obtener estadísticas"""
    if require_guardarropia_employee():
        return jsonify({'error': 'No autorizado'}), 401
    
    try:
        service = get_guardarropia_service()
        shift_date = request.args.get('shift_date', '')
        
        stats = service.get_stats(shift_date=shift_date if shift_date else None)
        
        return jsonify({
            'success': True,
            'stats': {
                'total_deposited': stats.total_deposited,
                'total_retrieved': stats.total_retrieved,
                'total_lost': stats.total_lost,
                'currently_stored': stats.currently_stored,
                'spaces_occupied': stats.spaces_occupied,
                'spaces_available': stats.spaces_available,
                'shift_date': stats.shift_date
            }
        })
    except Exception as e:
        current_app.logger.error(f"Error al obtener estadísticas: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f"Error inesperado: {str(e)}"
        }), 500


@guardarropia_bp.route('/api/update-item', methods=['POST'])
@guardarropia_admin_bp.route('/api/update-item', methods=['POST'])
def api_update_item():
    """API: Actualizar un item de guardarropía"""
    # Permitir acceso a administradores, cajeros y empleados de guardarropía
    is_admin = session.get('admin_logged_in', False)
    is_cashier = session.get('pos_logged_in', False)
    is_employee = session.get('guardarropia_logged_in', False)
    
    if not is_admin and not is_cashier and not is_employee:
        return jsonify({'success': False, 'error': 'No autorizado'}), 401
    
    try:
        data = request.get_json()
        item_id = data.get('item_id')
        ticket_code = data.get('ticket_code')
        
        if not item_id and not ticket_code:
            return jsonify({'success': False, 'error': 'ID o código de ticket requerido'}), 400
        
        from app.models.guardarropia_models import GuardarropiaItem
        from app.models import db
        
        # Buscar el item
        if item_id:
            item = GuardarropiaItem.query.get(item_id)
        else:
            item = GuardarropiaItem.query.filter_by(ticket_code=ticket_code).first()
        
        if not item:
            return jsonify({'success': False, 'error': 'Item no encontrado'}), 404
        
        # Actualizar campos
        if 'customer_name' in data:
            item.customer_name = data['customer_name']
        if 'customer_phone' in data:
            item.customer_phone = data['customer_phone']
        if 'description' in data:
            item.description = data['description']
        if 'price' in data:
            from decimal import Decimal
            item.price = Decimal(str(data['price'])) if data['price'] else None
        if 'payment_type' in data:
            item.payment_type = data['payment_type'] if data['payment_type'] else None
        if 'cluster_numbers' in data:
            item.cluster_numbers = data['cluster_numbers'] if data['cluster_numbers'] else None
        
        db.session.commit()
        
        current_app.logger.info(f"✅ Item actualizado: {item.ticket_code} por {session.get('admin_username') or session.get('guardarropia_employee_name') or 'Usuario'}")
        
        return jsonify({
            'success': True,
            'message': 'Item actualizado correctamente',
            'item': item.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error al actualizar item: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@guardarropia_bp.route('/api/delete-item', methods=['POST'])
@guardarropia_admin_bp.route('/api/delete-item', methods=['POST'])
def api_delete_item():
    """API: Eliminar un item de guardarropía (soft delete)"""
    # Permitir acceso a administradores, cajeros y empleados de guardarropía
    is_admin = session.get('admin_logged_in', False)
    is_cashier = session.get('pos_logged_in', False)
    is_employee = session.get('guardarropia_logged_in', False)
    
    if not is_admin and not is_cashier and not is_employee:
        return jsonify({'success': False, 'error': 'No autorizado'}), 401
    
    try:
        data = request.get_json()
        item_id = data.get('item_id')
        ticket_code = data.get('ticket_code')
        reason = data.get('reason', '').strip()
        
        if not reason:
            return jsonify({'success': False, 'error': 'Debes proporcionar una razón para la eliminación'}), 400
        
        if not item_id and not ticket_code:
            return jsonify({'success': False, 'error': 'ID o código de ticket requerido'}), 400
        
        from app.models.guardarropia_models import GuardarropiaItem
        from app.models import db
        from datetime import datetime
        from app.helpers.timezone_utils import CHILE_TZ
        
        # Buscar el item
        if item_id:
            item = GuardarropiaItem.query.get(item_id)
        else:
            item = GuardarropiaItem.query.filter_by(ticket_code=ticket_code).first()
        
        if not item:
            return jsonify({'success': False, 'error': 'Item no encontrado'}), 404
        
        # Soft delete: marcar como eliminado (NO borrar físicamente de la BD)
        deleted_by = session.get('admin_username') or session.get('guardarropia_employee_name') or session.get('pos_employee_name') or 'Usuario'
        deleted_at = datetime.now(CHILE_TZ).strftime('%Y-%m-%d %H:%M:%S')
        
        # Agregar información de eliminación a las notas (el ticket NO se borra, solo se marca)
        # El ticket permanece en la base de datos pero se marca como eliminado
        eliminacion_info = f"\n\n[ELIMINADO] Por: {deleted_by} | Fecha: {deleted_at} | Razón: {reason}"
        item.notes = (item.notes or '') + eliminacion_info
        
        # NO cambiar el status, mantenerlo como 'deposited' pero marcado en notas
        # Esto permite que el ticket siga existiendo en la BD pero no se muestre en listados activos
        
        # Liberar los clusters asignados para que estén disponibles nuevamente
        clusters_liberados = item.cluster_numbers  # Guardar para logging
        item.cluster_numbers = None
        
        db.session.commit()
        
        current_app.logger.info(
            f"✅ Item eliminado (soft delete): {item.ticket_code} por {deleted_by} - Razón: {reason} | "
            f"Clusters liberados: {clusters_liberados or 'N/A'}"
        )
        
        return jsonify({
            'success': True,
            'message': f'Item eliminado correctamente (soft delete). Clusters liberados: {clusters_liberados or "N/A"}',
            'clusters_liberados': clusters_liberados
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error al eliminar item: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


# ========== RUTAS PARA PRENDAS NO RETIRADAS ==========

@guardarropia_admin_bp.route('/prendas-no-retiradas')
def prendas_no_retiradas():
    """Lista todas las prendas no retiradas con fotos y seguimiento"""
    if require_admin():
        return require_admin()
    
    try:
        from app.models.guardarropia_models import GuardarropiaItem
        from sqlalchemy import or_, desc
        from datetime import datetime, timedelta
        from app.helpers.timezone_utils import CHILE_TZ
        
        # Obtener prendas no retiradas (que tienen marked_unretrieved_at)
        prendas = GuardarropiaItem.query.filter(
            GuardarropiaItem.marked_unretrieved_at.isnot(None),
            or_(
                GuardarropiaItem.notes.is_(None),
                ~GuardarropiaItem.notes.like('%[ELIMINADO]%')
            )
        ).order_by(desc(GuardarropiaItem.marked_unretrieved_at)).all()
        
        # Calcular estadísticas
        total_prendas = len(prendas)
        prendas_con_foto = sum(1 for p in prendas if p.photo_path)
        prendas_sin_foto = total_prendas - prendas_con_foto
        
        # Agrupar por días desde marcado
        prendas_por_dias = {}
        for prenda in prendas:
            dias = prenda.days_since_unretrieved()
            if dias <= 7:
                rango = "1-7 días"
            elif dias <= 30:
                rango = "8-30 días"
            elif dias <= 90:
                rango = "31-90 días"
            else:
                rango = "Más de 90 días"
            
            if rango not in prendas_por_dias:
                prendas_por_dias[rango] = 0
            prendas_por_dias[rango] += 1
        
        return render_template(
            'guardarropia/prendas_no_retiradas.html',
            prendas=prendas,
            total_prendas=total_prendas,
            prendas_con_foto=prendas_con_foto,
            prendas_sin_foto=prendas_sin_foto,
            prendas_por_dias=prendas_por_dias
        )
    except Exception as e:
        current_app.logger.error(f"Error al listar prendas no retiradas: {e}", exc_info=True)
        flash(f'Error al cargar prendas no retiradas: {str(e)}', 'error')
        return redirect(url_for('guardarropia_admin.admin_index'))


@guardarropia_admin_bp.route('/marcar-no-retirado/<ticket_code>', methods=['POST'])
def marcar_no_retirado(ticket_code):
    """Marca una prenda como no retirada"""
    if require_admin():
        return require_admin()
    
    try:
        from app.models.guardarropia_models import GuardarropiaItem
        from app.models import db
        from datetime import datetime
        from app.helpers.timezone_utils import CHILE_TZ
        
        item = GuardarropiaItem.query.filter_by(ticket_code=ticket_code).first()
        if not item:
            flash(f"No se encontró el ticket {ticket_code}", "error")
            return redirect(url_for('guardarropia_admin.prendas_no_retiradas'))
        
        # Marcar como no retirado
        item.marked_unretrieved_at = datetime.now(CHILE_TZ)
        item.marked_unretrieved_by = session.get('admin_username', 'admin')
        
        # Si hay foto en el request, guardarla
        if 'photo' in request.files:
            photo = request.files['photo']
            if photo and photo.filename:
                photo_path = save_guardarropia_photo(photo, ticket_code)
                if photo_path:
                    item.photo_path = photo_path
        
        # Agregar nota de seguimiento inicial si se proporciona
        tracking_note = request.form.get('tracking_note', '').strip()
        if tracking_note:
            if item.tracking_notes:
                item.tracking_notes += f"\n[{datetime.now(CHILE_TZ).strftime('%Y-%m-%d %H:%M')}] {tracking_note}"
            else:
                item.tracking_notes = f"[{datetime.now(CHILE_TZ).strftime('%Y-%m-%d %H:%M')}] {tracking_note}"
            item.last_tracking_date = datetime.now(CHILE_TZ)
        
        db.session.commit()
        
        flash(f"Prenda {ticket_code} marcada como no retirada correctamente", "success")
        return redirect(url_for('guardarropia_admin.prendas_no_retiradas'))
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error al marcar prenda como no retirada: {e}", exc_info=True)
        flash(f'Error al marcar prenda: {str(e)}', 'error')
        return redirect(url_for('guardarropia_admin.prendas_no_retiradas'))


@guardarropia_admin_bp.route('/agregar-foto/<ticket_code>', methods=['POST'])
def agregar_foto(ticket_code):
    """Agrega o actualiza la foto de una prenda no retirada"""
    if require_admin():
        return require_admin()
    
    try:
        from app.models.guardarropia_models import GuardarropiaItem
        from app.models import db
        
        item = GuardarropiaItem.query.filter_by(ticket_code=ticket_code).first()
        if not item:
            return jsonify({'success': False, 'error': 'Ticket no encontrado'}), 404
        
        if 'photo' not in request.files:
            return jsonify({'success': False, 'error': 'No se proporcionó foto'}), 400
        
        photo = request.files['photo']
        if not photo or not photo.filename:
            return jsonify({'success': False, 'error': 'Archivo de foto vacío'}), 400
        
        # Guardar foto
        photo_path = save_guardarropia_photo(photo, ticket_code)
        if not photo_path:
            return jsonify({'success': False, 'error': 'Error al guardar foto'}), 500
        
        # Actualizar item
        old_photo_path = item.photo_path
        item.photo_path = photo_path
        db.session.commit()
        
        # Eliminar foto antigua si existe
        if old_photo_path:
            try:
                import os
                static_folder = current_app.static_folder or os.path.join(current_app.root_path, 'static')
                old_path = os.path.join(static_folder, old_photo_path.lstrip('/'))
                if os.path.exists(old_path):
                    os.remove(old_path)
            except Exception as e:
                current_app.logger.warning(f"No se pudo eliminar foto antigua: {e}")
        
        return jsonify({
            'success': True,
            'message': 'Foto agregada correctamente',
            'photo_path': photo_path
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error al agregar foto: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@guardarropia_admin_bp.route('/agregar-seguimiento/<ticket_code>', methods=['POST'])
def agregar_seguimiento(ticket_code):
    """Agrega una nota de seguimiento a una prenda no retirada"""
    if require_admin():
        return require_admin()
    
    try:
        from app.models.guardarropia_models import GuardarropiaItem
        from app.models import db
        from datetime import datetime
        from app.helpers.timezone_utils import CHILE_TZ
        
        item = GuardarropiaItem.query.filter_by(ticket_code=ticket_code).first()
        if not item:
            return jsonify({'success': False, 'error': 'Ticket no encontrado'}), 404
        
        tracking_note = request.form.get('tracking_note', '').strip()
        if not tracking_note:
            return jsonify({'success': False, 'error': 'Nota de seguimiento vacía'}), 400
        
        # Agregar nota de seguimiento
        timestamp = datetime.now(CHILE_TZ).strftime('%Y-%m-%d %H:%M')
        user = session.get('admin_username', 'admin')
        new_note = f"[{timestamp}] {user}: {tracking_note}"
        
        if item.tracking_notes:
            item.tracking_notes += f"\n{new_note}"
        else:
            item.tracking_notes = new_note
        
        item.last_tracking_date = datetime.now(CHILE_TZ)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Seguimiento agregado correctamente',
            'tracking_note': new_note,
            'last_tracking_date': item.last_tracking_date.isoformat()
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error al agregar seguimiento: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


def save_guardarropia_photo(photo_file, ticket_code):
    """
    Guarda una foto de guardarropía en el directorio estático
    Returns: ruta relativa desde static (ej: 'img/guardarropia/GR12345.jpg')
    """
    try:
        import os
        from werkzeug.utils import secure_filename
        from PIL import Image
        import io
        
        # Obtener ruta del directorio static
        static_folder = current_app.static_folder or os.path.join(current_app.root_path, 'static')
        
        # Crear directorio si no existe
        guardarropia_dir = os.path.join(static_folder, 'img', 'guardarropia')
        os.makedirs(guardarropia_dir, exist_ok=True)
        
        # Obtener extensión del archivo
        filename = secure_filename(photo_file.filename)
        ext = os.path.splitext(filename)[1].lower()
        if ext not in ['.jpg', '.jpeg', '.png', '.gif']:
            ext = '.jpg'  # Por defecto JPG
        
        # Nombre del archivo: ticket_code + timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_ticket = secure_filename(ticket_code)
        new_filename = f"{safe_ticket}_{timestamp}{ext}"
        
        # Ruta completa
        file_path = os.path.join(guardarropia_dir, new_filename)
        
        # Leer y optimizar imagen
        photo_file.seek(0)
        img = Image.open(io.BytesIO(photo_file.read()))
        
        # Convertir a RGB si es necesario (para PNG con transparencia)
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background
        
        # Redimensionar si es muy grande (max 1920x1920)
        max_size = (1920, 1920)
        if img.size[0] > max_size[0] or img.size[1] > max_size[1]:
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        # Guardar con calidad optimizada
        img.save(file_path, 'JPEG', quality=85, optimize=True)
        
        # Retornar ruta relativa desde static
        return f"img/guardarropia/{new_filename}"
        
    except Exception as e:
        current_app.logger.error(f"Error al guardar foto de guardarropía: {e}", exc_info=True)
        return None


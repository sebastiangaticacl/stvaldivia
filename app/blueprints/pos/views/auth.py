import logging
from flask import render_template, request, jsonify, session, redirect, url_for, flash, current_app
from app.blueprints.pos import caja_bp
from app.helpers.pos_api import authenticate_employee, get_employees
from app.helpers.puesto_validator import puede_abrir_puesto, obtener_empleados_habilitados_para_puesto
from app.helpers.session_manager import init_session
from app.models import db
from datetime import datetime
from app.helpers.motivational_messages import get_welcome_message, get_time_based_greeting
from app.helpers.rate_limiting import is_locked_out, record_failed_attempt, clear_failed_attempts
from app.helpers.sale_audit_logger import SaleAuditLogger
from app.helpers.register_lock_db import unlock_register
from app.blueprints.pos.services import pos_service

logger = logging.getLogger(__name__)

@caja_bp.route('/', methods=['GET'])
@caja_bp.route('', methods=['GET'])
def home():
    """Home del POS - Redirige a login"""
    return redirect(url_for('caja.login'))

@caja_bp.route('/caja1', methods=['GET'])
def caja1():
    """Ruta directa para Caja 1 - Redirige a login y luego a caja 1"""
    session['target_register_id'] = '1'
    return redirect(url_for('caja.login'))

@caja_bp.route('/caja2', methods=['GET'])
def caja2():
    """Ruta directa para Caja 2 - Redirige a login y luego a caja 2"""
    session['target_register_id'] = '2'
    return redirect(url_for('caja.login'))

@caja_bp.route('/caja3', methods=['GET'])
def caja3():
    """Ruta directa para Caja 3 - Redirige a login y luego a caja 3"""
    session['target_register_id'] = '3'
    return redirect(url_for('caja.login'))

@caja_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login del POS - Autenticación por empleado + PIN (flujo nuevo)"""
    # Limpiar sesión de guardarropía si existe (para evitar conflictos)
    if session.get('guardarropia_logged_in'):
        session.pop('guardarropia_logged_in', None)
        session.pop('guardarropia_employee_id', None)
        session.pop('guardarropia_jornada_id', None)
        session.pop('guardarropia_employee_name', None)

    # Si ya está logueado en POS, ir directo a selección de caja (flujo nuevo)
    if session.get('pos_logged_in'):
        return redirect(url_for('caja.register'))

    if request.method == 'POST':
        pin = (request.form.get('pin') or '').strip()
        employee_id = request.form.get('employee_id')

        if not pin or not employee_id:
            flash("Debes ingresar tu PIN.", "error")
            employees = obtener_empleados_habilitados_para_puesto("caja")
            return render_template('pos/login.html', employees=employees, puesto='caja')

        employee = authenticate_employee(None, pin=pin, employee_id=employee_id)
        if employee:
            employee_id_str = str(employee["id"]) if employee.get("id") else None
            puede_acceder, mensaje_validacion, jornada_id = puede_abrir_puesto(employee_id_str, "caja")

            if not puede_acceder:
                flash(mensaje_validacion, "error")
                employee_name = employee.get("name", "Desconocido")
                logger.warning(f"⚠️  Intento de acceso denegado: {employee_name} - {mensaje_validacion}")
                employees = obtener_empleados_habilitados_para_puesto("caja")
                return render_template('pos/login.html', employees=employees, puesto='caja')

            session['pos_employee_id'] = employee_id_str
            session["jornada_id"] = jornada_id
            session['pos_employee_name'] = employee.get('name', 'Empleado')
            session['pos_logged_in'] = True
            session['show_fortune_cookie'] = True

            employee_name = employee.get("name", "Empleado")
            logger.info(f"✅ Login Caja exitoso: {employee_name}")
            init_session()
            try:
                welcome_msg = f"{get_time_based_greeting()} {get_welcome_message(employee_name)}"
            except Exception:
                welcome_msg = f"Bienvenido, {employee_name}!"
            flash(welcome_msg, "success")

            return redirect(url_for('caja.register', show_fortune='true'))

        flash("PIN incorrecto. Intenta nuevamente.", "error")

    employees = obtener_empleados_habilitados_para_puesto("caja")
    if not employees:
        # Mantener mensajes similares a Guardarropía para UX en local
        try:
            from app.models.jornada_models import Jornada
            jornada_abierta = Jornada.query.filter_by(estado_apertura='abierto').order_by(
                Jornada.fecha_jornada.desc()
            ).first()
            if not jornada_abierta:
                flash("No hay un turno abierto actualmente. Abre un turno desde el panel administrativo antes de acceder a Caja.", "warning")
            else:
                flash("No hay cajeros asignados en el turno actual. Asigna cajeros en la planilla del turno desde el panel administrativo.", "warning")
        except Exception:
            pass

    return render_template('pos/login.html', employees=employees, puesto='caja')


@caja_bp.route('/login_old', methods=['GET', 'POST'])
def login_old():
    """DEPRECATED: Login del POS antiguo (compatibilidad). Preferir /caja/login + /caja/register"""
    # Obtener register_id desde query params
    register_id = request.args.get('register_id')
    register_name = request.args.get('register_name')
    
    if request.method == 'POST':
        pin = request.form.get('pin', '').strip()
        employee_id = request.form.get('employee_id')
        
        if not pin or not employee_id:
            flash("Debes ingresar tu PIN.", "error")
            employees = obtener_empleados_habilitados_para_puesto("caja")
            return render_template('pos/login.html', employees=employees, register_id=register_id, register_name=register_name, puesto='caja', form_action=url_for('caja.login_old'))
        
        employee = authenticate_employee(None, pin=pin, employee_id=employee_id)
        
        if employee:
            employee_id_str = str(employee["id"]) if employee.get("id") else None
            puede_acceder, mensaje_validacion, jornada_id = puede_abrir_puesto(employee_id_str, "caja")
        
            if not puede_acceder:
                flash(mensaje_validacion, "error")
                employee_name = employee.get("name", "Desconocido")
                logger.warning(f"⚠️  Intento de acceso denegado: {employee_name} - {mensaje_validacion}")
                employees = obtener_empleados_habilitados_para_puesto("caja")
                return render_template("pos/login.html", employees=employees, register_id=register_id, register_name=register_name, puesto='caja', form_action=url_for('caja.login_old'))
            
            employee_id_str = str(employee['id']) if employee.get('id') else None
            session['pos_employee_id'] = employee_id_str
            session["jornada_id"] = jornada_id
            session['pos_employee_name'] = employee['name']
            session['pos_logged_in'] = True
            session['show_fortune_cookie'] = True  # Flag en sesión para mostrar galleta
            
            # Guardar register_id si se proporcionó
            if register_id:
                session['register_id'] = register_id
            if register_name:
                session['register_name'] = register_name
            
            employee_name = employee.get("name", "Empleado")
            logger.info(f"✅ Login exitoso: {employee_name}")
            init_session()
            welcome_msg = f"{get_time_based_greeting()} {get_welcome_message(employee_name)}"
            flash(welcome_msg, "success")
            # Redirigir con parámetro para mostrar galleta de la fortuna
            return redirect(url_for('caja.register', show_fortune='true'))
        else:
            flash("PIN incorrecto. Intenta nuevamente.", "error")
            # IMPORTANTE: Mantener register_id y register_name para permitir reintentos
            employees = obtener_empleados_habilitados_para_puesto("caja")
            return render_template('pos/login.html', employees=employees, register_id=register_id, register_name=register_name, puesto='caja', form_action=url_for('caja.login_old'))
    
    employees = obtener_empleados_habilitados_para_puesto("caja")
    if not employees:
        logger.warning("⚠️ No hay empleados habilitados para Caja")
        flash("No hay cajeros asignados en el turno actual. Por favor, contacta al administrador.", "warning")
    return render_template('pos/login.html', employees=employees, register_id=register_id, register_name=register_name, puesto='caja', form_action=url_for('caja.login_old'))


@caja_bp.route('/api/verify-pin', methods=['POST'])
def api_verify_pin():
    """API: Verificar PIN del empleado actual o PIN del superadmin para operaciones como cerrar caja"""
    if not session.get('pos_logged_in'):
        return jsonify({'success': False, 'error': 'No autenticado'}), 401
    
    try:
        data = request.get_json()
        pin = data.get('pin', '').strip()
        
        if not pin:
            return jsonify({'success': False, 'error': 'PIN requerido'}), 400
        
        # Verificar si es una sesión de admin y si el PIN es el del superadmin
        is_admin = session.get('admin_logged_in', False)
        if is_admin:
            from flask import current_app
            SUPERADMIN_PIN = current_app.config.get('SUPERADMIN_PIN', '9999')
            if pin == SUPERADMIN_PIN:
                logger.info("✅ PIN del superadmin verificado correctamente")
                return jsonify({
                    'success': True,
                    'message': 'PIN del superadmin verificado correctamente',
                    'employee': {
                        'id': 'superadmin',
                        'name': session.get('admin_username', 'Superadmin')
                    }
                })
        
        # Obtener employee_id de la sesión
        employee_id = session.get('pos_employee_id')
        if not employee_id:
            logger.warning("⚠️ No hay employee_id en la sesión")
            return jsonify({'success': False, 'error': 'No hay empleado en la sesión'}), 400
        
        # Verificar PIN usando la función de autenticación local
        from app.helpers.employee_local import authenticate_employee_local
        
        employee = authenticate_employee_local(str(employee_id), pin)
        
        if employee:
            logger.info(f"✅ PIN verificado correctamente para empleado {employee_id}")
            return jsonify({
                'success': True,
                'message': 'PIN verificado correctamente',
                'employee': {
                    'id': employee.get('id'),
                    'name': employee.get('name')
                }
            })
        else:
            logger.warning(f"❌ PIN incorrecto para empleado {employee_id}")
            return jsonify({'success': False, 'error': 'PIN incorrecto'}), 401
            
    except Exception as e:
        logger.error(f"Error al verificar PIN: {e}", exc_info=True)
        return jsonify({'success': False, 'error': f'Error al verificar PIN: {str(e)}'}), 500


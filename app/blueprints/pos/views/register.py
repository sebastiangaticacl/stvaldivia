import logging
import json
from datetime import datetime
from flask import render_template, request, jsonify, session, redirect, url_for, flash, current_app
from app.helpers.timezone_utils import CHILE_TZ
from app.blueprints.pos import caja_bp
from app.blueprints.pos.services import pos_service
from app.infrastructure.services.ticket_printer_service import TicketPrinterService
from app.models import PosSale, db
from app.helpers.register_lock_db import (
    lock_register, is_register_locked, get_register_lock, 
    get_employee_locks, unlock_register, force_unlock_register
)
from app.helpers.shift_manager_compat import get_shift_status, close_shift as close_shift_helper
from app.helpers.register_close_db import save_register_close
from app.helpers.sale_security_validator import validate_session_active, validate_cart_before_close
from app.helpers.idempotency_helper import generate_close_idempotency_key
from app.helpers.register_session_service import RegisterSessionService
from app.helpers.sos_drawer_helper import (
    save_sos_request, can_request_drawer, _get_sos_file_path
)
from app import socketio
import uuid
import os
from app.helpers.financial_utils import to_decimal, round_currency, safe_float

logger = logging.getLogger(__name__)

@caja_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Selección de caja"""
    # Limpiar sesión de guardarropía si existe (para evitar conflictos)
    if session.get('guardarropia_logged_in'):
        session.pop('guardarropia_logged_in', None)
        session.pop('guardarropia_employee_id', None)
        session.pop('guardarropia_jornada_id', None)
        session.pop('guardarropia_employee_name', None)
    
    if not session.get('pos_logged_in'):
        return redirect(url_for('caja.login'))
    
    # Si hay una caja objetivo (desde /caja1, /caja2, /caja3), seleccionarla automáticamente
    target_register_id = session.pop('target_register_id', None)
    if target_register_id:
        # Intentar abrir la caja directamente
        try:
            # lock_register ya está importado al principio del archivo
            register_id = str(target_register_id)
            employee_id = session.get('pos_employee_id')
            
            # Verificar si la caja existe
            from app.models.pos_models import PosRegister
            register = PosRegister.query.filter(
                (PosRegister.id == register_id) | (PosRegister.code == str(register_id))
            ).first()
            
            if register and register.is_active:
                # Bloquear la caja para este empleado
                lock_result = lock_register(register_id, employee_id, session.get('pos_employee_name', 'Cajero'))
                if lock_result.get('success'):
                    session['pos_register_id'] = register_id
                    session['pos_register_name'] = register.name
                    return redirect(url_for('caja.sales'))
                else:
                    flash(f"No se pudo abrir la caja {register.name}: {lock_result.get('error', 'Error desconocido')}", "error")
            else:
                flash(f"Caja {target_register_id} no encontrada o inactiva", "error")
        except Exception as e:
            logger.error(f"Error al abrir caja objetivo {target_register_id}: {e}", exc_info=True)
            flash(f"Error al abrir la caja: {str(e)}", "error")
    
    # Verificar si es superadmin (para filtrar cajas superadmin_only)
    # En POS, el usuario puede ser admin o empleado regular
    # Verificar si hay sesión de admin activa
    is_superadmin = False
    if session.get('admin_logged_in'):
        username = session.get('admin_username', '').lower()
        is_superadmin = (username == 'sebagatica')
    
    # Obtener cajas de la BD primero
    from app.models.pos_models import PosRegister
    from flask import current_app
    
    # Mostrar TODAS las cajas activas (incluyendo de prueba) - igual que en desarrollo
    # Esto permite que las cajas creadas en producción sean visibles
    query = PosRegister.query.filter_by(is_active=True)
    
    # NO filtrar cajas de prueba - mostrarlas siempre (tanto en desarrollo como producción)
    # Las cajas de prueba se marcan visualmente con 🧪 pero están disponibles para uso
    
    db_registers = query.all()
    
    # Convertir a formato dict y filtrar superadmin_only
    registers = []
    for reg in db_registers:
        # Si es superadmin_only, solo mostrarlo a superadmin
        if reg.superadmin_only and not is_superadmin:
            continue
        registers.append({
            'id': str(reg.id),
            'name': reg.name,
            'code': reg.code,
            'superadmin_only': reg.superadmin_only,
            'is_test': reg.is_test
        })
    
    # Si no hay cajas en BD, usar defaults o API
    if not registers:
        default_registers = [
            {'id': '1', 'name': 'Caja 1', 'code': '1', 'superadmin_only': False},
            {'id': '2', 'name': 'Caja 2', 'code': '2', 'superadmin_only': False},
            {'id': '3', 'name': 'Caja 3', 'code': '3', 'superadmin_only': False},
            {'id': '4', 'name': 'Caja 4', 'code': '4', 'superadmin_only': False},
            {'id': '5', 'name': 'Caja 5', 'code': '5', 'superadmin_only': False},
            {'id': '6', 'name': 'Caja 6', 'code': '6', 'superadmin_only': False},
        ]
        
        try:
            api_registers = pos_service.get_registers()
            if api_registers and len(api_registers) > 0:
                # Agregar cajas de API (asumiendo que no son superadmin_only)
                for reg in api_registers:
                    if isinstance(reg, dict):
                        reg['superadmin_only'] = False
                        registers.append(reg)
                    else:
                        registers.append({
                            'id': str(getattr(reg, 'id', reg.get('id', ''))),
                            'name': getattr(reg, 'name', reg.get('name', f"Caja {getattr(reg, 'id', reg.get('id', ''))}")),
                            'code': str(getattr(reg, 'id', reg.get('id', ''))),
                            'superadmin_only': False
                        })
        except Exception as e:
            logger.error(f"Error al obtener cajas de API: {e}")
        
        # Si aún no hay cajas, usar defaults
        if not registers:
            registers = default_registers
    
    # Marcar cajas bloqueadas
    for reg in registers:
        reg_id = str(reg['id'])
        # Obtener información completa del bloqueo
        lock_info = get_register_lock(reg_id)
        if lock_info:
            reg['is_locked'] = True
            reg['locked_by'] = lock_info.get('employee_id')
            reg['locked_by_name'] = lock_info.get('employee_name')  # Nombre del cajero que bloqueó
            reg['locked_at'] = lock_info.get('locked_at')
            # Verificar si es MI bloqueo
            if str(lock_info.get('employee_id')) == str(session.get('pos_employee_id')):
                reg['is_locked_by_me'] = True
        else:
            reg['is_locked'] = False
            reg['locked_by'] = None
            reg['locked_by_name'] = None
            reg['locked_at'] = None
            reg['is_locked_by_me'] = False
    
    if request.method == 'POST':
        register_id = request.form.get('register_id')
        action = request.form.get('action')
        
        if not register_id:
            flash("Debes seleccionar una caja.", "error")
            return render_template('pos/register.html', registers=registers)
        
        # ⚠️ VALIDACIÓN: Verificar que la caja no sea superadmin_only si el usuario no es superadmin
        register_obj = PosRegister.query.filter(
            (PosRegister.id == register_id) | (PosRegister.code == str(register_id))
        ).first()
        
        if register_obj and register_obj.superadmin_only and not is_superadmin:
            flash("No tienes autorización para usar esta caja.", "error")
            logger.warning(f"⚠️ Intento de acceso no autorizado a caja SUPERADMIN por usuario no superadmin")
            return redirect(url_for('caja.register'))
        
        # Buscar nombre de la caja
        register_name = next((r['name'] for r in registers if str(r['id']) == str(register_id)), f"Caja {register_id}")
        
        employee_id = session.get('pos_employee_id')
        employee_name = session.get('pos_employee_name')
        
        # Verificar estado del bloqueo
        lock_info = get_register_lock(register_id)
        locked = lock_info is not None
        
        if locked:
            # Si está bloqueada por otro usuario
            if str(lock_info.get('employee_id')) != str(employee_id):
                locked_by_employee_id = lock_info.get('employee_id')
                locked_by_employee_name = lock_info.get('employee_name', 'otro cajero')
                flash(f"🔒 Esta caja está siendo usada por {locked_by_employee_name}. No puedes acceder a una caja que está en uso por otro cajero.", "error")
                return render_template('pos/register.html', registers=registers)
            
            # Si es mi bloqueo, permitir retomar siempre (puede ser por interrupción: apagón, caída de internet, etc.)
            # IMPORTANTE: Si hay un cierre pendiente, no prevenimos retomar porque puede haber sido una interrupción
            # El cierre pendiente solo previene abrir una NUEVA sesión, no retomar una existente
            logger.info(f"✅ Cajero {employee_id} retomando su propia caja {register_id} (puede ser por interrupción)")
            
            # P0-001: Verificar si existe RegisterSession activa, si no crear una
            from app.models.jornada_models import Jornada
            fecha_hoy = datetime.now(CHILE_TZ).strftime('%Y-%m-%d')
            jornada_actual = Jornada.query.filter_by(
                fecha_jornada=fecha_hoy,
                estado_apertura='abierto'
            ).first()
            
            if jornada_actual:
                active_session = RegisterSessionService.get_active_session(register_id, jornada_actual.id)
                if not active_session:
                    # Crear sesión si no existe (recuperación de interrupción)
                    success, register_session, msg = RegisterSessionService.open_session(
                        register_id=register_id,
                        employee_id=employee_id,
                        employee_name=employee_name,
                        jornada_id=jornada_actual.id
                    )
                    if success:
                        session['pos_register_session_id'] = register_session.id
                    else:
                        logger.warning(f"⚠️ No se pudo crear RegisterSession al retomar: {msg}")
                else:
                    session['pos_register_session_id'] = active_session.id
            
            session['pos_register_id'] = str(register_id)
            session['pos_register_name'] = register_name
            flash(f"Has retomado la {register_name}.", "success")
            return redirect(url_for('caja.sales'))
        
        # Si no está bloqueada, intentar bloquear
        # Verificar si hay confirmación (puede venir como 'confirmed'='true' o 'confirm_open'='1')
        confirmed = request.form.get('confirmed') == 'true' or request.form.get('confirm_open') == '1'
        
        # Verificar si es una caja de test
        is_test_register = register_obj and register_obj.is_test if register_obj else False
        
        if not confirmed:
            # Verificar si hay ventas previas en esta caja en el turno actual
            shift_status = get_shift_status()
            shift_date = shift_status.get('shift_date') if shift_status.get('is_open') else None
            
            previous_sales_count = 0
            previous_sales_total = 0.0
            has_other_employee_sales = False
            other_employee_name = ""
            
            # Para cajas de test, no validar ventas de otros usuarios (acceso libre)
            if shift_date and not is_test_register:
                try:
                    current_employee_id_str = str(employee_id) if employee_id else None
                    
                    # Excluir ventas de test y canceladas al verificar acceso
                    previous_sales = PosSale.query.filter(
                        PosSale.register_id == str(register_id),
                        PosSale.shift_date == shift_date,
                        PosSale.is_test == False,
                        PosSale.is_cancelled == False
                    ).all()
                    
                    previous_sales_count = len(previous_sales)
                    # CORRECCIÓN: Usar Decimal para suma de montos
                    from app.helpers.financial_utils import to_decimal, round_currency
                    previous_sales_total = round_currency(
                        sum(to_decimal(sale.total_amount or 0) for sale in previous_sales)
                    ) if previous_sales else 0.0
                    
                    # Verificar si hay ventas de otro cajero (excluyendo ventas de test y canceladas)
                    if previous_sales:
                        for sale in previous_sales:
                            # Ignorar ventas de test y canceladas
                            if sale.is_test or (hasattr(sale, 'is_cancelled') and sale.is_cancelled):
                                continue
                            
                            # Ignorar ventas de TEST AGENT o empleados de prueba
                            sale_employee_name = (sale.employee_name or '').upper()
                            if 'TEST' in sale_employee_name or 'AGENT' in sale_employee_name:
                                continue
                            
                            sale_employee_id = str(sale.employee_id) if sale.employee_id else None
                            if sale_employee_id and sale_employee_id != current_employee_id_str:
                                has_other_employee_sales = True
                                other_employee_name = sale.employee_name
                                break
                    
                    if has_other_employee_sales:
                        flash(f"Esta caja tiene ventas de {other_employee_name}. No puedes acceder.", "error")
                        return redirect(url_for('caja.register'))
                        
                except Exception as e:
                    logger.error(f"Error al verificar ventas previas: {e}")
            
            return render_template(
                'pos/confirm_register_open.html',
                register_id=register_id,
                register_name=register_name,
                previous_sales_count=previous_sales_count,
                previous_sales_total=previous_sales_total,
                shift_date=shift_date,
                is_zero=previous_sales_count == 0,
                has_other_employee_sales=has_other_employee_sales
            )
        
        # Confirmado - Bloquear (NUEVA caja)
        # Verificar si esta caja tiene un cierre pendiente antes de abrir una NUEVA sesión
        from app.models.pos_models import RegisterClose
        
        shift_status = get_shift_status()
        shift_date = shift_status.get('shift_date') if shift_status.get('is_open') else None
        
        has_pending_close = False
        if shift_date:
            pending_close = RegisterClose.query.filter_by(
                register_id=str(register_id),
                shift_date=shift_date,
                status='pending'
            ).first()
            
            if pending_close:
                has_pending_close = True
                logger.info(f"⚠️ Caja {register_id} tiene un cierre pendiente (ID: {pending_close.id}). No se puede abrir una nueva sesión hasta que el admin lo acepte.")
        
        if has_pending_close:
            flash(f"⏳ Esta caja tiene un cierre pendiente de revisión por el administrador. No puedes abrirla hasta que el cierre sea aceptado.", "warning")
            return redirect(url_for('caja.register'))
        
        # Verificar si tiene ventas en otras cajas (lógica simplificada del original)
        current_employee_id_str = str(employee_id) if employee_id else None
        
        if shift_date and current_employee_id_str:
             other_register_sales = PosSale.query.filter(
                PosSale.employee_id == current_employee_id_str,
                PosSale.register_id != str(register_id),
                PosSale.shift_date == shift_date
            ).first()
             
             if other_register_sales:
                 flash(f"Ya tienes ventas en otra caja (Caja {other_register_sales.register_id}). Debes usar esa.", "error")
                 return redirect(url_for('caja.register'))

        # Verificar bloqueos existentes
        existing_locks = get_employee_locks(employee_id)
        other_locks = [lock for lock in existing_locks if str(lock.register_id) != str(register_id)]
        
        if other_locks:
             flash(f"Ya tienes abierta la Caja {other_locks[0].register_id}. Debes cerrarla primero.", "error")
             return redirect(url_for('caja.register'))

        # P0-002: Validar que existe jornada activa antes de abrir caja
        from app.models.jornada_models import Jornada
        # IMPORTANT: No amarrar a "fecha de hoy". La jornada abierta es la fuente de verdad,
        # y en local puede haber jornadas abiertas con shift_date distinto.
        jornada_actual = Jornada.query.filter_by(
            estado_apertura='abierto'
        ).order_by(Jornada.fecha_jornada.desc()).first()
        
        if not jornada_actual:
            # En local/dev, permitir abrir Caja Test creando una jornada de prueba automáticamente
            try:
                local_only = bool(current_app.config.get('LOCAL_ONLY', False))
                enable_auto = bool(current_app.config.get('ENABLE_AUTO_OPEN_JORNADA', False))
                allow_auto_open = local_only or enable_auto

                if allow_auto_open:
                    # Usar shift_date si existe; fallback a hoy (Chile)
                    fecha = (shift_date or datetime.now(CHILE_TZ).strftime('%Y-%m-%d'))
                    jornada_actual = Jornada(
                        fecha_jornada=fecha,
                        tipo_turno='Test',
                        nombre_fiesta='Jornada Test (Local)',
                        horario_apertura_programado='00:00',
                        horario_cierre_programado='23:59',
                        estado_apertura='abierto',
                        abierto_en=datetime.utcnow(),
                        abierto_por=session.get('pos_employee_name') or 'local'
                    )
                    db.session.add(jornada_actual)
                    db.session.flush()
                    logger.warning(f"🧪 Jornada auto-creada en local: {jornada_actual.id} ({jornada_actual.fecha_jornada})")
                else:
                    flash("No hay jornada abierta. Debes abrir una jornada antes de abrir una caja.", "error")
                    return redirect(url_for('caja.register'))
            except Exception as e:
                logger.error(f"Error al auto-crear jornada en local: {e}", exc_info=True)
                flash("No hay jornada abierta. Debes abrir una jornada antes de abrir una caja.", "error")
                return redirect(url_for('caja.register'))
        
        if lock_register(register_id, employee_id, employee_name):
            # P0-001: Crear RegisterSession (estado explícito de caja)
            success, register_session, msg = RegisterSessionService.open_session(
                register_id=register_id,
                employee_id=employee_id,
                employee_name=employee_name,
                jornada_id=jornada_actual.id,
                initial_cash=None  # Opcional, se puede agregar después
            )
            
            if not success:
                # Si falla crear sesión, desbloquear caja
                unlock_register(register_id)
                flash(f"Error al abrir sesión de caja: {msg}", "error")
                return redirect(url_for('caja.register'))
            
            session['pos_register_id'] = str(register_id)
            session['pos_register_name'] = register_name
            session['pos_register_session_id'] = register_session.id  # Guardar ID de sesión
            
            # Verificar si se debe abrir cajón (si hay ventas previas)
            # ... (lógica omitida por brevedad, se asume manejo en frontend o siguiente paso)
            
            flash(f"Caja {register_name} abierta correctamente.", "success")
            return redirect(url_for('caja.sales'))
        else:
            flash("No se pudo bloquear la caja. Intenta nuevamente.", "error")
            
    return render_template('pos/register.html', registers=registers)


@caja_bp.route('/open-register-from-stats/<register_id>', methods=['GET'])
def open_register_from_stats(register_id):
    """Abrir caja directamente desde la página de estadísticas - acceso directo para admin"""
    # Verificar autenticación de admin
    if not session.get('admin_logged_in'):
        flash("Debes estar logueado como administrador para abrir una caja.", "error")
        return redirect(url_for('auth.login_admin'))
    
    # Verificar permisos de superadmin si la caja es superadmin_only
    from app.models.pos_models import PosRegister
    register_obj = PosRegister.query.filter(
        (PosRegister.id == register_id) | (PosRegister.code == str(register_id))
    ).first()
    
    if register_obj:
        if register_obj.superadmin_only:
            username = session.get('admin_username', '').lower()
            if username != 'sebagatica':
                flash("No tienes autorización para usar esta caja.", "error")
                return redirect(url_for('routes.admin_dashboard'))
    
    # Obtener información del admin
    admin_username = session.get('admin_username', 'Admin')
    
    # Si no está logueado en POS, crear sesión automática como admin
    if not session.get('pos_logged_in'):
        # Crear sesión de POS automática para admin
        # Usar un ID especial para admin (ej: "admin-{username}")
        admin_employee_id = f"admin-{admin_username.lower()}"
        session['pos_employee_id'] = admin_employee_id
        session['pos_employee_name'] = f"Admin: {admin_username}"
        session['pos_logged_in'] = True
        session['is_admin_session'] = True  # Marcar como sesión de admin
        logger.info(f"✅ Sesión POS automática creada para admin: {admin_username}")
        employee_id = admin_employee_id
        employee_name = f"Admin: {admin_username}"
    else:
        employee_id = session.get('pos_employee_id')
        employee_name = session.get('pos_employee_name', f"Admin: {admin_username}")
    
    # Verificar si la caja está bloqueada por otro usuario
    if is_register_locked(register_id):
        lock = get_register_lock(register_id)
        if lock and lock.get('employee_id') != employee_id:
            # Si es admin, puede forzar el desbloqueo
            if session.get('is_admin_session'):
                logger.info(f"⚠️ Caja bloqueada por {lock.get('employee_name', 'Usuario desconocido')}, admin forzando desbloqueo")
                unlock_register(register_id)
            else:
                flash(f"La caja está siendo usada por {lock.get('employee_name', 'otro usuario')}.", "warning")
                return redirect(url_for('routes.admin_dashboard'))
    
    # Bloquear la caja
    register_name = register_obj.name if register_obj else f'Caja {register_id}'
    if lock_register(register_id, employee_id, employee_name):
        session['pos_register_id'] = str(register_id)
        session['pos_register_name'] = register_name
        flash(f"Caja {register_name} abierta correctamente.", "success")
        logger.info(f"✅ Caja {register_name} abierta por admin {admin_username}")
        return redirect(url_for('caja.sales'))
    else:
        flash("No se pudo abrir la caja. Intenta nuevamente.", "error")
        return redirect(url_for('routes.admin_dashboard'))


@caja_bp.route('/close-register', methods=['GET'])
def close_register_view():
    """Vista para cierre de caja (blind close)"""
    if not session.get('pos_logged_in'):
        return redirect(url_for('caja.login'))
    
    register_id = session.get('pos_register_id')
    if not register_id:
        flash("No tienes una caja asignada.", "warning")
        return redirect(url_for('caja.register'))
    
    return render_template('pos/close_register.html')


@caja_bp.route('/api/open-cash-drawer', methods=['POST'])
def api_open_cash_drawer():
    """API: Abrir cajón de dinero manualmente"""
    if not session.get('pos_logged_in'):
        return jsonify({'success': False, 'error': 'No autenticado'}), 401
    
    try:
        printer_service = TicketPrinterService()
        success = printer_service.open_cash_drawer()
        
        if success:
            return jsonify({'success': True, 'message': 'Cajón abierto'})
        else:
            return jsonify({'success': False, 'error': 'No se pudo abrir el cajón'}), 500
    except Exception as e:
        logger.error(f"Error al abrir cajón: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@caja_bp.route('/api/register-summary', methods=['GET'])
def api_register_summary():
    """API: Obtener resumen de caja para cierre"""
    if not session.get('pos_logged_in'):
        return jsonify({'success': False, 'error': 'No autenticado'}), 401
    
    register_id = session.get('pos_register_id')
    if not register_id:
        return jsonify({'success': False, 'error': 'No hay caja asignada'}), 400
    
    try:
        shift_status = get_shift_status()
        shift_date = shift_status.get('shift_date')
        opened_at = shift_status.get('opened_at')  # Fallback al opened_at del turno
        
        if not shift_date:
            # Fallback a fecha actual si no hay turno (no debería pasar)
            shift_date = datetime.now(CHILE_TZ).strftime('%Y-%m-%d')
        
        # Obtener el momento en que se abrió ESTA caja específica (locked_at del bloqueo)
        try:
            lock_info = get_register_lock(register_id)
            if lock_info and lock_info.get('locked_at'):
                locked_at = lock_info.get('locked_at')
                if isinstance(locked_at, str):
                    try:
                        locked_at_dt = datetime.fromisoformat(locked_at.replace('Z', '+00:00'))
                        if locked_at_dt.tzinfo:
                            locked_at_dt = locked_at_dt.replace(tzinfo=None)
                        opened_at = locked_at_dt.strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        opened_at = locked_at
                elif isinstance(locked_at, datetime):
                    locked_at_naive = locked_at.replace(tzinfo=None) if locked_at.tzinfo else locked_at
                    opened_at = locked_at_naive.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    opened_at = str(locked_at) if locked_at else opened_at
        except Exception as e:
            logger.debug(f"No se pudo obtener locked_at del bloqueo para resumen: {e}")
        
        # P0-006, P0-016: Obtener ventas locales EXCLUYENDO cortesía, prueba y no_revenue
        register_sales = PosSale.query.filter_by(
            register_id=str(register_id),
            shift_date=shift_date
        ).filter(
            PosSale.is_cancelled == False,  # P0-008: Excluir canceladas
            PosSale.no_revenue == False,  # P0-016: Excluir no revenue
            PosSale.is_courtesy == False,  # P0-006: Excluir cortesías
            PosSale.is_test == False  # P0-006: Excluir pruebas
        ).all()
        
        # Usar los campos específicos de pago (payment_cash, payment_debit, payment_credit)
        # en lugar de payment_type, ya que una venta puede tener múltiples métodos de pago
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
                'register_name': session.get('pos_register_name', 'Caja'),
                'employee_name': session.get('pos_employee_name', 'Cajero'),
                'shift_date': shift_date,
                'opened_at': opened_at  # Ahora es el momento en que el trabajador abrió esta caja
            },
            'sales': [s.to_dict() for s in register_sales[:50]] # Simplificado
        })
    except Exception as e:
        logger.error(f"Error al obtener resumen de caja: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@caja_bp.route('/api/close-register', methods=['POST'])
def api_close_register():
    """API: Procesar cierre de caja"""
    if not session.get('pos_logged_in'):
        return jsonify({'success': False, 'error': 'No autenticado'}), 401
    
    try:
        is_valid, error = validate_session_active()
        if not is_valid:
            return jsonify({'success': False, 'error': error}), 401
        
        cart = session.get('pos_cart', [])
        is_valid, error = validate_cart_before_close(cart)
        if not is_valid:
            return jsonify({'success': False, 'error': error}), 400
        
        register_id = session.get('pos_register_id')
        employee_id = session.get('pos_employee_id')
        
        # P0-010: Validar estado de caja (debe estar OPEN)
        active_session = RegisterSessionService.get_active_session(register_id)
        if not active_session or not active_session.is_open():
            return jsonify({'success': False, 'error': 'La caja no está abierta. No se puede cerrar.'}), 403
        
        # P0-011: Idempotencia de cierre
        shift_date = active_session.shift_date
        idempotency_key_close = generate_close_idempotency_key(register_id, shift_date, employee_id)
        
        # Verificar si ya existe cierre con esta key
        from app.models.pos_models import RegisterClose
        existing_close = RegisterClose.query.filter_by(
            register_id=register_id,
            shift_date=shift_date
        ).filter(
            RegisterClose.idempotency_key_close == idempotency_key_close
        ).first()
        
        if existing_close:
            # Retornar cierre existente (idempotencia)
            logger.info(f"✅ Cierre duplicado detectado (idempotencia), retornando cierre existente: {existing_close.id}")
            return jsonify({
                'success': True,
                'message': 'Cierre ya procesado (idempotencia)',
                'close_id': existing_close.id,
                'redirect_url': url_for('home.index')
            }), 200
        
        data = request.get_json()
        actual_cash = float(data.get('actual_cash', 0))
        actual_debit = float(data.get('actual_debit', 0))
        actual_credit = float(data.get('actual_credit', 0))
        notes = data.get('notes', '')
        
        if actual_cash < 0 or actual_debit < 0 or actual_credit < 0:
            return jsonify({'success': False, 'error': 'Los montos no pueden ser negativos'}), 400
        
        # P0-009: CIERRE A CIEGAS - El backend calcula expected, el cajero NO lo ve
        # Reutilizar lógica de resumen
        # En una refactorización real, esto debería estar en un servicio
        summary_response = api_register_summary()
        if summary_response.status_code != 200:
            return jsonify({'success': False, 'error': 'Error al obtener resumen'}), 500
        
        summary_data = summary_response.get_json()
        summary = summary_data.get('summary', {})
        
        # P0-009: CIERRE A CIEGAS - Backend calcula expected pero NO se envía al cajero
        expected_cash = summary.get('total_cash', 0)
        expected_debit = summary.get('total_debit', 0)
        expected_credit = summary.get('total_credit', 0)
        
        diff_cash = float(actual_cash) - float(expected_cash)
        diff_debit = float(actual_debit) - float(expected_debit)
        diff_credit = float(actual_credit) - float(expected_credit)
        difference = float(diff_cash + diff_debit + diff_credit)
        
        # ==========================================
        # P1-011: Validar montos razonables
        # ==========================================
        # Validar que las diferencias no excedan un umbral razonable (50% del esperado o $10,000, lo que sea mayor)
        max_tolerance_percent = 0.5  # 50%
        max_tolerance_absolute = 10000.0  # $10,000
        
        expected_total = float(expected_cash + expected_debit + expected_credit)
        max_tolerance = max(expected_total * max_tolerance_percent, max_tolerance_absolute)
        
        if abs(difference) > max_tolerance:
            error_msg = f'Diferencia excesiva en cierre: ${difference:,.0f} (esperado: ${expected_total:,.0f}, tolerancia máxima: ${max_tolerance:,.0f})'
            logger.error(f"⚠️ P1-011: {error_msg}")
            from app.models.pos_models import SaleAuditLog
            import json as json_lib
            audit = SaleAuditLog(
                event_type='CLOSE_EXCESSIVE_DIFF',
                severity='error',
                actor_user_id=employee_id,
                actor_name=session.get('pos_employee_name', 'Cajero'),
                register_id=register_id,
                register_session_id=active_session.id,
                jornada_id=active_session.jornada_id,
                payload_json=json_lib.dumps({
                    'expected_total': expected_total,
                    'actual_total': float(actual_cash + actual_debit + actual_credit),
                    'difference': difference,
                    'max_tolerance': max_tolerance
                })
            )
            db.session.add(audit)
            db.session.commit()
            return jsonify({
                'success': False,
                'error': f'La diferencia es demasiado grande (${abs(difference):,.0f}). Por favor, verifica los montos e intenta nuevamente.'
            }), 400
        
        # P0-013: Registrar auditoría de cierre con diferencias
        from app.models.pos_models import SaleAuditLog
        import json as json_lib
        tolerance = 100.0
        if abs(difference) > tolerance:
            audit = SaleAuditLog(
                event_type='CLOSE_WITH_DIFF',
                severity='warning' if abs(difference) <= 2000 else 'error',
                actor_user_id=employee_id,
                actor_name=session.get('pos_employee_name', 'Cajero'),
                register_id=register_id,
                register_session_id=active_session.id,
                jornada_id=active_session.jornada_id,
                payload_json=json_lib.dumps({
                    'expected_cash': expected_cash,
                    'actual_cash': actual_cash,
                    'diff_cash': diff_cash,
                    'expected_debit': expected_debit,
                    'actual_debit': actual_debit,
                    'diff_debit': diff_debit,
                    'expected_credit': expected_credit,
                    'actual_credit': actual_credit,
                    'diff_credit': diff_credit,
                    'difference_total': difference,
                    'tolerance': tolerance
                })
            )
            db.session.add(audit)
            db.session.commit()
        
        # Log para debug
        logger.info(f"💰 Cálculo de diferencias: cash={diff_cash}, debit={diff_debit}, credit={diff_credit}, total={difference}")
        
        # Obtener el momento en que se abrió ESTA caja específica (locked_at del bloqueo)
        register_id = session.get('pos_register_id')
        opened_at = summary.get('opened_at')  # Fallback al opened_at del turno
        
        try:
            lock_info = get_register_lock(register_id)
            if lock_info and lock_info.get('locked_at'):
                # Usar el locked_at como opened_at (momento en que el trabajador abrió esta caja)
                locked_at = lock_info.get('locked_at')
                if isinstance(locked_at, str):
                    # Si es string, intentar parsear
                    try:
                        locked_at_dt = datetime.fromisoformat(locked_at.replace('Z', '+00:00'))
                        if locked_at_dt.tzinfo:
                            locked_at_dt = locked_at_dt.replace(tzinfo=None)
                        opened_at = locked_at_dt.strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        opened_at = locked_at
                elif isinstance(locked_at, datetime):
                    # Si ya es datetime, formatear
                    locked_at_naive = locked_at.replace(tzinfo=None) if locked_at.tzinfo else locked_at
                    opened_at = locked_at_naive.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    opened_at = str(locked_at) if locked_at else summary.get('opened_at')
                logger.info(f"✅ Usando locked_at como opened_at para cierre: {opened_at}")
        except Exception as e:
            logger.warning(f"⚠️ No se pudo obtener locked_at del bloqueo, usando opened_at del turno: {e}")
        
        # Guardar cierre - Asegurar que todos los valores sean float explícitamente
        close_register_data = {
            'register_id': register_id,
            'register_name': summary.get('register_name'),
            'employee_id': session.get('pos_employee_id'),
            'employee_name': summary.get('employee_name'),
            'shift_date': shift_date,  # Desde active_session
            'opened_at': active_session.opened_at.strftime('%Y-%m-%d %H:%M:%S') if active_session.opened_at else opened_at,
            'closed_at': datetime.now(CHILE_TZ).replace(tzinfo=None),
            'expected_cash': safe_float(expected_cash),
            'actual_cash': safe_float(actual_cash),
            'diff_cash': safe_float(diff_cash),
            'expected_debit': safe_float(expected_debit),
            'actual_debit': safe_float(actual_debit),
            'diff_debit': safe_float(diff_debit),
            'expected_credit': safe_float(expected_credit),
            'actual_credit': safe_float(actual_credit),
            'diff_credit': safe_float(diff_credit),
            'total_sales': int(summary.get('total_sales', 0)),
            # CORRECCIÓN: Usar Decimal para montos financieros
            'total_amount': safe_float(summary.get('total_amount', 0)),
            'difference_total': safe_float(difference),  # Usar Decimal para precisión
            'notes': notes,
            'idempotency_key_close': idempotency_key_close  # P0-011
        }
        
        # Log para verificar que se está guardando correctamente
        logger.info(f"💾 Guardando cierre con difference_total={close_register_data['difference_total']}")
        
        # Guardar cierre con status 'pending' - espera aceptación del admin
        # NO se desbloquea la caja todavía - el admin debe aceptar el cierre primero
        close_register_data['status'] = 'pending'  # Asegurar que quede pendiente
        register_close = save_register_close(close_register_data)
        
        # P0-013: Registrar auditoría de cierre declarado
        if register_close:
            audit = SaleAuditLog(
                event_type='BLIND_CLOSE_SUBMITTED',
                severity='info',
                actor_user_id=employee_id,
                actor_name=session.get('pos_employee_name', 'Cajero'),
                register_id=register_id,
                register_session_id=active_session.id,
                jornada_id=active_session.jornada_id,
                payload_json=json_lib.dumps({
                    'close_id': register_close.id,
                    'actual_cash': actual_cash,
                    'actual_debit': actual_debit,
                    'actual_credit': actual_credit
                })
            )
            db.session.add(audit)
            db.session.commit()
            
            # P0-010: Cerrar RegisterSession
            RegisterSessionService.close_session(
                active_session.id,
                session.get('pos_employee_name', 'Cajero'),
                employee_id
            )
        
        # Enviar notificación a admin
        if register_close:
            try:
                from app.helpers.notification_service import NotificationService
                
                # Determinar si es una diferencia grande (mayor a $2.000)
                diff = register_close.difference_total
                if abs(diff) > 2000:
                    NotificationService.notify_diferencia_grande(
                        cierre_id=register_close.id,
                        barra=register_close.register_name,
                        diferencia=diff
                    )
                else:
                    NotificationService.notify_cierre_pendiente(
                        cierre_id=register_close.id,
                        barra=register_close.register_name,
                        cajero=register_close.employee_name
                    )
            except Exception as e:
                logger.error(f"Error al enviar notificación de cierre: {e}")
        
        # Imprimir ticket de cierre
        try:
            printer_service = TicketPrinterService()
            printer_service.print_register_close_summary(
                register_name=summary.get('register_name'),
                employee_name=summary.get('employee_name'),
                shift_date=summary.get('shift_date'),
                opened_at=summary.get('opened_at'),
                closed_at=datetime.now(CHILE_TZ).strftime('%Y-%m-%d %H:%M:%S'),
                total_sales=summary.get('total_sales'),
                expected_cash=expected_cash,
                actual_cash=actual_cash,
                diff_cash=diff_cash,
                expected_debit=expected_debit,
                actual_debit=actual_debit,
                diff_debit=diff_debit,
                expected_credit=expected_credit,
                actual_credit=actual_credit,
                diff_credit=diff_credit,
                difference_total=difference,
                is_balanced=abs(difference) < 100, # Tolerancia de 100 pesos
                notes=notes
            )
        except Exception as e:
            logger.error(f"Error al imprimir cierre: {e}")
        
        # Desbloquear la caja después del cierre
        # El cajero cierra la caja y la libera para que esté disponible nuevamente
        unlock_success = unlock_register(register_id)
        if unlock_success:
            logger.info(f"✅ Caja {register_id} desbloqueada después del cierre.")
        else:
            logger.warning(f"⚠️ No se pudo desbloquear la caja {register_id} después del cierre.")
        
        # Limpiar sesión de caja pero mantener login
        session.pop('pos_register_id', None)
        session.pop('pos_register_name', None)
        session.pop('pos_cart', None)
        
        # Emitir evento socket
        socketio.emit('register_closed', {
            'register_id': close_register_data['register_id'],
            'employee_name': close_register_data['employee_name'],
            'difference': difference
        })
        
        # FASE 8: Emitir evento para visor de cajas
        socketio.emit('register_activity', {
            'register_id': close_register_data['register_id'],
            'action': 'closed',
            'cashier_name': close_register_data['employee_name'],
            'timestamp': datetime.now(CHILE_TZ).isoformat()
        }, namespace='/admin')
        
        # Emitir actualización de métricas del dashboard
        try:
            from app.helpers.dashboard_metrics_service import get_metrics_service
            metrics_service = get_metrics_service()
            metrics = metrics_service.get_all_metrics(use_cache=False)
            socketio.emit('metrics_update', {'metrics': metrics}, namespace='/admin_stats')
        except Exception as e:
            logger.warning(f"Error al emitir actualización de métricas: {e}")
        
        # P0-009: CIERRE A CIEGAS - Respuesta al cajero sin mostrar expected ni diferencias
        # Solo confirmar que se recibió correctamente
        is_admin = session.get('admin_logged_in', False)
        
        response_data = {
            'success': True,
            'message': 'Cierre recibido correctamente',
            'redirect_url': url_for('home.index')
        }
        
        # Solo admin ve comparación (opcional, para debugging)
        if is_admin and register_close:
            response_data['admin_data'] = {
                'expected_cash': float(expected_cash),
                'expected_debit': float(expected_debit),
                'expected_credit': float(expected_credit),
                'actual_cash': float(actual_cash),
                'actual_debit': float(actual_debit),
                'actual_credit': float(actual_credit),
                'diff_cash': float(diff_cash),
                'diff_debit': float(diff_debit),
                'diff_credit': float(diff_credit),
                'difference_total': float(difference),
                'close_id': register_close.id
            }
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error al cerrar caja: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@caja_bp.route('/close-shift', methods=['POST'])
def close_shift_route():
    """Cerrar turno completo (Admin)"""
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'error': 'No autorizado'}), 403
    
    try:
        success, message = close_shift_helper(closed_by=session.get('admin_username', 'admin'))
        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'success': False, 'error': message}), 400
    except Exception as e:
        logger.error(f"Error al cerrar turno: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@caja_bp.route('/api/request-sos-drawer', methods=['POST'])
def api_request_sos_drawer():
    """API: Solicitar apertura SOS"""
    if not session.get('pos_logged_in'):
        return jsonify({'success': False, 'error': 'No autenticado'}), 401
    
    try:
        employee_id = session.get('pos_employee_id')
        register_id = session.get('pos_register_id')
        
        can_request, error_message = can_request_drawer(employee_id, register_id)
        if not can_request:
            return jsonify({'success': False, 'error': error_message}), 429
        
        request_id = str(uuid.uuid4())
        sos_request = {
            'request_id': request_id,
            'register_id': register_id,
            'register_name': session.get('pos_register_name', 'Caja'),
            'employee_id': employee_id,
            'employee_name': session.get('pos_employee_name', 'Cajero'),
            'printer_name': session.get('pos_printer_name'),
            'requested_at': datetime.now(CHILE_TZ).isoformat(),
            'status': 'pending',
            'authorized_by': None,
            'authorized_at': None,
            'authorization_method': None
        }
        
        if save_sos_request(sos_request):
            return jsonify({
                'success': True, 
                'request_id': request_id, 
                'requires_authorization': True,
                'message': 'Solicitud enviada. Esperando autorización.'
            })
        else:
            return jsonify({'success': False, 'error': 'Error al guardar solicitud'}), 500
            
    except Exception as e:
        logger.error(f"Error SOS: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@caja_bp.route('/api/authorize-sos-drawer', methods=['POST'])
def api_authorize_sos_drawer():
    """API: Autorizar SOS con PIN"""
    if not session.get('pos_logged_in'):
        return jsonify({'success': False, 'error': 'No autenticado'}), 401
    
    try:
        data = request.get_json()
        request_id = data.get('request_id')
        pin = data.get('pin', '').strip()
        
        if not request_id or not pin:
            return jsonify({'success': False, 'error': 'Datos incompletos'}), 400
        
        SUPERADMIN_PIN = current_app.config.get('SUPERADMIN_PIN', '9999')
        if pin != SUPERADMIN_PIN:
            return jsonify({'success': False, 'error': 'PIN incorrecto'}), 401
        
        # Lógica simplificada de actualización de archivo JSON
        from app.helpers.production_check import is_production, get_safe_instance_path, ensure_not_production
        ensure_not_production("El sistema de solicitudes SOS desde archivo")
        instance_dir = get_safe_instance_path() or current_app.instance_path
        sos_file = os.path.join(instance_dir, 'sos_drawer_requests.json')
        
        if not os.path.exists(sos_file):
            return jsonify({'success': False, 'error': 'Solicitud no encontrada'}), 404
            
        with open(sos_file, 'r', encoding='utf-8') as f:
            requests_list = json.load(f)
            
        request_found = False
        for req in requests_list:
            if req.get('request_id') == request_id and req.get('status') == 'pending':
                req['status'] = 'authorized'
                req['authorized_by'] = 'Superadmin (Presencial)'
                req['authorized_at'] = datetime.now(CHILE_TZ).isoformat()
                request_found = True
                break
        
        if not request_found:
            return jsonify({'success': False, 'error': 'Solicitud no encontrada o procesada'}), 404
            
        with open(sos_file, 'w', encoding='utf-8') as f:
            json.dump(requests_list, f, indent=2, ensure_ascii=False)
            
        # Abrir cajón
        printer_service = TicketPrinterService()
        if printer_service.open_cash_drawer():
            return jsonify({'success': True, 'message': 'Cajón abierto'})
        else:
            return jsonify({'success': False, 'error': 'Error de impresora'}), 500
            
    except Exception as e:
        logger.error(f"Error autorizar SOS: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# MVP1: Rutas para apertura/cierre de sesión con arqueo
@caja_bp.route('/session/open', methods=['GET', 'POST'])
def session_open():
    """Abrir sesión de caja con fondo inicial"""
    if not session.get('pos_logged_in') and not session.get('admin_logged_in'):
        return redirect(url_for('auth.login_pos'))
    
    from app.models.pos_models import PosRegister
    from app.models.jornada_models import Jornada
    from app.helpers.shift_manager_compat import get_shift_status
    
    if request.method == 'POST':
        try:
            register_id = request.form.get('register_id', '').strip()
            initial_cash_str = request.form.get('initial_cash', '').strip()
            jornada_id_str = request.form.get('jornada_id', '').strip()
            
            if not register_id:
                flash('Debe seleccionar una caja', 'error')
                return redirect(url_for('caja.session_open'))
            
            # Validar que la caja existe
            register = PosRegister.query.get(int(register_id))
            if not register:
                flash('Caja no encontrada', 'error')
                return redirect(url_for('caja.session_open'))
            
            # Obtener jornada actual o la especificada
            jornada_id = None
            if jornada_id_str:
                jornada_id = int(jornada_id_str)
            else:
                # Buscar jornada abierta
                jornada_abierta = Jornada.query.filter_by(estado_apertura='abierto').order_by(
                    Jornada.fecha_jornada.desc()
                ).first()
                if jornada_abierta:
                    jornada_id = jornada_abierta.id
            
            if not jornada_id:
                flash('No hay jornada abierta. Debe abrir una jornada primero.', 'error')
                return redirect(url_for('caja.session_open'))
            
            # Parsear initial_cash
            initial_cash = None
            if initial_cash_str:
                try:
                    initial_cash = float(initial_cash_str)
                except ValueError:
                    flash('Monto inicial inválido', 'error')
                    return redirect(url_for('caja.session_open'))
            
            # Obtener empleado de la sesión
            employee_id = session.get('pos_employee_id') or session.get('admin_username', 'admin')
            employee_name = session.get('pos_employee_name') or session.get('admin_username', 'Admin')
            
            # Abrir sesión
            success, register_session, msg = RegisterSessionService.open_session(
                register_id=register_id,
                employee_id=str(employee_id),
                employee_name=employee_name,
                jornada_id=jornada_id,
                initial_cash=initial_cash
            )
            
            if success:
                session['pos_register_id'] = register_id
                session['pos_register_name'] = register.name
                session['pos_register_session_id'] = register_session.id
                flash(f'Sesión abierta correctamente. Fondo inicial: ${initial_cash:,.0f}' if initial_cash else 'Sesión abierta correctamente', 'success')
                return redirect(url_for('caja.sales'))
            else:
                flash(f'Error al abrir sesión: {msg}', 'error')
                return redirect(url_for('caja.session_open'))
                
        except Exception as e:
            logger.error(f"Error al abrir sesión: {e}", exc_info=True)
            flash(f'Error: {str(e)}', 'error')
            return redirect(url_for('caja.session_open'))
    
    # GET: Mostrar formulario
    registers = PosRegister.query.filter_by(is_active=True).order_by(PosRegister.name).all()
    jornadas_abiertas = Jornada.query.filter_by(estado_apertura='abierto').order_by(
        Jornada.fecha_jornada.desc()
    ).all()
    
    return render_template('caja/session/open.html', registers=registers, jornadas_abiertas=jornadas_abiertas)


@caja_bp.route('/session/close', methods=['GET', 'POST'])
def session_close():
    """Cerrar sesión de caja con arqueo"""
    if not session.get('pos_logged_in') and not session.get('admin_logged_in'):
        return redirect(url_for('auth.login_pos'))
    
    from app.models.pos_models import RegisterSession, PosRegister
    
    register_session_id = session.get('pos_register_session_id')
    if not register_session_id:
        flash('No hay sesión activa', 'error')
        return redirect(url_for('caja.register'))
    
    register_session = RegisterSession.query.get(register_session_id)
    if not register_session:
        flash('Sesión no encontrada', 'error')
        return redirect(url_for('caja.register'))
    
    if register_session.status != 'OPEN':
        flash(f'La sesión ya está cerrada (estado: {register_session.status})', 'error')
        return redirect(url_for('caja.register'))
    
    register = PosRegister.query.filter_by(code=register_session.register_id).first()
    
    if request.method == 'POST':
        try:
            # Obtener datos del formulario
            cash_count_raw = request.form.get('cash_count', '').strip()
            close_notes = request.form.get('close_notes', '').strip() or None
            incidents_raw = request.form.get('incidents', '').strip()
            
            # Parsear cash_count (JSON)
            cash_count = None
            if cash_count_raw:
                try:
                    cash_count = json.loads(cash_count_raw)
                except json.JSONDecodeError:
                    flash('Error: cash_count debe ser un JSON válido', 'error')
                    return redirect(url_for('caja.session_close'))
            
            # Parsear incidents (JSON array)
            incidents = None
            if incidents_raw:
                try:
                    incidents = json.loads(incidents_raw)
                except json.JSONDecodeError:
                    flash('Error: incidents debe ser un JSON válido', 'error')
                    return redirect(url_for('caja.session_close'))
            
            # Obtener empleado
            employee_id = session.get('pos_employee_id') or session.get('admin_username', 'admin')
            employee_name = session.get('pos_employee_name') or session.get('admin_username', 'Admin')
            
            # Cerrar sesión
            success, msg = RegisterSessionService.close_session(
                register_session_id=register_session_id,
                closed_by=employee_name,
                employee_id=str(employee_id),
                cash_count=cash_count,
                close_notes=close_notes,
                incidents=incidents
            )
            
            if success:
                # Limpiar sesión
                session.pop('pos_register_id', None)
                session.pop('pos_register_name', None)
                session.pop('pos_register_session_id', None)
                flash('Sesión cerrada correctamente', 'success')
                return redirect(url_for('caja.register'))
            else:
                flash(f'Error al cerrar sesión: {msg}', 'error')
                return redirect(url_for('caja.session_close'))
                
        except Exception as e:
            logger.error(f"Error al cerrar sesión: {e}", exc_info=True)
            flash(f'Error: {str(e)}', 'error')
            return redirect(url_for('caja.session_close'))
    
    # GET: Mostrar formulario de cierre
    # Obtener resumen de ventas para mostrar
    from app.models.pos_models import PosSale
    from sqlalchemy import func
    
    sales_summary = db.session.query(
        func.count(PosSale.id).label('total_sales'),
        func.sum(PosSale.payment_cash).label('total_cash'),
        func.sum(PosSale.payment_debit).label('total_debit'),
        func.sum(PosSale.payment_credit).label('total_credit')
    ).filter_by(
        register_id=register_session.register_id,
        shift_date=register_session.shift_date
    ).filter(
        PosSale.is_cancelled == False,
        PosSale.no_revenue == False
    ).first()
    
    summary = {
        'total_sales': sales_summary.total_sales or 0,
        'total_cash': float(sales_summary.total_cash or 0),
        'total_debit': float(sales_summary.total_debit or 0),
        'total_credit': float(sales_summary.total_credit or 0),
        'total_amount': float((sales_summary.total_cash or 0) + (sales_summary.total_debit or 0) + (sales_summary.total_credit or 0)),
        'initial_cash': float(register_session.initial_cash or 0),
        'expected_cash': float((register_session.initial_cash or 0) + (sales_summary.total_cash or 0))
    }
    
    return render_template('caja/session/close.html', register_session=register_session, register=register, summary=summary)

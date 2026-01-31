"""
Rutas de administración - Visor de Cajas en Tiempo Real (FASE 8)
"""
from flask import render_template, session, redirect, url_for, jsonify, current_app
from app.models.pos_models import PosRegister, RegisterSession, PosSale, PaymentAgent, PaymentIntent
from app.models.jornada_models import Jornada
from app.helpers.register_session_service import RegisterSessionService
from datetime import datetime
from app.helpers.timezone_utils import CHILE_TZ
from . import admin_bp  # Importar el blueprint existente


@admin_bp.route('/cajas/live')
def live_cash_registers():
    """Visor de cajas en tiempo real (FASE 8)"""
    # Solo admin/superadmin
    if not session.get('admin_logged_in'):
        return redirect(url_for('home.index'))
    
    # Verificar si es superadmin
    is_superadmin = False
    if session.get('admin_logged_in'):
        username = session.get('admin_username', '').lower()
        is_superadmin = (username == 'sebagatica')
    
    # Obtener todas las cajas activas
    registers = PosRegister.query.filter_by(is_active=True).all()
    
    # Filtrar superadmin_only
    visible_registers = []
    for reg in registers:
        if reg.superadmin_only and not is_superadmin:
            continue
        visible_registers.append(reg)
    
    return render_template('admin/live_cash_registers.html', 
                         registers=visible_registers,
                         is_superadmin=is_superadmin)


@admin_bp.route('/api/cajas/live/status')
def api_live_cash_registers_status():
    """API: Obtener estado de todas las cajas en tiempo real"""
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'No autorizado'}), 401
    
    try:
        # Verificar si es superadmin
        is_superadmin = False
        if session.get('admin_logged_in'):
            username = session.get('admin_username', '').lower()
            is_superadmin = (username == 'sebagatica')
        
        # Obtener jornada actual
        fecha_hoy = datetime.now(CHILE_TZ).strftime('%Y-%m-%d')
        jornada_actual = Jornada.query.filter_by(
            fecha_jornada=fecha_hoy,
            estado_apertura='abierto'
        ).first()
        
        jornada_id = jornada_actual.id if jornada_actual else None
        
        # Obtener todas las cajas activas
        registers = PosRegister.query.filter_by(is_active=True).all()
        
        registers_status = []
        for reg in registers:
            # Filtrar superadmin_only
            if reg.superadmin_only and not is_superadmin:
                continue
            
            # Obtener sesión activa
            active_session = None
            if jornada_id:
                active_session = RegisterSessionService.get_active_session(
                    register_id=str(reg.id),
                    jornada_id=jornada_id
                )
            
            # Obtener última venta (solo para admin, sin datos sensibles)
            last_sale = None
            if jornada_id:
                last_sale_obj = PosSale.query.filter_by(
                    register_id=str(reg.id),
                    jornada_id=jornada_id,
                    is_cancelled=False,
                    no_revenue=False
                ).order_by(PosSale.created_at.desc()).first()
                
                if last_sale_obj:
                    last_sale = {
                        'sale_id': last_sale_obj.id,
                        'created_at': last_sale_obj.created_at.isoformat() if last_sale_obj.created_at else None,
                        'items_count': len(last_sale_obj.items) if last_sale_obj.items else 0
                    }
            
            # Contar ventas del turno (sin mostrar totales)
            sales_count = 0
            if jornada_id:
                sales_count = PosSale.query.filter_by(
                    register_id=str(reg.id),
                    jornada_id=jornada_id,
                    is_cancelled=False,
                    no_revenue=False
                ).count()
            
            register_status = {
                'register_id': str(reg.id),
                'register_name': reg.name,
                'register_code': reg.code,
                'is_open': active_session is not None,
                'status': active_session.status if active_session else 'CLOSED',
                'cashier_id': active_session.employee_id if active_session else None,
                'cashier_name': active_session.employee_name if active_session else None,
                'opened_at': active_session.opened_at.isoformat() if active_session and active_session.opened_at else None,
                'sales_count': sales_count,
                'last_sale': last_sale
            }
            
            registers_status.append(register_status)
        
        return jsonify({
            'success': True,
            'registers': registers_status,
            'jornada_id': jornada_id,
            'timestamp': datetime.now(CHILE_TZ).isoformat()
        })
        
    except Exception as e:
        current_app.logger.error(f"Error al obtener estado de cajas: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/api/getnet/status')
def api_getnet_status():
    """
    API: Obtener estado de Getnet para un register_id específico
    Parámetro opcional: ?register_id=TEST001 (default: "1")
    """
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'No autorizado'}), 401
    
    try:
        from datetime import timedelta
        
        register_id = request.args.get('register_id', '1')
        register_id = str(register_id).strip()
        
        now = datetime.utcnow()
        
        # Buscar PaymentAgent más reciente para este register_id
        agent = PaymentAgent.query.filter_by(
            register_id=register_id
        ).order_by(PaymentAgent.last_heartbeat.desc()).first()
        
        # Calcular seconds_since_heartbeat
        seconds_since_heartbeat = None
        agent_data = None
        
        if agent:
            delta = now - agent.last_heartbeat
            seconds_since_heartbeat = int(delta.total_seconds())
            
            agent_data = {
                'online': seconds_since_heartbeat <= 300,  # Online si heartbeat < 5 min
                'agent_name': agent.agent_name,
                'last_heartbeat': agent.last_heartbeat.isoformat() if agent.last_heartbeat else None,
                'last_ip': agent.last_ip,
                'last_getnet_status': agent.last_getnet_status,
                'last_getnet_message': agent.last_getnet_message,
                'seconds_since_heartbeat': seconds_since_heartbeat
            }
        else:
            agent_data = {
                'online': False,
                'agent_name': None,
                'last_heartbeat': None,
                'last_ip': None,
                'last_getnet_status': None,
                'last_getnet_message': None,
                'seconds_since_heartbeat': None
            }
        
        # Buscar último PaymentIntent para este register_id
        last_intent = PaymentIntent.query.filter_by(
            register_id=register_id
        ).order_by(PaymentIntent.created_at.desc()).first()
        
        backend_data = {
            'ok': True,
            'last_payment_intent_at': last_intent.created_at.isoformat() if last_intent and last_intent.created_at else None,
            'last_payment_intent_status': last_intent.status if last_intent else None
        }
        
        # Determinar overall_status
        overall_status = "ERROR"
        
        if not agent:
            overall_status = "ERROR"
        elif seconds_since_heartbeat is None:
            overall_status = "ERROR"
        elif seconds_since_heartbeat > 300:
            overall_status = "ERROR"
        elif 60 < seconds_since_heartbeat <= 300:
            overall_status = "WARN"
        elif agent.last_getnet_status == 'ERROR':
            overall_status = "ERROR"
        elif agent.last_getnet_status == 'UNKNOWN':
            overall_status = "WARN"
        elif seconds_since_heartbeat <= 60 and agent.last_getnet_status == 'OK':
            overall_status = "OK"
        else:
            overall_status = "WARN"
        
        return jsonify({
            'register_id': register_id,
            'agent': agent_data,
            'backend': backend_data,
            'overall_status': overall_status
        })
        
    except Exception as e:
        current_app.logger.error(f"Error al obtener estado Getnet: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


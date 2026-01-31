"""
Rutas para administración de máquinas de pago (Getnet, etc.)
"""
from flask import render_template, request, jsonify, session, redirect, url_for, flash, current_app
from app.models import db
from app.models.pos_models import PosRegister, PaymentAgent, PaymentIntent
from app.blueprints.admin import admin_bp
import json
import logging

logger = logging.getLogger(__name__)


@admin_bp.route('/payment-machines')
def payment_machines_list():
    """Lista todas las máquinas de pago configuradas"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('auth.login_admin'))
    
    try:
        # Obtener todas las cajas que tienen configuración de pago
        registers = PosRegister.query.filter(
            PosRegister.is_active == True,
            PosRegister.provider_config.isnot(None)
        ).order_by(PosRegister.name).all()
        
        # Obtener estado de agentes para cada caja
        machines = []
        for register in registers:
            provider_config = {}
            if register.provider_config:
                try:
                    provider_config = json.loads(register.provider_config)
                except:
                    provider_config = {}
            
            # Obtener agente asociado (si existe)
            agent = PaymentAgent.query.filter_by(
                register_id=str(register.id)
            ).order_by(PaymentAgent.last_heartbeat.desc()).first()
            
            # Información de Getnet si está configurado
            getnet_info = None
            if 'GETNET' in provider_config:
                getnet_config = provider_config['GETNET']
                getnet_info = {
                    'mode': getnet_config.get('mode', 'unknown'),
                    'port': getnet_config.get('port', 'N/A'),
                    'baudrate': getnet_config.get('baudrate', 'N/A'),
                    'timeout_ms': getnet_config.get('timeout_ms', 'N/A')
                }
            
            # Preparar datos del agente
            agent_data = None
            if agent:
                agent_dict = agent.to_dict()
                agent_data = agent_dict
            
            # Obtener estadísticas de movimientos recientes (últimas 24 horas)
            from datetime import datetime, timedelta
            from sqlalchemy import func, case
            last_24h = datetime.utcnow() - timedelta(hours=24)
            
            payments_stats = db.session.query(
                func.count(PaymentIntent.id).label('total'),
                func.sum(PaymentIntent.amount_total).label('total_amount'),
                func.sum(case(
                    (PaymentIntent.status == PaymentIntent.STATUS_APPROVED, PaymentIntent.amount_total),
                    else_=0
                )).label('approved_amount'),
                func.sum(case(
                    (PaymentIntent.status == PaymentIntent.STATUS_DECLINED, 1),
                    else_=0
                )).label('declined_count')
            ).filter(
                PaymentIntent.register_id == str(register.id),
                PaymentIntent.created_at >= last_24h
            ).first()
            
            payments_info = {
                'total': payments_stats.total or 0,
                'total_amount': float(payments_stats.total_amount or 0),
                'approved_amount': float(payments_stats.approved_amount or 0),
                'declined_count': payments_stats.declined_count or 0
            }
            
            # Obtener último movimiento
            last_payment = PaymentIntent.query.filter_by(
                register_id=str(register.id)
            ).order_by(PaymentIntent.created_at.desc()).first()
            
            last_payment_info = None
            if last_payment:
                last_payment_info = {
                    'id': str(last_payment.id),
                    'amount': float(last_payment.amount_total),
                    'status': last_payment.status,
                    'created_at': last_payment.created_at.isoformat() if last_payment.created_at else None,
                    'provider': last_payment.provider,
                    'auth_code': last_payment.auth_code
                }
            
            machines.append({
                'register': register,
                'getnet_config': getnet_info,
                'agent': agent_data,
                'payments_stats': payments_info,
                'last_payment': last_payment_info
            })
        
        return render_template('admin/payment_machines/list.html', machines=machines)
    
    except Exception as e:
        logger.error(f"Error al listar máquinas de pago: {e}", exc_info=True)
        flash(f'Error al cargar máquinas de pago: {str(e)}', 'error')
        return redirect(url_for('routes.admin_dashboard'))


@admin_bp.route('/payment-machines/<int:register_id>/edit', methods=['GET', 'POST'])
def payment_machines_edit(register_id):
    """Editar configuración de máquina de pago"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('auth.login_admin'))
    
    register = PosRegister.query.get_or_404(register_id)
    
    if request.method == 'POST':
        try:
            # Leer configuración actual
            provider_config = {}
            if register.provider_config:
                try:
                    provider_config = json.loads(register.provider_config)
                except:
                    provider_config = {}
            
            # Actualizar configuración de Getnet
            getnet_mode = request.form.get('getnet_mode', '').strip()
            getnet_port = request.form.get('getnet_port', '').strip()
            getnet_baudrate = request.form.get('getnet_baudrate', '').strip()
            getnet_timeout_ms = request.form.get('getnet_timeout_ms', '').strip()
            
            if getnet_mode == 'serial':
                # Validar que port esté presente
                if not getnet_port:
                    flash('Error: Puerto COM es requerido para modo serial', 'error')
                    return render_template('admin/payment_machines/edit.html', register=register, provider_config=provider_config)
                
                # Actualizar configuración Getnet
                if 'GETNET' not in provider_config:
                    provider_config['GETNET'] = {}
                
                provider_config['GETNET']['mode'] = 'serial'
                provider_config['GETNET']['port'] = getnet_port
                
                if getnet_baudrate:
                    try:
                        provider_config['GETNET']['baudrate'] = int(getnet_baudrate)
                    except:
                        provider_config['GETNET']['baudrate'] = 115200
                else:
                    provider_config['GETNET']['baudrate'] = 115200
                
                if getnet_timeout_ms:
                    try:
                        provider_config['GETNET']['timeout_ms'] = int(getnet_timeout_ms)
                    except:
                        provider_config['GETNET']['timeout_ms'] = 30000
                else:
                    provider_config['GETNET']['timeout_ms'] = 30000
            elif getnet_mode == 'manual':
                if 'GETNET' not in provider_config:
                    provider_config['GETNET'] = {}
                provider_config['GETNET']['mode'] = 'manual'
            
            # Guardar configuración
            register.provider_config = json.dumps(provider_config, ensure_ascii=False)
            register.updated_at = db.func.now()
            db.session.commit()
            
            logger.info(f"✅ Configuración de pago actualizada para caja {register.id} ({register.name})")
            flash(f'Configuración de máquina de pago actualizada correctamente para {register.name}', 'success')
            return redirect(url_for('admin.payment_machines_list'))
        
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error al actualizar configuración de pago: {e}", exc_info=True)
            flash(f'Error al actualizar configuración: {str(e)}', 'error')
    
    # GET: Mostrar formulario
    provider_config = {}
    if register.provider_config:
        try:
            provider_config = json.loads(register.provider_config)
        except:
            provider_config = {}
    
    getnet_config = provider_config.get('GETNET', {}) if provider_config else {}
    
    return render_template('admin/payment_machines/edit.html', 
                         register=register, 
                         getnet_config=getnet_config)


@admin_bp.route('/api/payment-machines/<int:register_id>/test-connection', methods=['POST'])
def test_payment_machine_connection(register_id):
    """Probar conexión con máquina de pago"""
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'error': 'No autorizado'}), 401
    
    try:
        register = PosRegister.query.get_or_404(register_id)
        
        # Obtener configuración
        provider_config = {}
        if register.provider_config:
            try:
                provider_config = json.loads(register.provider_config)
            except:
                pass
        
        getnet_config = provider_config.get('GETNET', {})
        
        if getnet_config.get('mode') != 'serial':
            return jsonify({
                'success': False,
                'error': 'Solo se puede probar conexión en modo serial'
            }), 400
        
        port = getnet_config.get('port')
        if not port:
            return jsonify({
                'success': False,
                'error': 'Puerto COM no configurado'
            }), 400
        
        # Verificar estado del agente
        agent = PaymentAgent.query.filter_by(
            register_id=str(register_id)
        ).order_by(PaymentAgent.last_heartbeat.desc()).first()
        
        if not agent:
            return jsonify({
                'success': False,
                'error': 'No hay agente conectado para esta caja',
                'details': 'El agente debe estar corriendo en Windows para probar la conexión'
            }), 400
        
        # Verificar estado de Getnet según el agente
        getnet_status = agent.last_getnet_status
        getnet_message = agent.last_getnet_message
        
        if getnet_status == 'OK':
            return jsonify({
                'success': True,
                'message': 'Conexión exitosa',
                'details': getnet_message or 'Terminal Getnet conectado y respondiendo',
                'port': port,
                'agent_status': 'online',
                'last_heartbeat': agent.last_heartbeat.isoformat() if agent.last_heartbeat else None
            })
        elif getnet_status == 'ERROR':
            return jsonify({
                'success': False,
                'error': 'Error de conexión',
                'details': getnet_message or 'Error al conectar con terminal Getnet',
                'port': port,
                'agent_status': 'online',
                'last_heartbeat': agent.last_heartbeat.isoformat() if agent.last_heartbeat else None
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Estado desconocido',
                'details': getnet_message or 'No se pudo verificar el estado del terminal',
                'port': port,
                'agent_status': 'online',
                'last_heartbeat': agent.last_heartbeat.isoformat() if agent.last_heartbeat else None
            })
    
    except Exception as e:
        logger.error(f"Error al probar conexión: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admin_bp.route('/api/payment-machines/<int:register_id>/test-payment', methods=['POST'])
def test_payment_machine_payment(register_id):
    """Ejecutar un pago de prueba directo con Getnet"""
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'error': 'No autorizado'}), 401
    
    try:
        from datetime import datetime
        import uuid
        import json as json_lib
        
        register = PosRegister.query.get_or_404(register_id)
        
        # Obtener datos del request
        data = request.get_json(silent=True) or {}
        amount = data.get('amount', 100)  # Default $100 CLP
        
        try:
            amount = float(amount)
            if amount <= 0:
                return jsonify({
                    'success': False,
                    'error': 'El monto debe ser mayor a 0'
                }), 400
        except (ValueError, TypeError):
            return jsonify({
                'success': False,
                'error': 'Monto inválido'
            }), 400
        
        # Verificar que hay agente conectado
        agent = PaymentAgent.query.filter_by(
            register_id=str(register_id)
        ).order_by(PaymentAgent.last_heartbeat.desc()).first()
        
        if not agent:
            return jsonify({
                'success': False,
                'error': 'No hay agente conectado para esta caja',
                'details': 'El agente debe estar corriendo en Windows para procesar el pago'
            }), 400
        
        # Verificar que Getnet esté OK
        if agent.last_getnet_status != 'OK':
            return jsonify({
                'success': False,
                'error': f'Getnet no está disponible (estado: {agent.last_getnet_status})',
                'details': agent.last_getnet_message or 'Verifica la conexión del terminal Getnet'
            }), 400
        
        # Crear PaymentIntent de prueba
        test_cart = [{
            'product_id': 'TEST',
            'name': 'Prueba de Pago',
            'quantity': 1,
            'price': amount,
            'unit_price': amount
        }]
        
        import hashlib
        cart_json = json_lib.dumps(test_cart, ensure_ascii=False)
        cart_hash = hashlib.sha256(cart_json.encode()).hexdigest()
        
        test_intent = PaymentIntent(
            id=uuid.uuid4(),
            register_id=str(register_id),
            register_session_id=None,
            employee_id='admin',
            employee_name='Administrador (Prueba)',
            amount_total=amount,
            currency='CLP',
            cart_json=cart_json,
            cart_hash=cart_hash,
            provider='GETNET',
            status=PaymentIntent.STATUS_READY,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.session.add(test_intent)
        db.session.commit()
        
        logger.info(f"✅ PaymentIntent de prueba creado: {test_intent.id} amount={amount} register={register_id}")
        
        return jsonify({
            'success': True,
            'message': 'Pago de prueba iniciado',
            'intent_id': str(test_intent.id),
            'amount': amount,
            'details': 'El agente procesará el pago automáticamente. El terminal mostrará el monto.'
        })
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error al crear pago de prueba: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


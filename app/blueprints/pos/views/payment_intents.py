"""
Rutas para PaymentIntent - Sistema de intenciones de pago con agente local
"""
import logging
import json
import hashlib
from datetime import datetime
from flask import request, jsonify, session, current_app
from app.blueprints.pos import caja_bp
from app.models import db
from app.models.pos_models import PaymentIntent, PosSale, PosSaleItem, PosRegister, PaymentAgent
from app.helpers.rate_limiter import rate_limit
from app.helpers.sale_security_validator import comprehensive_sale_validation
from app.helpers.register_session_service import RegisterSessionService
from app.helpers.financial_utils import to_decimal, round_currency
from app.application.services.service_factory import get_shift_service
from app.models.jornada_models import Jornada

logger = logging.getLogger(__name__)


def calculate_cart_hash(cart: list) -> str:
    """Calcula hash SHA256 del carrito para idempotencia"""
    cart_str = json.dumps(cart, sort_keys=True)
    return hashlib.sha256(cart_str.encode('utf-8')).hexdigest()


def verify_agent_auth() -> bool:
    """
    Verifica autenticación del agente.

    Acepta:
    - Header: X-AGENT-KEY
    - Parámetro: agent_key (querystring)
    - (Compat) JSON body: agent_key
    """
    agent_key = request.headers.get('X-AGENT-KEY', '') or request.args.get('agent_key', '')
    if not agent_key:
        try:
            body = request.get_json(silent=True) or {}
            agent_key = body.get('agent_key', '') or ''
        except Exception:
            agent_key = ''
    expected_key = current_app.config.get('AGENT_API_KEY')
    
    if not expected_key:
        logger.warning("⚠️ AGENT_API_KEY not configured")
        return False
    
    return agent_key == expected_key


@caja_bp.route('/api/payment/intents', methods=['POST'])
@rate_limit(max_requests=30, window_seconds=60)
def create_payment_intent():
    """
    Crear PaymentIntent con status READY
    
    Body esperado:
    {
        "register_id": "1",
        "provider": "GETNET",
        "amount_total": 1500.0
    }
    
    Valida:
    - register_id existe en PosRegister
    - amount_total > 0
    """
    if not session.get('pos_logged_in'):
        return jsonify({'success': False, 'error': 'No autenticado'}), 401
    
    try:
        data = request.get_json() or {}
        register_id = data.get('register_id')
        provider = data.get('provider', 'GETNET')
        amount_total = data.get('amount_total')
        
        # Validar register_id
        if not register_id:
            return jsonify({'success': False, 'error': 'register_id requerido'}), 400
        
        register_id = str(register_id)
        
        # Validar que register_id existe en PosRegister
        register_obj = PosRegister.query.filter(
            (PosRegister.id == register_id) | (PosRegister.code == register_id)
        ).first()
        
        if not register_obj:
            return jsonify({'success': False, 'error': f'register_id {register_id} no existe'}), 400
        
        # Validar amount_total
        if amount_total is None:
            return jsonify({'success': False, 'error': 'amount_total requerido'}), 400
        
        try:
            amount_total = float(amount_total)
        except (ValueError, TypeError):
            return jsonify({'success': False, 'error': 'amount_total debe ser un número'}), 400
        
        if amount_total <= 0:
            return jsonify({'success': False, 'error': 'amount_total debe ser mayor a 0'}), 400
        
        # Obtener datos de sesión si están disponibles
        employee_id = session.get('pos_employee_id')
        employee_name = session.get('pos_employee_name', 'Cajero')
        register_session_id = session.get('pos_register_session_id')
        
        # Obtener carrito del body o de la sesión
        cart = data.get('cart') or session.get('pos_cart', [])
        cart_json = None
        cart_hash = None
        if cart:
            try:
                import json as json_lib
                cart_json = json_lib.dumps(cart, ensure_ascii=False, sort_keys=True)
                cart_hash = calculate_cart_hash(cart)
            except Exception as e:
                logger.warning(f"No se pudo serializar cart para PaymentIntent: {e}")
        else:
            # Si no hay carrito, crear uno vacío (puede ser válido para algunos casos)
            cart_json = '[]'
            cart_hash = calculate_cart_hash([])
        
        # Crear PaymentIntent
        intent = PaymentIntent(
            register_id=register_id,
            register_session_id=register_session_id,
            employee_id=employee_id,
            employee_name=employee_name,
            amount_total=amount_total,
            currency='CLP',
            provider=provider,
            status=PaymentIntent.STATUS_READY,
            cart_json=cart_json,
            cart_hash=cart_hash,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.session.add(intent)
        db.session.commit()
        
        # LOG con formato específico solicitado
        current_app.logger.info(
            f"[PAYMENT_INTENT] READY→ id={intent.id} register={intent.register_id} amount={intent.amount_total}"
        )
        
        return jsonify({
            'success': True,
            'intent_id': str(intent.id)
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error al crear PaymentIntent: {e}", exc_info=True)
        return jsonify({'success': False, 'error': f'Error interno: {str(e)}'}), 500


@caja_bp.route('/api/payment/intents/<uuid:intent_id>/cancel', methods=['POST'])
@rate_limit(max_requests=10, window_seconds=60)
def cancel_payment_intent(intent_id):
    """Cancelar PaymentIntent si aún no está APPROVED"""
    if not session.get('pos_logged_in'):
        return jsonify({'success': False, 'error': 'No autenticado'}), 401
    
    try:
        intent = PaymentIntent.query.get(intent_id)
        if not intent:
            return jsonify({'success': False, 'error': 'Intent no encontrado'}), 404
        
        # Verificar que pertenece a la caja actual
        register_id = session.get('pos_register_id')
        register_id = str(register_id) if register_id is not None else None
        if intent.register_id != register_id:
            return jsonify({'success': False, 'error': 'Intent no pertenece a esta caja'}), 403
        
        if not intent.can_cancel():
            return jsonify({
                'success': False,
                'error': f'Intent no puede cancelarse (estado: {intent.status})'
            }), 400
        
        intent.status = PaymentIntent.STATUS_CANCELLED
        intent.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        logger.info(f"✅ PaymentIntent cancelado: {intent_id}")
        
        return jsonify({
            'success': True,
            'intent_id': str(intent.id),
            'status': intent.status,
            'message': 'Intent cancelado exitosamente'
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error al cancelar PaymentIntent: {e}", exc_info=True)
        return jsonify({'success': False, 'error': f'Error interno: {str(e)}'}), 500


@caja_bp.route('/api/payment/intents/<uuid:intent_id>/status', methods=['GET'])
@rate_limit(max_requests=60, window_seconds=60)
def get_payment_intent_status(intent_id):
    """Obtener estado de PaymentIntent (para polling desde UI)"""
    if not session.get('pos_logged_in'):
        return jsonify({'success': False, 'error': 'No autenticado'}), 401
    
    try:
        intent = PaymentIntent.query.get(intent_id)
        if not intent:
            return jsonify({'success': False, 'error': 'Intent no encontrado'}), 404
        
        # Verificar que pertenece a la caja actual
        register_id = session.get('pos_register_id')
        register_id = str(register_id) if register_id is not None else None
        if intent.register_id != register_id:
            return jsonify({'success': False, 'error': 'Intent no pertenece a esta caja'}), 403
        
        # Log para debugging
        current_app.logger.debug(
            f"[PAYMENT_INTENT] Status check→ id={intent.id} status={intent.status} register={intent.register_id}"
        )
        
        return jsonify({
            'success': True,
            'intent_id': str(intent.id),
            'status': intent.status,
            'amount_total': float(intent.amount_total),
            'provider_ref': intent.provider_ref,
            'auth_code': intent.auth_code,
            'error_code': intent.error_code,
            'error_message': intent.error_message,
            'created_at': intent.created_at.isoformat() if intent.created_at else None,
            'updated_at': intent.updated_at.isoformat() if intent.updated_at else None,
            'approved_at': intent.approved_at.isoformat() if intent.approved_at else None,
            # Incluir también en formato 'intent' para compatibilidad
            'intent': {
                'id': str(intent.id),
                'status': intent.status,
                'amount_total': float(intent.amount_total),
                'provider_ref': intent.provider_ref,
                'auth_code': intent.auth_code,
                'error_code': intent.error_code,
                'error_message': intent.error_message,
            }
        })
        
    except Exception as e:
        logger.error(f"Error al obtener estado de PaymentIntent: {e}", exc_info=True)
        return jsonify({'success': False, 'error': f'Error interno: {str(e)}'}), 500


def _process_agent_result_payload(data: dict):
    """Lógica común para aplicar el resultado del agente a un PaymentIntent."""
    if not data:
        return jsonify({'success': False, 'error': 'Body JSON requerido'}), 400

    intent_id_str = data.get('intent_id')
    status = data.get('status')
    provider_ref = data.get('provider_ref')
    auth_code = data.get('auth_code')
    error_code = data.get('error_code')
    error_message = data.get('error_message')

    if not intent_id_str:
        return jsonify({'success': False, 'error': 'intent_id requerido'}), 400

    if status not in [PaymentIntent.STATUS_APPROVED, PaymentIntent.STATUS_DECLINED, PaymentIntent.STATUS_ERROR]:
        return jsonify({'success': False, 'error': f'status inválido: {status}'}), 400

    # Obtener intent
    import uuid
    intent_id = uuid.UUID(intent_id_str)
    intent = PaymentIntent.query.get(intent_id)

    if not intent:
        return jsonify({'success': False, 'error': 'Intent no encontrado'}), 404

    if intent.status != PaymentIntent.STATUS_IN_PROGRESS:
        return jsonify({
            'success': False,
            'error': f'Intent no está en estado IN_PROGRESS (actual: {intent.status})'
        }), 400

    # Actualizar intent
    intent.status = status
    intent.provider_ref = provider_ref
    intent.auth_code = auth_code
    intent.error_code = error_code
    intent.error_message = error_message
    intent.updated_at = datetime.utcnow()

    if status == PaymentIntent.STATUS_APPROVED:
        # Agente SOLO marca APPROVED. La venta se crea desde la UI POS (sale/create)
        # para mantener sesión/validaciones y evitar crear ventas "fantasma" si la UI cae.
        intent.approved_at = datetime.utcnow()
        db.session.commit()
        current_app.logger.info(
            f"[PAYMENT_INTENT] APPROVED→ id={intent.id} register={intent.register_id} amount={intent.amount_total} auth_code={auth_code} provider_ref={provider_ref}"
        )
        logger.info(f"✅ PaymentIntent APPROVED por agente: {intent_id} - Frontend debe detectar y crear venta")
        return jsonify({
            'success': True,
            'intent_id': str(intent.id),
            'intent_status': 'APPROVED',
            'status': 'APPROVED',  # Duplicado para compatibilidad con frontend
            'message': 'Pago aprobado (agent). Esperando confirmación POS.'
        })

    # DECLINED / ERROR
    db.session.commit()
    logger.info(f"✅ PaymentIntent {status}: {intent_id} - NO se creó venta")
    return jsonify({
        'success': True,
        'intent_id': str(intent.id),
        'intent_status': status,
        'error_code': error_code,
        'error_message': error_message,
        'message': f'Pago {status.lower()}'
    })


@caja_bp.route('/api/payment/intents/<uuid:intent_id>', methods=['GET'])
@rate_limit(max_requests=60, window_seconds=60)
def get_payment_intent(intent_id):
    """
    Alias simple para polling desde UI:
      GET /caja/api/payment/intents/<intent_id>
    (mismo payload que /status)
    """
    return get_payment_intent_status(intent_id)


@caja_bp.route('/api/payment/agent/pending', methods=['GET'])
@rate_limit(max_requests=120, window_seconds=60)  # Aumentado para permitir polling cada 0.5s
def agent_get_pending():
    """
    Obtener PaymentIntent pendiente más antiguo para una caja (AGENT ONLY)
    
    Autenticación: X-AGENT-KEY header
    Al entregar, cambia status a IN_PROGRESS y lockea
    """
    if not verify_agent_auth():
        return jsonify({'success': False, 'error': 'Autenticación inválida'}), 401
    
    try:
        register_id = request.args.get('register_id')
        if not register_id:
            return jsonify({'success': False, 'error': 'register_id requerido'}), 400
        
        # Buscar intent más antiguo con status READY para esta caja
        intent = PaymentIntent.query.filter_by(
            register_id=register_id,
            status=PaymentIntent.STATUS_READY
        ).order_by(PaymentIntent.created_at.asc()).first()
        
        if not intent:
            return jsonify({
                'success': True,
                'pending': False,
                'message': 'No hay intents pendientes'
            })
        
        # Lockear intent (cambiar a IN_PROGRESS)
        agent_id = request.headers.get('X-AGENT-ID', 'unknown')
        intent.status = PaymentIntent.STATUS_IN_PROGRESS
        intent.locked_by_agent = agent_id
        intent.locked_at = datetime.utcnow()
        intent.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        logger.info(f"✅ Agent {agent_id} tomó intent {intent.id} para register {register_id}")
        
        # Parsear cart_json
        cart_dict = None
        if intent.cart_json:
            try:
                cart_dict = json.loads(intent.cart_json)
            except:
                cart_dict = None
        
        return jsonify({
            'success': True,
            'pending': True,
            'intent_id': str(intent.id),
            'register_id': intent.register_id,
            'amount_total': float(intent.amount_total),
            'currency': intent.currency,
            'cart': cart_dict,
            'created_at': intent.created_at.isoformat() if intent.created_at else None,
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error al obtener intent pendiente: {e}", exc_info=True)
        return jsonify({'success': False, 'error': f'Error interno: {str(e)}'}), 500


@caja_bp.route('/api/payment/agent/result', methods=['POST'])
@rate_limit(max_requests=30, window_seconds=60)
def agent_report_result():
    """
    Reportar resultado de pago desde agente local (AGENT ONLY)
    
    Si status=APPROVED:
        - Marcar intent APPROVED
        - Crear PosSale desde cart_json
        - Aplicar inventario
        - Asociar register_id/session_id/employee_id
    
    Si DECLINED/ERROR:
        - Marcar intent DECLINED/ERROR
        - NO crear venta, NO aplicar inventario
    """
    if not verify_agent_auth():
        return jsonify({'success': False, 'error': 'Autenticación inválida'}), 401
    
    try:
        data = request.get_json(silent=True) or {}
        return _process_agent_result_payload(data)
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error al reportar resultado de pago: {e}", exc_info=True)
        return jsonify({'success': False, 'error': f'Error interno: {str(e)}'}), 500


@caja_bp.route('/api/getnet/pending', methods=['GET'])
@rate_limit(max_requests=30, window_seconds=60)
def getnet_pending_compat():
    """
    Endpoint compat para agentes antiguos:
    - GET /api/getnet/pending?register_id=1
    - Auth: X-AGENT-KEY o agent_key
    Respuesta:
      {hasPayment:false}
      o {hasPayment:true, paymentId:<intent_id>, amount:<int CLP>}
    """
    if not verify_agent_auth():
        return jsonify({'success': False, 'error': 'Autenticación inválida'}), 401

    try:
        register_id = request.args.get('register_id') or '1'
        register_id = str(register_id)
        agent_id = request.headers.get('X-AGENT-ID', 'unknown')

        intent = PaymentIntent.query.filter_by(
            register_id=register_id,
            status=PaymentIntent.STATUS_READY
        ).order_by(PaymentIntent.created_at.asc()).first()

        if not intent:
            return jsonify({'hasPayment': False})

        # Lockear intent
        intent.status = PaymentIntent.STATUS_IN_PROGRESS
        intent.locked_by_agent = agent_id
        intent.locked_at = datetime.utcnow()
        intent.updated_at = datetime.utcnow()
        db.session.commit()

        amount_clp = int(float(intent.amount_total))
        return jsonify({
            'hasPayment': True,
            'paymentId': str(intent.id),
            'amount': amount_clp
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error en /api/getnet/pending: {e}", exc_info=True)
        return jsonify({'success': False, 'error': f'Error interno: {str(e)}'}), 500


@caja_bp.route('/api/getnet/result', methods=['POST'])
@rate_limit(max_requests=30, window_seconds=60)
def getnet_result_compat():
    """
    Endpoint compat para agentes antiguos:
    POST /api/getnet/result
    Body esperado (legacy):
      { paymentId: <uuid>, result: { success: bool, message: str, provider_ref?, auth_code? } }
    """
    if not verify_agent_auth():
        return jsonify({'success': False, 'error': 'Autenticación inválida'}), 401

    try:
        data = request.get_json(silent=True) or {}

        payment_id = data.get('paymentId') or data.get('intent_id')
        if not payment_id:
            return jsonify({'success': False, 'error': 'paymentId requerido'}), 400

        # Traducir resultado legacy -> status esperado
        result = data.get('result') or {}
        if isinstance(result, dict):
            success = bool(result.get('success', False))
            message = str(result.get('message', '') or '')
            provider_ref = result.get('provider_ref') or result.get('providerRef')
            auth_code = result.get('auth_code') or result.get('authCode')
        else:
            success = False
            message = ''
            provider_ref = None
            auth_code = None

        if success:
            status = PaymentIntent.STATUS_APPROVED
            error_code = None
            error_message = None
        else:
            # Mapeo simple: rejected -> DECLINED, resto -> ERROR
            status = PaymentIntent.STATUS_DECLINED if message.lower() in ('rejected', 'declined') else PaymentIntent.STATUS_ERROR
            error_code = 'DECLINED' if status == PaymentIntent.STATUS_DECLINED else 'ERROR'
            error_message = message or 'error'

        payload = {
            'intent_id': str(payment_id),
            'status': status,
            'provider_ref': provider_ref,
            'auth_code': auth_code,
            'error_code': error_code,
            'error_message': error_message,
        }

        return _process_agent_result_payload(payload)

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error en /api/getnet/result: {e}", exc_info=True)
        return jsonify({'success': False, 'error': f'Error interno: {str(e)}'}), 500


@caja_bp.route('/api/payment/agent/heartbeat', methods=['POST'])
@rate_limit(max_requests=60, window_seconds=60)
def agent_heartbeat():
    """
    Endpoint para que el agente Windows envíe heartbeat periódico
    
    Body esperado:
    {
        "register_id": "TEST001",
        "agent_name": "POS-CAJA-TEST",
        "ip": "192.168.1.50",
        "getnet_status": "OK",  # 'OK' | 'ERROR' | 'UNKNOWN'
        "getnet_message": "Pinpad conectado y listo"
    }
    """
    if not verify_agent_auth():
        return jsonify({'ok': False, 'error': 'Autenticación inválida'}), 401
    
    try:
        data = request.get_json(silent=True) or {}
        
        register_id = data.get('register_id')
        agent_name = data.get('agent_name')
        
        if not register_id or not agent_name:
            return jsonify({
                'ok': False,
                'error': 'register_id y agent_name son requeridos'
            }), 400
        
        register_id = str(register_id).strip()
        agent_name = str(agent_name).strip()
        
        ip = data.get('ip', '').strip() or None
        getnet_status = data.get('getnet_status', '').strip() or None
        getnet_message = data.get('getnet_message', '').strip() or None
        
        # Validar getnet_status si viene
        if getnet_status and getnet_status not in ['OK', 'ERROR', 'UNKNOWN']:
            getnet_status = 'UNKNOWN'
        
        now = datetime.utcnow()
        
        # Buscar PaymentAgent existente por register_id y agent_name
        agent = PaymentAgent.query.filter_by(
            register_id=register_id,
            agent_name=agent_name
        ).first()
        
        if agent:
            # Actualizar existente
            agent.last_heartbeat = now
            agent.last_ip = ip
            agent.last_getnet_status = getnet_status
            agent.last_getnet_message = getnet_message
            agent.updated_at = now
            
            logger.info(
                f"💓 Heartbeat actualizado: register={register_id} agent={agent_name} "
                f"status={getnet_status} ip={ip}"
            )
        else:
            # Crear nuevo
            agent = PaymentAgent(
                register_id=register_id,
                agent_name=agent_name,
                last_heartbeat=now,
                last_ip=ip,
                last_getnet_status=getnet_status,
                last_getnet_message=getnet_message,
                created_at=now,
                updated_at=now
            )
            db.session.add(agent)
            
            logger.info(
                f"✅ Nuevo agente registrado: register={register_id} agent={agent_name} "
                f"status={getnet_status}"
            )
        
        db.session.commit()
        
        return jsonify({
            'ok': True,
            'agent_id': str(agent.id),
            'message': 'heartbeat registrado'
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error al registrar heartbeat: {e}", exc_info=True)
        return jsonify({
            'ok': False,
            'error': f'Error interno: {str(e)}'
        }), 500


@caja_bp.route('/api/payment/agent/config', methods=['GET'])
@rate_limit(max_requests=30, window_seconds=60)
def agent_get_config():
    """
    Endpoint para que el agente obtenga su configuración desde el backend
    
    Query params:
    - register_id: ID de la caja (requerido)
    
    Autenticación: X-AGENT-KEY header
    
    Retorna la configuración de Getnet desde provider_config de la caja
    """
    if not verify_agent_auth():
        return jsonify({'success': False, 'error': 'Autenticación inválida'}), 401
    
    try:
        register_id = request.args.get('register_id')
        if not register_id:
            return jsonify({'success': False, 'error': 'register_id requerido'}), 400
        
        register_id = str(register_id).strip()
        
        # Buscar caja
        register_obj = PosRegister.query.filter(
            (PosRegister.id == register_id) | (PosRegister.code == register_id)
        ).first()
        
        if not register_obj:
            return jsonify({'success': False, 'error': f'register_id {register_id} no existe'}), 404
        
        # Obtener provider_config
        provider_config = {}
        if register_obj.provider_config:
            try:
                provider_config = json.loads(register_obj.provider_config)
            except:
                provider_config = {}
        
        # Extraer configuración de Getnet
        getnet_config = provider_config.get('GETNET', {})
        
        # Preparar respuesta con configuración Getnet
        config_response = {
            'success': True,
            'register_id': register_id,
            'register_name': register_obj.name,
            'register_code': register_obj.code,
            'getnet': {
                'enabled': bool(getnet_config),
                'mode': getnet_config.get('mode', 'manual'),
            }
        }
        
        # Si es modo serial, incluir configuración serial
        if getnet_config.get('mode') == 'serial':
            config_response['getnet'].update({
                'port': getnet_config.get('port', 'COM3'),
                'baudrate': getnet_config.get('baudrate', 115200),
                'timeout_ms': getnet_config.get('timeout_ms', 30000)
            })
        
        logger.info(f"✅ Configuración Getnet enviada a agente para register {register_id}")
        return jsonify(config_response)
    
    except Exception as e:
        logger.error(f"Error al obtener configuración para agente: {e}", exc_info=True)
        return jsonify({'success': False, 'error': f'Error interno: {str(e)}'}), 500

